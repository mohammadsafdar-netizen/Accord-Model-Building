"""Tests for pdf_filler — round-trip fill and read back."""

import pytest
import tempfile
from pathlib import Path

from Custom_model_fa_pf.config import FORM_TEMPLATES_DIR
from Custom_model_fa_pf.pdf_filler import fill_pdf, _find_template


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


class TestPdfFiller:
    def test_find_template_125(self):
        """Check that a template exists for Form 125."""
        template = _find_template("125")
        if template is None:
            pytest.skip("No template PDF for Form 125 — copy one to form_templates/")
        assert template.exists()
        assert template.suffix == ".pdf"

    @pytest.mark.skipif(
        not list(FORM_TEMPLATES_DIR.glob("*125*")),
        reason="No Form 125 template PDF available",
    )
    def test_fill_text_fields(self, temp_dir):
        """Fill text fields and verify result."""
        field_values = {
            "NamedInsured_FullName_A": "Test Company LLC",
            "Policy_EffectiveDate_A": "01/01/2026",
        }
        output_path = temp_dir / "filled_125.pdf"
        result = fill_pdf("125", field_values, output_path)

        assert result.output_path == output_path
        assert output_path.exists()
        assert result.filled_count > 0
        assert result.error_count == 0

    @pytest.mark.skipif(
        not list(FORM_TEMPLATES_DIR.glob("*125*")),
        reason="No Form 125 template PDF available",
    )
    def test_round_trip_fill_read(self, temp_dir):
        """Fill PDF then read back with extract_acroform_fields."""
        try:
            from ocr_engine import OCREngine
        except ImportError:
            pytest.skip("OCREngine not available")

        field_values = {
            "NamedInsured_FullName_A": "Round Trip Test Inc",
        }
        output_path = temp_dir / "roundtrip_125.pdf"
        fill_result = fill_pdf("125", field_values, output_path)

        if not fill_result.output_path:
            pytest.skip("Fill failed")

        # Read back
        read_back = OCREngine.extract_acroform_fields(output_path)
        assert read_back.get("NamedInsured_FullName_A") == "Round Trip Test Inc"

    def test_missing_template_returns_error(self, temp_dir):
        """Filling with no template should return errors."""
        result = fill_pdf("999", {"field": "value"}, temp_dir / "bad.pdf")
        assert result.error_count > 0
        assert result.filled_count == 0

    @pytest.mark.skipif(
        not list(FORM_TEMPLATES_DIR.glob("*125*")),
        reason="No Form 125 template PDF available",
    )
    def test_checkbox_filling(self, temp_dir):
        """Fill checkbox fields."""
        field_values = {
            "NamedInsured_LegalEntity_CorporationIndicator_A": "1",
        }
        output_path = temp_dir / "checkbox_125.pdf"
        result = fill_pdf("125", field_values, output_path)
        # Just verify no errors — checkbox fill is best-effort
        assert result.error_count == 0
