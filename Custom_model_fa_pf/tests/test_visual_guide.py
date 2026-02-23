"""Tests for visual form guide generation."""

import pytest
from pathlib import Path
from Custom_model_fa_pf.visual_guide import (
    generate_field_overlay,
    FieldHighlight,
)
from Custom_model_fa_pf.config import FORM_TEMPLATES_DIR


class TestFieldHighlight:
    def test_create_highlight(self):
        h = FieldHighlight(
            field_name="NamedInsured_FullName_A",
            value="Acme LLC",
            rect=(100.0, 200.0, 400.0, 220.0),
            page=0,
            status="confirmed",
        )
        assert h.color == (0, 200, 0, 80)  # Green for confirmed

    def test_pending_is_yellow(self):
        h = FieldHighlight(
            field_name="test", value="", rect=(0, 0, 100, 20),
            page=0, status="pending",
        )
        assert h.color == (255, 200, 0, 80)

    def test_error_is_red(self):
        h = FieldHighlight(
            field_name="test", value="BAD", rect=(0, 0, 100, 20),
            page=0, status="error",
        )
        assert h.color == (255, 0, 0, 80)


@pytest.mark.skipif(
    not FORM_TEMPLATES_DIR.exists(),
    reason="Template directory not found",
)
class TestGenerateOverlay:
    def test_generate_for_form_125(self):
        from Custom_model_fa_pf.form_reader import find_template, read_pdf_form

        path = find_template("125")
        if path is None:
            pytest.skip("Form 125 template not found")

        catalog = read_pdf_form(path)
        # Pick a few fields that have rects
        fields_with_rects = [
            f for f in catalog.fields.values() if f.rect is not None
        ][:5]

        highlights = [
            FieldHighlight(
                field_name=f.name,
                value="Test Value",
                rect=f.rect,
                page=f.page,
                status="confirmed",
            )
            for f in fields_with_rects
        ]

        images = generate_field_overlay(path, highlights)
        assert len(images) > 0
        # Each image should be a bytes object (PNG)
        for img_bytes in images.values():
            assert img_bytes[:4] == b'\x89PNG'
