#!/usr/bin/env python3
"""
Vision helpers: crop form page images into regions for describe-then-extract pipeline.
Supports fixed grid (2x2) or dynamic layout-based regions from Docling/EasyOCR.
"""
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Optional: for layout-based cropping from OCR result
try:
    from ocr_engine import OCRResult, SpatialIndex
    OCR_ENGINE_AVAILABLE = True
except ImportError:
    OCRResult = None  # type: ignore
    SpatialIndex = None  # type: ignore
    OCR_ENGINE_AVAILABLE = False


def crop_page_to_tiles(
    image_path: Path,
    grid: Tuple[int, int] = (2, 2),
    output_dir: Optional[Path] = None,
) -> List[Path]:
    """
    Split a page image into a grid of tiles (e.g. 2x2 = 4 regions).
    Returns paths to saved tile images (temp dir or output_dir).
    """
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL/Pillow required for crop_page_to_tiles. pip install Pillow")
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(str(path))
    img = Image.open(path).convert("RGB")
    w, h = img.size
    rows, cols = grid
    tile_w = w // cols
    tile_h = h // rows
    if output_dir is None:
        import tempfile
        output_dir = Path(tempfile.mkdtemp(prefix="vision_tiles_"))
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    out_paths: List[Path] = []
    stem = path.stem
    for i in range(rows):
        for j in range(cols):
            left = j * tile_w
            top = i * tile_h
            right = (j + 1) * tile_w if j < cols - 1 else w
            bottom = (i + 1) * tile_h if i < rows - 1 else h
            tile = img.crop((left, top, right, bottom))
            out_name = f"{stem}_tile_{i}_{j}.png"
            out_path = output_dir / out_name
            tile.save(out_path, "PNG")
            out_paths.append(out_path)
    return out_paths


def crop_pages_to_tiles(
    image_paths: List[Path],
    grid: Tuple[int, int] = (2, 2),
    output_dir: Optional[Path] = None,
    max_pages: int = 2,
) -> List[Path]:
    """Crop the first max_pages images to tiles; returns flat list of all tile paths."""
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="vision_tiles_"))
    all_tiles: List[Path] = []
    for page_idx, p in enumerate(image_paths[:max_pages]):
        if not Path(p).exists():
            continue
        tiles = crop_page_to_tiles(p, grid=grid, output_dir=output_dir)
        all_tiles.extend(tiles)
    return all_tiles


# =============================================================================
# Layout-based cropping (EasyOCR bbox / spatial index)
# =============================================================================

def _crop_image_to_bbox(
    image_path: Path,
    bbox: Tuple[int, int, int, int],
    output_path: Path,
) -> Path:
    """Crop image to (x_min, y_min, x_max, y_max); save to output_path. Returns output_path."""
    if not PIL_AVAILABLE:
        raise RuntimeError("PIL required for _crop_image_to_bbox")
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    x_min, y_min, x_max, y_max = bbox
    x_min = max(0, min(x_min, w - 1))
    y_min = max(0, min(y_min, h - 1))
    x_max = max(x_min + 1, min(x_max, w))
    y_max = max(y_min + 1, min(y_max, h))
    cropped = img.crop((x_min, y_min, x_max, y_max))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(output_path, "PNG")
    return output_path


def layout_regions_from_docling(
    docling_regions_per_page: List[List[Dict[str, Any]]],
    image_paths: List[Path],
    max_pages: int = 2,
    padding_px: int = 15,
    min_region_height_px: int = 40,
    output_dir: Optional[Path] = None,
) -> List[Path]:
    """
    Crop page images to Docling layout regions (blocks/paragraphs) for describe-then-extract.
    Each region dict has l, t, r, b (floats); optional coord_origin (e.g. bottom-left);
    if values are in 0-1 they are scaled by image size.
    Returns flat list of crop image paths.
    """
    if not PIL_AVAILABLE or not docling_regions_per_page or not image_paths:
        return []
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="vision_docling_"))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    all_crops: List[Path] = []
    for page_idx in range(min(max_pages, len(docling_regions_per_page), len(image_paths))):
        page_path = Path(image_paths[page_idx])
        if not page_path.exists():
            continue
        img = Image.open(page_path).convert("RGB")
        w, h = img.size
        regions = docling_regions_per_page[page_idx]
        stem = page_path.stem
        for idx, reg in enumerate(regions):
            l_ = reg.get("l", 0)
            t_ = reg.get("t", 0)
            r_ = reg.get("r", 0)
            b_ = reg.get("b", 0)
            try:
                l_, t_, r_, b_ = float(l_), float(t_), float(r_), float(b_)
            except (TypeError, ValueError):
                continue
            if r_ <= l_ or b_ <= t_:
                continue
            # Normalized 0-1 -> pixel
            if 0 <= l_ <= 1 and 0 <= t_ <= 1 and 0 <= r_ <= 1 and 0 <= b_ <= 1:
                l_, t_, r_, b_ = l_ * w, t_ * h, r_ * w, b_ * h
            # Docling bottom-left origin: convert to top-left image coords
            co = (reg.get("coord_origin") or "").lower()
            if "bottom" in co or "bottom_left" in co:
                y_min_img = h - b_
                y_max_img = h - t_
                t_, b_ = y_min_img, y_max_img
            x_min = max(0, int(l_) - padding_px)
            y_min = max(0, int(t_) - padding_px)
            x_max = min(w, int(r_) + padding_px)
            y_max = min(h, int(b_) + padding_px)
            if x_max <= x_min + 1 or y_max <= y_min + 1:
                continue
            if y_max - y_min < min_region_height_px:
                continue
            out_path = output_dir / f"{stem}_docling_{page_idx + 1}_{idx}.png"
            _crop_image_to_bbox(page_path, (x_min, y_min, x_max, y_max), out_path)
            all_crops.append(out_path)
    return all_crops


def layout_regions_from_spatial_index(
    spatial_index: "SpatialIndex",
    page_image_path: Path,
    output_dir: Path,
    page_num: int = 1,
    gap_threshold_px: int = 45,
    padding_px: int = 15,
    min_region_height_px: int = 60,
) -> List[Path]:
    """
    Group rows by vertical gap (layout); each group becomes one crop.
    Uses EasyOCR spatial index: rows are already clustered; we merge consecutive
    rows into a region when the gap between them is small, else start a new region.
    Returns paths to saved region images.
    """
    if not PIL_AVAILABLE or not OCR_ENGINE_AVAILABLE or spatial_index is None:
        return []
    rows = getattr(spatial_index, "rows", [])
    if not rows:
        return []
    # Sort by vertical position
    sorted_rows = sorted(rows, key=lambda r: getattr(r, "y_center", r.y_min if hasattr(r, "y_min") else 0))
    regions: List[List[Any]] = []  # list of rows per region
    prev_bottom = -1
    for row in sorted_rows:
        y_min = row.y_min if hasattr(row, "y_min") else min(b.y_min for b in row.blocks)
        y_max = row.y_max if hasattr(row, "y_max") else max(b.y_max for b in row.blocks)
        gap = y_min - prev_bottom if prev_bottom >= 0 else 0
        if gap > gap_threshold_px and regions:
            regions.append([])
        if not regions:
            regions.append([])
        regions[-1].append(row)
        prev_bottom = y_max

    stem = page_image_path.stem
    out_paths: List[Path] = []
    for idx, row_list in enumerate(regions):
        if not row_list:
            continue
        all_blocks = []
        for row in row_list:
            all_blocks.extend(getattr(row, "blocks", []))
        if not all_blocks:
            continue
        x_min = min(b.x_min for b in all_blocks) - padding_px
        y_min = min(b.y_min for b in all_blocks) - padding_px
        x_max = max(b.x_max for b in all_blocks) + padding_px
        y_max = max(b.y_max for b in all_blocks) + padding_px
        region_h = y_max - y_min
        if region_h < min_region_height_px:
            continue
        img = Image.open(page_image_path).convert("RGB")
        w, h = img.size
        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(w, x_max)
        y_max = min(h, y_max)
        if x_max <= x_min or y_max <= y_min:
            continue
        out_path = output_dir / f"{stem}_region_{page_num}_{idx}.png"
        _crop_image_to_bbox(page_image_path, (x_min, y_min, x_max, y_max), out_path)
        out_paths.append(out_path)
    return out_paths


def layout_regions_from_ocr_result(
    ocr_result: "OCRResult",
    max_pages: int = 2,
    gap_threshold_px: int = 45,
    padding_px: int = 15,
    min_region_height_px: int = 60,
    output_dir: Optional[Path] = None,
) -> List[Path]:
    """
    Build layout-based region crops from OCR result (EasyOCR spatial indices).
    Uses row clustering by vertical gap so each logical "section" becomes one crop.
    Returns flat list of crop image paths (Region 1, 2, ... for page 1, then page 2).
    """
    if not OCR_ENGINE_AVAILABLE or ocr_result is None:
        return []
    indices = getattr(ocr_result, "spatial_indices", [])
    paths = getattr(ocr_result, "clean_image_paths", None) or getattr(ocr_result, "image_paths", [])
    if not indices or not paths:
        return []
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="vision_layout_"))
    all_crops: List[Path] = []
    for page_idx in range(min(max_pages, len(indices), len(paths))):
        page_path = Path(paths[page_idx])
        if not page_path.exists():
            continue
        crops = layout_regions_from_spatial_index(
            indices[page_idx],
            page_path,
            output_dir,
            page_num=page_idx + 1,
            gap_threshold_px=gap_threshold_px,
            padding_px=padding_px,
            min_region_height_px=min_region_height_px,
        )
        all_crops.extend(crops)
    return all_crops


def regions_from_bbox_pages(
    bbox_pages: List[List[Dict[str, Any]]],
    image_paths: List[Path],
    max_pages: int = 2,
    gap_threshold_px: int = 45,
    padding_px: int = 15,
    min_region_height_px: int = 60,
    output_dir: Optional[Path] = None,
) -> List[Path]:
    """
    Build layout-based regions from raw EasyOCR bbox data (no SpatialIndex).
    Clusters bboxes by Y position into rows, then groups rows by vertical gap.
    Use when spatial_indices are not available.
    """
    if not PIL_AVAILABLE or not bbox_pages or not image_paths:
        return []
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="vision_layout_"))
    all_crops: List[Path] = []
    for page_idx in range(min(max_pages, len(bbox_pages), len(image_paths))):
        page_bbox = bbox_pages[page_idx]
        page_path = Path(image_paths[page_idx])
        if not page_path.exists() or not page_bbox:
            continue
        # Cluster into rows by y (center or y_min)
        sorted_bbox = sorted(page_bbox, key=lambda d: (d.get("y_min", d.get("y", 0)), d.get("x_min", d.get("x", 0))))
        row_tol = 35
        rows: List[List[Dict]] = []
        for b in sorted_bbox:
            y = b.get("y_min", b.get("y", 0))
            if rows and abs(y - (rows[-1][0].get("y_min", rows[-1][0].get("y", 0)))) <= row_tol:
                rows[-1].append(b)
            else:
                rows.append([b])
        # Group rows by gap
        regions: List[List[Dict]] = []
        prev_bottom = -1
        for row in rows:
            y_min = min(d.get("y_min", d.get("y", 0)) for d in row)
            y_max = max(d.get("y_max", d.get("y", 0) + d.get("height", 0)) for d in row)
            gap = y_min - prev_bottom if prev_bottom >= 0 else 0
            if gap > gap_threshold_px and regions:
                regions.append([])
            if not regions:
                regions.append([])
            regions[-1].extend(row)
            prev_bottom = y_max
        # Bbox per region + crop
        img = Image.open(page_path).convert("RGB")
        w, h = img.size
        stem = page_path.stem
        for idx, region_boxes in enumerate(regions):
            if not region_boxes:
                continue
            x_min = min(d.get("x_min", d.get("x", 0)) for d in region_boxes) - padding_px
            y_min = min(d.get("y_min", d.get("y", 0)) for d in region_boxes) - padding_px
            x_max = max(d.get("x_max", d.get("x", 0) + d.get("width", 0)) for d in region_boxes) + padding_px
            y_max = max(d.get("y_max", d.get("y", 0) + d.get("height", 0)) for d in region_boxes) + padding_px
            if y_max - y_min < min_region_height_px:
                continue
            x_min, y_min = max(0, x_min), max(0, y_min)
            x_max, y_max = min(w, x_max), min(h, y_max)
            if x_max <= x_min or y_max <= y_min:
                continue
            out_path = output_dir / f"{stem}_region_{page_idx + 1}_{idx}.png"
            _crop_image_to_bbox(page_path, (x_min, y_min, x_max, y_max), out_path)
            all_crops.append(out_path)
    return all_crops
