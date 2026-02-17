#!/usr/bin/env python3
"""
Image Preprocessor: Deskew + Denoise + Binarize + CLAHE
========================================================
Prepares scanned form images for better OCR accuracy.

Pipeline:
  1. Load grayscale
  2. Deskew via deskew.determine_skew() + cv2.warpAffine()
  3. Denoise via cv2.fastNlMeansDenoising(h=10)
  4. Binarize via cv2.threshold(THRESH_BINARY + THRESH_OTSU)
  5. CLAHE contrast enhancement
  6. Save to output_path

Usage:
    from image_preprocessor import preprocess_for_ocr
    preprocessed = preprocess_for_ocr(Path("scan.png"), Path("output/"))
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from deskew import determine_skew
    DESKEW_AVAILABLE = True
except ImportError:
    DESKEW_AVAILABLE = False


def preprocess_image(image_path: Path, output_path: Path) -> Path:
    """Deskew + denoise + binarize + CLAHE. Returns preprocessed image path."""
    if not CV2_AVAILABLE:
        raise RuntimeError("opencv-python is required for image preprocessing")

    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Deskew
    if DESKEW_AVAILABLE:
        angle = determine_skew(gray)
        if angle is not None and abs(angle) > 0.1:
            (h, w) = gray.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            gray = cv2.warpAffine(
                gray, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )

    # 2. Denoise
    gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

    # 3. Binarize (Otsu's threshold)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 4. CLAHE contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(binary)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), enhanced)
    return output_path


def preprocess_for_ocr(image_path: Path, output_dir: Path) -> Path:
    """Wrapper: creates preprocessed copy in output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{image_path.stem}_preprocessed.png"
    return preprocess_image(image_path, out_path)
