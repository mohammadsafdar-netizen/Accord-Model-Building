#!/usr/bin/env python3
"""
Image Aligner: SIFT feature matching + homography warp
========================================================
Aligns scanned form images to canonical template images for
improved positional field matching accuracy.

Usage:
    from image_aligner import align_to_template, get_template_image
    aligned_path, H = align_to_template(scan.png, template.png, out.png)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def align_to_template(
    scanned_img_path: Path,
    template_img_path: Path,
    output_path: Path,
    nfeatures: int = 2000,
    ratio_threshold: float = 0.75,
    ransac_threshold: float = 5.0,
) -> Tuple[Path, Optional[np.ndarray]]:
    """SIFT feature matching + homography warp. Returns (aligned_path, H_matrix).

    If alignment fails (too few matches, bad homography), returns original image path
    and None for the homography matrix.
    """
    if not CV2_AVAILABLE:
        raise RuntimeError("opencv-python is required for image alignment")

    scan_img = cv2.imread(str(scanned_img_path))
    template_img = cv2.imread(str(template_img_path))

    if scan_img is None:
        raise ValueError(f"Could not read scanned image: {scanned_img_path}")
    if template_img is None:
        raise ValueError(f"Could not read template image: {template_img_path}")

    scan_gray = cv2.cvtColor(scan_img, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)

    # 1. SIFT detector
    sift = cv2.SIFT_create(nfeatures=nfeatures)
    kp1, des1 = sift.detectAndCompute(scan_gray, None)
    kp2, des2 = sift.detectAndCompute(template_gray, None)

    if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
        print(f"    [ALIGN] Too few features detected, skipping alignment")
        return scanned_img_path, None

    # 2. BFMatcher with KNN
    bf = cv2.BFMatcher(cv2.NORM_L2)
    matches = bf.knnMatch(des1, des2, k=2)

    # 3. Lowe's ratio test
    good_matches = []
    for m_pair in matches:
        if len(m_pair) == 2:
            m, n = m_pair
            if m.distance < ratio_threshold * n.distance:
                good_matches.append(m)

    if len(good_matches) < 10:
        print(f"    [ALIGN] Only {len(good_matches)} good matches (need 10+), skipping alignment")
        return scanned_img_path, None

    # 4. Find homography
    src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, ransac_threshold)

    if H is None:
        print(f"    [ALIGN] Homography computation failed, skipping alignment")
        return scanned_img_path, None

    # 5. Validate homography: check determinant ~1 (no extreme scaling)
    det = np.linalg.det(H[:2, :2])
    if det < 0.5 or det > 2.0:
        print(f"    [ALIGN] Bad homography determinant ({det:.2f}), skipping alignment")
        return scanned_img_path, None

    # 6. Warp scan to template coordinates
    h_t, w_t = template_gray.shape[:2]
    aligned = cv2.warpPerspective(
        scan_img, H, (w_t, h_t),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), aligned)

    inliers = int(mask.sum()) if mask is not None else 0
    print(f"    [ALIGN] Aligned with {inliers}/{len(good_matches)} inlier matches (det={det:.3f})")

    return output_path, H


def get_template_image(form_type: str, page: int) -> Optional[Path]:
    """Get canonical template image for form type + page.

    Looks for templates/canonical_{form_type}_p{page}.png
    """
    template_path = TEMPLATES_DIR / f"canonical_{form_type}_p{page}.png"
    if template_path.exists():
        return template_path
    return None
