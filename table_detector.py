#!/usr/bin/env python3
"""
Table Transformer: ML-based table detection and structure recognition
=====================================================================
Uses microsoft/table-transformer-detection for finding tables and
microsoft/table-transformer-structure-recognition-v1.1-all for
recognizing rows, columns, and cells.

Replaces hardcoded X/Y boundaries in spatial_extract.py with
dynamically detected table structure.

Usage:
    from table_detector import TableTransformerEngine
    engine = TableTransformerEngine(device="cuda")
    tables = engine.extract_tables(image_path, bbox_data)
    engine.cleanup()
"""

from __future__ import annotations

import gc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from transformers import AutoImageProcessor, TableTransformerForObjectDetection
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


# Detection threshold for table regions
TABLE_DETECTION_THRESHOLD = 0.7
# Structure recognition threshold
STRUCTURE_THRESHOLD = 0.5


@dataclass
class DetectedCell:
    """A single cell in a detected table."""
    row: int
    col: int
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    text: str = ""
    confidence: float = 0.0

    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        return (self.x_min, self.y_min, self.x_max, self.y_max)


@dataclass
class DetectedTable:
    """A detected table with its structure."""
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    confidence: float
    page: int = 0
    rows: List[List[DetectedCell]] = field(default_factory=list)
    headers: List[str] = field(default_factory=list)
    num_rows: int = 0
    num_cols: int = 0

    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        return (self.x_min, self.y_min, self.x_max, self.y_max)

    def to_markdown(self) -> str:
        """Convert table to markdown format."""
        if not self.rows:
            return ""

        lines = []

        # Headers
        if self.headers:
            lines.append("| " + " | ".join(self.headers) + " |")
            lines.append("| " + " | ".join("---" for _ in self.headers) + " |")

        # Data rows
        for row in self.rows:
            cells = [cell.text for cell in row]
            # Pad to consistent width
            while len(cells) < self.num_cols:
                cells.append("")
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines)

    def get_row_dict(self, row_idx: int) -> Dict[str, str]:
        """Get a dict mapping header names to cell values for a row."""
        if row_idx >= len(self.rows) or not self.headers:
            return {}
        row = self.rows[row_idx]
        result = {}
        for i, header in enumerate(self.headers):
            if i < len(row):
                result[header] = row[i].text
        return result

    def get_column_values(self, col_name: str) -> List[str]:
        """Get all values in a column by header name."""
        if col_name not in self.headers:
            return []
        col_idx = self.headers.index(col_name)
        values = []
        for row in self.rows:
            if col_idx < len(row):
                values.append(row[col_idx].text)
            else:
                values.append("")
        return values


class TableTransformerEngine:
    """
    Detects tables and recognizes their structure using Table Transformer models.

    Lazy-loads models on first use. Can run on GPU or CPU.
    """

    DETECTION_MODEL = "microsoft/table-transformer-detection"
    STRUCTURE_MODEL = "microsoft/table-transformer-structure-recognition-v1.1-all"

    def __init__(self, device: str = "cpu"):
        """
        Args:
            device: "cpu" or "cuda" for model inference.
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "transformers is required for Table Transformer. "
                "Install with: pip install transformers"
            )
        if not PIL_AVAILABLE:
            raise ImportError("Pillow is required for Table Transformer.")

        self.device = device
        self._detection_model = None
        self._detection_processor = None
        self._structure_model = None
        self._structure_processor = None

    def _load_detection_model(self) -> None:
        """Lazy-load the table detection model."""
        if self._detection_model is not None:
            return
        print("  [TableTransformer] Loading detection model ...")
        self._detection_processor = AutoImageProcessor.from_pretrained(
            self.DETECTION_MODEL
        )
        self._detection_model = TableTransformerForObjectDetection.from_pretrained(
            self.DETECTION_MODEL
        ).to(self.device)
        self._detection_model.eval()

    def _load_structure_model(self) -> None:
        """Lazy-load the structure recognition model."""
        if self._structure_model is not None:
            return
        print("  [TableTransformer] Loading structure recognition model ...")
        self._structure_processor = AutoImageProcessor.from_pretrained(
            self.STRUCTURE_MODEL
        )
        self._structure_model = TableTransformerForObjectDetection.from_pretrained(
            self.STRUCTURE_MODEL
        ).to(self.device)
        self._structure_model.eval()

    def detect_tables(
        self,
        image_path: Path,
        threshold: float = TABLE_DETECTION_THRESHOLD,
    ) -> List[Tuple[float, float, float, float, float]]:
        """
        Detect table bounding boxes in an image.

        Returns:
            List of (x_min, y_min, x_max, y_max, confidence) tuples.
        """
        self._load_detection_model()

        image = Image.open(image_path).convert("RGB")
        width, height = image.size

        inputs = self._detection_processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._detection_model(**inputs)

        # Post-process
        target_sizes = torch.tensor([[height, width]]).to(self.device)
        results = self._detection_processor.post_process_object_detection(
            outputs, threshold=threshold, target_sizes=target_sizes
        )[0]

        tables = []
        for score, box in zip(results["scores"], results["boxes"]):
            x_min, y_min, x_max, y_max = box.cpu().tolist()
            tables.append((x_min, y_min, x_max, y_max, score.item()))

        return tables

    def recognize_structure(
        self,
        image_path: Path,
        table_bbox: Tuple[float, float, float, float],
        threshold: float = STRUCTURE_THRESHOLD,
    ) -> Dict[str, List[Tuple[float, float, float, float]]]:
        """
        Recognize table structure (rows, columns) within a table region.

        Returns:
            {"rows": [...bbox...], "columns": [...bbox...], "headers": [...bbox...]}
        """
        self._load_structure_model()

        image = Image.open(image_path).convert("RGB")
        # Crop to table region
        x_min, y_min, x_max, y_max = table_bbox
        cropped = image.crop((int(x_min), int(y_min), int(x_max), int(y_max)))
        crop_w, crop_h = cropped.size

        inputs = self._structure_processor(images=cropped, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._structure_model(**inputs)

        target_sizes = torch.tensor([[crop_h, crop_w]]).to(self.device)
        results = self._structure_processor.post_process_object_detection(
            outputs, threshold=threshold, target_sizes=target_sizes
        )[0]

        # Separate rows, columns, headers
        structure: Dict[str, List[Tuple[float, float, float, float]]] = {
            "rows": [],
            "columns": [],
            "headers": [],
        }

        # DETR labels: 0=table, 1=table column, 2=table row, 3=table column header,
        #              4=table projected row header, 5=table spanning cell
        label_map = {0: "table", 1: "columns", 2: "rows", 3: "headers", 4: "headers"}

        for label, box in zip(results["labels"], results["boxes"]):
            category = label_map.get(label.item(), None)
            if category is None or category == "table":
                continue
            bx = box.cpu().tolist()
            # Convert back to full-image coordinates
            bx = [
                bx[0] + x_min,
                bx[1] + y_min,
                bx[2] + x_min,
                bx[3] + y_min,
            ]
            structure[category].append(tuple(bx))

        # Sort rows by Y, columns by X
        structure["rows"].sort(key=lambda b: b[1])
        structure["columns"].sort(key=lambda b: b[0])

        return structure

    def extract_tables(
        self,
        image_path: Path,
        bbox_data: List[Dict],
        page: int = 0,
    ) -> List[DetectedTable]:
        """
        Full pipeline: detect tables, recognize structure, fill cells with OCR text.

        Args:
            image_path: Path to the page image.
            bbox_data: OCR bbox dicts for this page.
            page: Page number (0-indexed).

        Returns:
            List of DetectedTable with text-filled cells.
        """
        # Step 1: Detect tables
        table_bboxes = self.detect_tables(image_path)
        if not table_bboxes:
            return []

        detected_tables: List[DetectedTable] = []

        for tx_min, ty_min, tx_max, ty_max, conf in table_bboxes:
            # Step 2: Recognize structure
            structure = self.recognize_structure(
                image_path, (tx_min, ty_min, tx_max, ty_max)
            )

            row_bboxes = structure.get("rows", [])
            col_bboxes = structure.get("columns", [])

            if not row_bboxes or not col_bboxes:
                continue

            num_rows = len(row_bboxes)
            num_cols = len(col_bboxes)

            # Step 3: Intersect rows and columns to create cells
            table_rows: List[List[DetectedCell]] = []
            header_texts: List[str] = []

            for r_idx, row_bbox in enumerate(row_bboxes):
                row_cells: List[DetectedCell] = []
                for c_idx, col_bbox in enumerate(col_bboxes):
                    # Cell = intersection of row and column
                    cell_x_min = max(row_bbox[0], col_bbox[0])
                    cell_y_min = max(row_bbox[1], col_bbox[1])
                    cell_x_max = min(row_bbox[2], col_bbox[2])
                    cell_y_max = min(row_bbox[3], col_bbox[3])

                    if cell_x_max <= cell_x_min or cell_y_max <= cell_y_min:
                        row_cells.append(DetectedCell(
                            row=r_idx, col=c_idx,
                            x_min=col_bbox[0], y_min=row_bbox[1],
                            x_max=col_bbox[2], y_max=row_bbox[3],
                        ))
                        continue

                    # Find OCR blocks within the cell
                    cell_text = self._get_cell_text(
                        bbox_data, cell_x_min, cell_y_min, cell_x_max, cell_y_max
                    )

                    row_cells.append(DetectedCell(
                        row=r_idx, col=c_idx,
                        x_min=cell_x_min, y_min=cell_y_min,
                        x_max=cell_x_max, y_max=cell_y_max,
                        text=cell_text,
                    ))

                table_rows.append(row_cells)

            # Extract headers (first row or detected header regions)
            header_bboxes = structure.get("headers", [])
            if header_bboxes and table_rows:
                # Use first row as headers if it overlaps with header region
                header_texts = [cell.text for cell in table_rows[0]]
                # Remove header row from data rows
                data_rows = table_rows[1:]
            elif table_rows:
                # Use first row as headers
                header_texts = [cell.text for cell in table_rows[0]]
                data_rows = table_rows[1:]
            else:
                data_rows = table_rows

            detected_tables.append(DetectedTable(
                x_min=tx_min, y_min=ty_min,
                x_max=tx_max, y_max=ty_max,
                confidence=conf,
                page=page,
                rows=data_rows,
                headers=header_texts,
                num_rows=len(data_rows),
                num_cols=num_cols,
            ))

        return detected_tables

    @staticmethod
    def _get_cell_text(
        bbox_data: List[Dict],
        x_min: float, y_min: float,
        x_max: float, y_max: float,
        tolerance: float = 10,
    ) -> str:
        """Find OCR text blocks whose centers fall within a cell region."""
        blocks = []
        for b in bbox_data:
            bx, by = b["x"], b["y"]
            if (x_min - tolerance <= bx <= x_max + tolerance and
                    y_min - tolerance <= by <= y_max + tolerance):
                blocks.append(b)

        if not blocks:
            return ""

        # Sort by position and concatenate
        blocks.sort(key=lambda b: (b["y"], b["x"]))
        return " ".join(b["text"].strip() for b in blocks if b["text"].strip())

    def cleanup(self) -> None:
        """Free GPU/CPU memory used by models."""
        if self._detection_model is not None:
            del self._detection_model
            self._detection_model = None
        if self._detection_processor is not None:
            del self._detection_processor
            self._detection_processor = None
        if self._structure_model is not None:
            del self._structure_model
            self._structure_model = None
        if self._structure_processor is not None:
            del self._structure_processor
            self._structure_processor = None

        gc.collect()
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
        print("  [TableTransformer] Models unloaded")
