#!/usr/bin/env python3
"""
Run Docling OCR in a subprocess with no GPU (CUDA_VISIBLE_DEVICES="").
Used by ocr_engine when Docling is requested on CPU to avoid OOM when
another process (e.g. Ollama) holds GPU memory. Docling's internal EasyOCR
would otherwise try to use GPU and fail.

Usage (called by ocr_engine, not directly by users):
  CUDA_VISIBLE_DEVICES="" python run_docling_cpu_worker.py --images page1.png page2.png --out result.pkl
"""

from __future__ import annotations

import argparse
import os
import pickle
import sys
from pathlib import Path

# Ensure this process sees no GPU before any torch/CUDA import
if os.environ.get("CUDA_VISIBLE_DEVICES", "").strip() != "":
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

# Now safe to import docling (will use CPU only)
try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
except ImportError as e:
    print(f"Docling not available: {e}", file=sys.stderr)
    sys.exit(1)


def _extract_regions(doc) -> list:
    out = []
    if doc is None:
        return out
    try:
        it = getattr(doc, "iterate_items", None)
        if it is None:
            return out
        for item, _ in it():
            prov_list = getattr(item, "prov", None)
            if not prov_list or not isinstance(prov_list, (list, tuple)):
                continue
            prov = prov_list[0]
            bbox = getattr(prov, "bbox", None)
            if bbox is None:
                continue
            l_ = getattr(bbox, "l", getattr(bbox, "left", None))
            t_ = getattr(bbox, "t", getattr(bbox, "top", None))
            r_ = getattr(bbox, "r", getattr(bbox, "right", None))
            b_ = getattr(bbox, "b", getattr(bbox, "bottom", None))
            if l_ is not None and t_ is not None and r_ is not None and b_ is not None:
                out.append({"l": float(l_), "t": float(t_), "r": float(r_), "b": float(b_)})
    except Exception:
        pass
    return out


def _extract_native_pairs(doc) -> list:
    pairs = []
    if doc is None:
        return pairs
    try:
        kv_list = getattr(doc, "key_value_items", None)
        if isinstance(kv_list, (list, tuple)):
            for item in kv_list:
                key = getattr(item, "key", None)
                val = getattr(item, "value", None) or getattr(item, "text", None)
                if key is not None and val is not None:
                    k, v = str(key).strip(), str(val).strip()
                    if k and v:
                        pairs.append((k, v))
        tables = getattr(doc, "tables", None)
        if isinstance(tables, (list, tuple)):
            for table in tables:
                export_df = getattr(table, "export_to_dataframe", None)
                if export_df is not None:
                    try:
                        df = export_df(doc=doc)
                        if df is not None and not df.empty:
                            for _, row in df.iterrows():
                                for c in df.columns:
                                    h, v = str(c).strip(), str(row.get(c, "")).strip()
                                    if h and v:
                                        pairs.append((h, v))
                    except Exception:
                        pass
    except Exception:
        pass
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", nargs="+", required=True, help="Page image paths")
    ap.add_argument("--out", required=True, help="Output pickle path (pages, regions, native_pairs)")
    args = ap.parse_args()

    acc_opts = AcceleratorOptions(num_threads=4, device=AcceleratorDevice.CPU)
    pipe_opts = PdfPipelineOptions()
    pipe_opts.accelerator_options = acc_opts
    pipe_opts.do_ocr = True
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipe_opts)}
    )

    pages = []
    regions_per_page = []
    native_pairs_per_page = []
    for img_path in args.images:
        try:
            result = converter.convert(img_path)
            doc = result.document
            pages.append(doc.export_to_markdown())
            regions_per_page.append(_extract_regions(doc))
            native_pairs_per_page.append(_extract_native_pairs(doc))
        except Exception as e:
            pages.append(f"[Docling OCR error: {e}]")
            regions_per_page.append([])
            native_pairs_per_page.append([])

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        pickle.dump((pages, regions_per_page, native_pairs_per_page), f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
