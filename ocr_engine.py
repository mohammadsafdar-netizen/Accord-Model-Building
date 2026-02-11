#!/usr/bin/env python3
"""
OCR Engine: Dual OCR Fusion + Spatial Analysis
===============================================
Combines Docling (semantic structure) and EasyOCR (spatial bounding boxes)
for high-accuracy text extraction from scanned ACORD forms.

Pipeline:
  PDF -> Images (300 DPI)
      -> Table line removal (morphological ops)
      -> Docling OCR  -> structured markdown per page
      -> EasyOCR      -> text + X,Y bounding boxes per page
      -> Spatial Index -> rows, columns, tables, label-value pairs
"""

from __future__ import annotations

import gc
import os
import re
import statistics

# Must be set before torch import to reduce GPU memory fragmentation
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import defaultdict

# ---------------------------------------------------------------------------
# Optional heavy imports
# ---------------------------------------------------------------------------
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    DOCLING_AVAILABLE = True
except ImportError:
    DOCLING_AVAILABLE = False


# ===========================================================================
# GPU helpers
# ===========================================================================

def cleanup_gpu_memory():
    """Release GPU memory between operations.

    Calls gc.collect() first to free Python objects referencing CUDA tensors,
    then empties the PyTorch CUDA memory cache to return blocks to the OS.
    """
    gc.collect()
    if TORCH_AVAILABLE and torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()  # also collect IPC memory
        gc.collect()  # second pass in case empty_cache freed python refs


# ===========================================================================
# Data classes
# ===========================================================================

@dataclass
class TextBlock:
    """A block of text with spatial information from EasyOCR."""
    text: str
    x: int          # Centre X
    y: int          # Centre Y
    x_min: int
    y_min: int
    x_max: int
    y_max: int
    width: int
    height: int
    confidence: float = 1.0
    page: int = 1
    is_label: bool = False
    is_value: bool = False

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x, self.y)

    def distance_to(self, other: "TextBlock") -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return (dx * dx + dy * dy) ** 0.5

    def is_horizontally_aligned(self, other: "TextBlock", tolerance: int = 30) -> bool:
        return abs(self.y - other.y) <= tolerance

    def is_to_right_of(self, other: "TextBlock", max_gap: int = 200) -> bool:
        return (
            self.is_horizontally_aligned(other)
            and self.x_min > other.x_max
            and self.x_min - other.x_max <= max_gap
        )


@dataclass
class Row:
    """A row of horizontally-aligned text blocks."""
    blocks: List[TextBlock] = field(default_factory=list)
    y_center: int = 0

    @property
    def y_min(self) -> int:
        return min(b.y_min for b in self.blocks) if self.blocks else 0

    @property
    def y_max(self) -> int:
        return max(b.y_max for b in self.blocks) if self.blocks else 0

    def to_text(self) -> str:
        return " | ".join(b.text for b in sorted(self.blocks, key=lambda b: b.x))


@dataclass
class Column:
    """A detected column region."""
    x_center: int
    x_min: int
    x_max: int
    name: Optional[str] = None
    blocks: List[TextBlock] = field(default_factory=list)


@dataclass
class TableRegion:
    """A detected table region with rows and columns."""
    rows: List[Row] = field(default_factory=list)
    columns: List[Column] = field(default_factory=list)
    y_min: int = 0
    y_max: int = 0
    header_row: Optional[Row] = None


@dataclass
class LabelValuePair:
    label: TextBlock
    value: TextBlock
    confidence: float = 1.0


@dataclass
class SpatialIndex:
    """Full spatial index for one page."""
    blocks: List[TextBlock] = field(default_factory=list)
    rows: List[Row] = field(default_factory=list)
    columns: List[Column] = field(default_factory=list)
    tables: List[TableRegion] = field(default_factory=list)
    label_value_pairs: List[LabelValuePair] = field(default_factory=list)
    page_width: int = 0
    page_height: int = 0
    page: int = 1


@dataclass
class OCRResult:
    """Complete OCR output for a document."""
    docling_pages: List[str]          # Markdown text per page
    bbox_pages: List[List[Dict]]      # Raw bbox dicts per page
    spatial_indices: List[SpatialIndex]
    image_paths: List[Path]
    clean_image_paths: List[Path]
    num_pages: int

    @property
    def full_docling_text(self) -> str:
        return "\n\n=== PAGE BREAK ===\n\n".join(self.docling_pages)

    def all_bbox_data(self) -> List[Dict]:
        out: List[Dict] = []
        for page_data in self.bbox_pages:
            out.extend(page_data)
        return out


# ===========================================================================
# Label / value detection helpers
# ===========================================================================

LABEL_PATTERNS = [
    r'.*:$',
    r'.*\?$',
    r'^[A-Z][A-Z\s]+$',
    r'^\d+\.',
    r'^\([a-z]\)',
]

LABEL_KEYWORDS = {
    'name', 'date', 'address', 'phone', 'fax', 'email', 'city', 'state',
    'zip', 'policy', 'insured', 'insurer', 'producer', 'agent', 'carrier',
    'effective', 'expiration', 'premium', 'limit', 'deductible', 'coverage',
    'driver', 'vehicle', 'license', 'dob', 'birth', 'gender', 'sex',
    'marital', 'number', 'code', 'type', 'yes', 'no', 'signature', 'title',
    'company', 'agency', 'naic',
}


def is_likely_label(text: str) -> bool:
    text_clean = text.strip()
    text_lower = text_clean.lower()
    for pat in LABEL_PATTERNS:
        if re.match(pat, text_clean):
            return True
    words = set(re.findall(r'\b\w+\b', text_lower))
    if words & LABEL_KEYWORDS:
        return True
    if '(' in text_clean and ')' in text_clean and len(text_clean) < 50:
        return True
    return False


def is_likely_value(text: str) -> bool:
    text_clean = text.strip()
    if re.match(r'\d{1,2}/\d{1,2}/\d{2,4}', text_clean):
        return True
    if re.match(r'^[\d,.$%]+$', text_clean):
        return True
    if re.match(r'^\d{3}[-.]?\d{3}[-.]?\d{4}$', text_clean):
        return True
    if '@' in text_clean and '.' in text_clean:
        return True
    return not is_likely_label(text_clean)


# ===========================================================================
# OCR Engine
# ===========================================================================

class OCREngine:
    """
    Dual OCR engine: Docling (structure) + EasyOCR (spatial bounding boxes).
    Also performs table-line removal and spatial indexing.
    """

    def __init__(
        self,
        dpi: int = 300,
        easyocr_gpu: bool = False,
        force_cpu: bool = True,
        docling_cpu_when_gpu: bool = True,
        row_tolerance: int = 25,
        column_tolerance: int = 40,
    ):
        self.dpi = dpi
        self.easyocr_gpu = easyocr_gpu
        self.force_cpu = force_cpu
        # Intelligent offload: when using GPU, run Docling on CPU to free GPU for EasyOCR + LLM
        self.docling_cpu_when_gpu = docling_cpu_when_gpu
        self.row_tolerance = row_tolerance
        self.column_tolerance = column_tolerance

        self._docling_converter = None
        self._easyocr_reader = None

    # ------------------------------------------------------------------
    # GPU memory cleanup
    # ------------------------------------------------------------------

    def cleanup_docling(self):
        """Free Docling from GPU memory. Must be called before EasyOCR on GPU."""
        if self._docling_converter is not None:
            del self._docling_converter
            self._docling_converter = None
        cleanup_gpu_memory()
        print("  [OCR] Docling unloaded from GPU")

    def cleanup_easyocr(self):
        """Free EasyOCR from GPU memory. Must be called before LLM on GPU."""
        if self._easyocr_reader is not None:
            del self._easyocr_reader
            self._easyocr_reader = None
        cleanup_gpu_memory()
        print("  [OCR] EasyOCR unloaded from GPU")

    def cleanup(self):
        """Free ALL GPU memory from OCR models."""
        self.cleanup_docling()
        self.cleanup_easyocr()
        print("  [OCR] All OCR GPU memory released")

    # ------------------------------------------------------------------
    # Lazy init (avoids heavy imports if unused)
    # ------------------------------------------------------------------

    def _get_docling(self, use_gpu: bool = False):
        """Get or create Docling converter.
        
        Args:
            use_gpu: If True, use GPU acceleration. If False, use CPU.
                     Each call with a different mode recreates the converter.
        """
        if self._docling_converter is not None:
            return self._docling_converter
        if not DOCLING_AVAILABLE:
            raise RuntimeError("docling is not installed. pip install docling")
        if not use_gpu:
            acc_opts = AcceleratorOptions(num_threads=4, device=AcceleratorDevice.CPU)
            pipe_opts = PdfPipelineOptions()
            pipe_opts.accelerator_options = acc_opts
            pipe_opts.do_ocr = True
            self._docling_converter = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipe_opts)}
            )
        else:
            # GPU mode - let Docling use default GPU acceleration
            pipe_opts = PdfPipelineOptions()
            pipe_opts.do_ocr = True
            self._docling_converter = DocumentConverter(
                format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipe_opts)}
            )
        return self._docling_converter

    def _get_easyocr(self):
        if self._easyocr_reader is not None:
            return self._easyocr_reader
        if not EASYOCR_AVAILABLE:
            raise RuntimeError("easyocr is not installed. pip install easyocr")
        # EasyOCR GPU is controlled independently from Docling.
        # On small GPUs (<=6GB), EasyOCR needs ~1.5GB which fits
        # after Docling (CPU-only) finishes.
        use_gpu = self.easyocr_gpu
        try:
            self._easyocr_reader = easyocr.Reader(["en"], gpu=use_gpu, verbose=False)
        except Exception:
            print("  [OCR] EasyOCR GPU init failed, falling back to CPU")
            self._easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        return self._easyocr_reader

    # ------------------------------------------------------------------
    # PDF -> images
    # ------------------------------------------------------------------

    def pdf_to_images(self, pdf_path: Path, output_dir: Path) -> List[Path]:
        """Convert PDF to page images at configured DPI."""
        if not PDF2IMAGE_AVAILABLE:
            raise RuntimeError("pdf2image is not installed. pip install pdf2image")
        output_dir.mkdir(parents=True, exist_ok=True)
        images = convert_from_path(str(pdf_path), dpi=self.dpi)
        paths: List[Path] = []
        for i, img in enumerate(images, 1):
            out = output_dir / f"{pdf_path.stem}_page_{i}.png"
            img.save(str(out), "PNG")
            paths.append(out)
        return paths

    # ------------------------------------------------------------------
    # Table-line removal
    # ------------------------------------------------------------------

    def create_clean_images(self, image_paths: List[Path]) -> List[Path]:
        """Remove horizontal / vertical lines via morphological ops for cleaner OCR."""
        if not CV2_AVAILABLE:
            return list(image_paths)  # fallback: use originals
        clean: List[Path] = []
        for img_path in image_paths:
            img = cv2.imread(str(img_path))
            if img is None:
                clean.append(img_path)
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

            h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (60, 1))
            v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 60))
            h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel, iterations=2)
            v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel, iterations=2)
            all_lines = cv2.add(h_lines, v_lines)
            all_lines = cv2.dilate(all_lines, np.ones((3, 3), np.uint8), iterations=2)

            text_only = cv2.subtract(binary, all_lines)
            text_only = cv2.bitwise_not(text_only)

            out_path = img_path.parent / f"{img_path.stem}_clean.png"
            cv2.imwrite(str(out_path), text_only)
            clean.append(out_path)
        return clean

    # ------------------------------------------------------------------
    # Docling OCR
    # ------------------------------------------------------------------

    def run_docling(self, image_paths: List[Path], use_gpu: bool = False) -> List[str]:
        """Run Docling OCR on each page image, returning markdown per page."""
        converter = self._get_docling(use_gpu=use_gpu)
        pages: List[str] = []
        for img_path in image_paths:
            cleanup_gpu_memory()
            try:
                result = converter.convert(img_path)
                md = result.document.export_to_markdown()
                pages.append(md)
            except Exception as e:
                pages.append(f"[Docling OCR error: {e}]")
            cleanup_gpu_memory()
        return pages

    # ------------------------------------------------------------------
    # EasyOCR with bounding boxes
    # ------------------------------------------------------------------

    def run_easyocr(self, image_paths: List[Path]) -> List[List[Dict]]:
        """Run EasyOCR on each image; returns list of bbox dicts per page."""
        reader = self._get_easyocr()
        all_pages: List[List[Dict]] = []
        for img_path in image_paths:
            cleanup_gpu_memory()
            try:
                results = reader.readtext(str(img_path))
            except Exception as e:
                print(f"  EasyOCR error on {img_path.name}: {e}")
                all_pages.append([])
                continue
            page_data: List[Dict] = []
            for bbox, text, conf in results:
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                x_min, x_max = int(min(x_coords)), int(max(x_coords))
                y_min, y_max = int(min(y_coords)), int(max(y_coords))
                page_data.append({
                    "text": re.sub(r"\s+", " ", text).strip(),
                    "x": int((x_min + x_max) / 2),
                    "y": int((y_min + y_max) / 2),
                    "x_min": x_min, "y_min": y_min,
                    "x_max": x_max, "y_max": y_max,
                    "width": x_max - x_min,
                    "height": y_max - y_min,
                    "confidence": round(conf, 2),
                })
            page_data.sort(key=lambda d: (d["y"], d["x"]))
            all_pages.append(page_data)
            cleanup_gpu_memory()
        return all_pages

    # ------------------------------------------------------------------
    # Spatial indexing
    # ------------------------------------------------------------------

    def build_spatial_index(
        self,
        bbox_data: List[Dict],
        page_width: int = 0,
        page_height: int = 0,
        page: int = 1,
    ) -> SpatialIndex:
        idx = SpatialIndex(page_width=page_width, page_height=page_height, page=page)

        for bd in bbox_data:
            block = TextBlock(
                text=bd["text"], x=bd["x"], y=bd["y"],
                x_min=bd["x_min"], y_min=bd["y_min"],
                x_max=bd["x_max"], y_max=bd["y_max"],
                width=bd["width"], height=bd["height"],
                confidence=bd.get("confidence", 1.0),
                page=page,
                is_label=is_likely_label(bd["text"]),
                is_value=is_likely_value(bd["text"]),
            )
            idx.blocks.append(block)

        idx.rows = self._cluster_into_rows(idx.blocks)
        idx.columns = self._detect_columns(idx.blocks)
        idx.tables = self._detect_tables(idx.rows, idx.columns)
        idx.label_value_pairs = self._find_label_value_pairs(idx.blocks)
        return idx

    def _cluster_into_rows(self, blocks: List[TextBlock]) -> List[Row]:
        if not blocks:
            return []
        sorted_blocks = sorted(blocks, key=lambda b: b.y)
        rows: List[Row] = []
        cur_row = Row(blocks=[sorted_blocks[0]])
        cur_y = float(sorted_blocks[0].y)
        for block in sorted_blocks[1:]:
            if abs(block.y - cur_y) <= self.row_tolerance:
                cur_row.blocks.append(block)
                cur_y = statistics.mean(b.y for b in cur_row.blocks)
            else:
                cur_row.y_center = int(cur_y)
                cur_row.blocks.sort(key=lambda b: b.x)
                rows.append(cur_row)
                cur_row = Row(blocks=[block])
                cur_y = float(block.y)
        if cur_row.blocks:
            cur_row.y_center = int(cur_y)
            cur_row.blocks.sort(key=lambda b: b.x)
            rows.append(cur_row)
        return rows

    def _detect_columns(self, blocks: List[TextBlock]) -> List[Column]:
        if not blocks:
            return []
        x_clusters: Dict[int, List[int]] = defaultdict(list)
        for b in sorted(blocks, key=lambda b: b.x):
            found = False
            for cx in list(x_clusters.keys()):
                if abs(b.x - cx) <= self.column_tolerance:
                    x_clusters[cx].append(b.x)
                    found = True
                    break
            if not found:
                x_clusters[b.x].append(b.x)
        cols: List[Column] = []
        for cx, positions in sorted(x_clusters.items()):
            if len(positions) >= 2:
                col = Column(
                    x_center=int(statistics.mean(positions)),
                    x_min=min(positions) - self.column_tolerance,
                    x_max=max(positions) + self.column_tolerance,
                )
                col.blocks = [b for b in blocks if col.x_min <= b.x <= col.x_max]
                cols.append(col)
        return cols

    def _detect_tables(self, rows: List[Row], columns: List[Column]) -> List[TableRegion]:
        if not rows or not columns:
            return []
        candidate_rows = [r for r in rows if len(r.blocks) >= 3]
        if len(candidate_rows) < 3:
            return []
        table = TableRegion(
            rows=candidate_rows,
            columns=columns,
            y_min=min(r.y_min for r in candidate_rows),
            y_max=max(r.y_max for r in candidate_rows),
        )
        first = candidate_rows[0]
        if all(is_likely_label(b.text) for b in first.blocks):
            table.header_row = first
        return [table]

    def _find_label_value_pairs(self, blocks: List[TextBlock]) -> List[LabelValuePair]:
        pairs: List[LabelValuePair] = []
        labels = [b for b in blocks if b.is_label]
        values = [b for b in blocks if b.is_value]
        used: Set[int] = set()
        for label in labels:
            best_val: Optional[TextBlock] = None
            best_score = float('inf')
            best_idx = -1
            for i, val in enumerate(values):
                if i in used:
                    continue
                if val.is_to_right_of(label, max_gap=300):
                    score = val.x_min - label.x_max
                    if score < best_score:
                        best_score = score
                        best_val = val
                        best_idx = i
            if best_val is not None:
                pairs.append(LabelValuePair(
                    label=label, value=best_val,
                    confidence=min(label.confidence, best_val.confidence),
                ))
                used.add(best_idx)
        return pairs

    # ------------------------------------------------------------------
    # Formatting helpers (for LLM prompts)
    # ------------------------------------------------------------------

    @staticmethod
    def format_bbox_as_rows(bbox_data: List[Dict], row_tolerance: int = 35, max_rows: int = 200) -> str:
        """Format bbox data as rows with X positions for LLM."""
        if not bbox_data:
            return ""
        rows: List[List[Dict]] = []
        cur_row: List[Dict] = []
        cur_y: float = -9999
        for item in sorted(bbox_data, key=lambda x: (x['y'], x['x'])):
            if abs(item['y'] - cur_y) <= row_tolerance:
                cur_row.append(item)
                cur_y = (cur_y + item['y']) / 2
            else:
                if cur_row:
                    rows.append(sorted(cur_row, key=lambda x: x['x']))
                cur_row = [item]
                cur_y = item['y']
        if cur_row:
            rows.append(sorted(cur_row, key=lambda x: x['x']))

        lines: List[str] = []
        for row in rows[:max_rows]:
            row_str = f"y≈{int(row[0]['y'])}: "
            row_str += " | ".join(f"[x={d['x']}]{d['text']}" for d in row[:12])
            lines.append(row_str)
        return "\n".join(lines)

    @staticmethod
    def format_bbox_as_text(bbox_data: List[Dict], row_tolerance: int = 35) -> str:
        """Format bbox data as plain text (no position info)."""
        if not bbox_data:
            return ""
        rows: List[List[Dict]] = []
        cur_row: List[Dict] = []
        cur_y: float = -9999
        for item in sorted(bbox_data, key=lambda x: (x['y'], x['x'])):
            if abs(item['y'] - cur_y) <= row_tolerance:
                cur_row.append(item)
                cur_y = (cur_y + item['y']) / 2
            else:
                if cur_row:
                    rows.append(sorted(cur_row, key=lambda x: x['x']))
                cur_row = [item]
                cur_y = item['y']
        if cur_row:
            rows.append(sorted(cur_row, key=lambda x: x['x']))
        return "\n".join(" ".join(d['text'] for d in row) for row in rows)

    @staticmethod
    def format_spatial_for_llm(spatial: SpatialIndex, include_positions: bool = True) -> str:
        lines: List[str] = []
        for row in spatial.rows:
            if include_positions:
                items = " | ".join(f"[X={b.x}]{b.text}" for b in row.blocks)
                lines.append(f"[Y≈{row.y_center}] {items}")
            else:
                lines.append(row.to_text())
        return "\n".join(lines)

    @staticmethod
    def format_label_value_pairs(pairs: List[LabelValuePair]) -> str:
        return "\n".join(f"{p.label.text} -> {p.value.text}" for p in pairs)

    @staticmethod
    def format_tables_for_llm(tables: List[TableRegion]) -> str:
        parts: List[str] = []
        for i, tbl in enumerate(tables, 1):
            parts.append(f"\n=== TABLE {i} ===")
            if tbl.header_row:
                parts.append("Headers: " + " | ".join(b.text for b in tbl.header_row.blocks))
            parts.append(f"Columns at X: {[c.x_center for c in tbl.columns]}")
            data_rows = tbl.rows[1:] if tbl.header_row else tbl.rows
            for row in data_rows:
                parts.append("  " + " | ".join(b.text for b in row.blocks))
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def process(self, pdf_path: Path, output_dir: Path) -> OCRResult:
        """
        Run the complete OCR pipeline on a PDF.

        GPU+CPU offload (when easyocr_gpu=True, docling_cpu_when_gpu=True):
          1. Docling on CPU  → no GPU load
          2. EasyOCR on GPU  → unload EasyOCR when done
          3. (caller runs LLM on GPU → caller unloads LLM)
        Full GPU (when easyocr_gpu=True, docling_cpu_when_gpu=False):
          1. Docling on GPU  → unload Docling
          2. EasyOCR on GPU  → unload EasyOCR
          3. (caller runs LLM on GPU)

        Returns an OCRResult with:
          - docling_pages (markdown per page)
          - bbox_pages (bbox dicts per page)
          - spatial_indices (per page)
          - image_paths / clean_image_paths
        """
        use_gpu = not self.force_cpu
        # Intelligent offload: Docling on CPU so GPU is free for EasyOCR and LLM
        docling_use_gpu = use_gpu and not self.docling_cpu_when_gpu

        print(f"  [OCR] Converting PDF to images at {self.dpi} DPI ...")
        img_dir = output_dir / "images"
        image_paths = self.pdf_to_images(pdf_path, img_dir)
        print(f"  [OCR] {len(image_paths)} page images created")

        print("  [OCR] Removing table lines ...")
        clean_paths = self.create_clean_images(image_paths)

        # ---- Phase 1: Docling OCR (CPU when offload, else GPU) ----
        docling_mode = "CPU (offload)" if (use_gpu and self.docling_cpu_when_gpu) else ("GPU" if docling_use_gpu else "CPU")
        print(f"  [OCR] Running Docling OCR ({docling_mode}) ...")
        docling_pages = self.run_docling(image_paths, use_gpu=docling_use_gpu)
        total_chars = sum(len(p) for p in docling_pages)
        print(f"  [OCR] Docling produced {total_chars} chars across {len(docling_pages)} pages")

        # Unload Docling from GPU before EasyOCR (no-op if Docling was CPU)
        self.cleanup_docling()

        # ---- Phase 2: EasyOCR (GPU when use_gpu, else CPU) ----
        easyocr_mode = "GPU" if use_gpu else "CPU"
        print(f"  [OCR] Running EasyOCR with bounding boxes ({easyocr_mode}) ...")
        bbox_pages = self.run_easyocr(clean_paths)
        total_blocks = sum(len(p) for p in bbox_pages)
        print(f"  [OCR] EasyOCR found {total_blocks} text blocks")

        # Unload EasyOCR from GPU before LLM
        self.cleanup_easyocr()

        # ---- Phase 3: Build spatial indices (CPU only, no GPU needed) ----
        print("  [OCR] Building spatial indices ...")
        spatial_indices: List[SpatialIndex] = []
        for page_num, page_bbox in enumerate(bbox_pages, 1):
            # Get dimensions from the image
            pw, ph = 0, 0
            if CV2_AVAILABLE and page_num <= len(image_paths):
                img = cv2.imread(str(image_paths[page_num - 1]))
                if img is not None:
                    ph, pw = img.shape[:2]
            si = self.build_spatial_index(page_bbox, pw, ph, page=page_num)
            spatial_indices.append(si)
            print(
                f"    Page {page_num}: {len(si.blocks)} blocks, "
                f"{len(si.rows)} rows, {len(si.columns)} cols, "
                f"{len(si.tables)} tables, {len(si.label_value_pairs)} pairs"
            )

        return OCRResult(
            docling_pages=docling_pages,
            bbox_pages=bbox_pages,
            spatial_indices=spatial_indices,
            image_paths=image_paths,
            clean_image_paths=clean_paths,
            num_pages=len(image_paths),
        )
