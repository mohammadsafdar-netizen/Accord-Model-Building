"""End-to-end pipeline tests — requires Ollama with model running."""

import pytest
import tempfile
from pathlib import Path

from Custom_model_fa_pf.tests.sample_emails import COMMERCIAL_AUTO_FULL, MULTI_LOB_AUTO_UMBRELLA


@pytest.mark.integration
class TestPipelineE2E:
    """Integration tests that require a running Ollama instance."""

    def test_commercial_auto_full_pipeline(self):
        """Full pipeline with commercial auto email."""
        from Custom_model_fa_pf.pipeline import run

        with tempfile.TemporaryDirectory() as tmp:
            result = run(
                email_text=COMMERCIAL_AUTO_FULL,
                output_dir=Path(tmp),
                json_only=True,
                show_gaps=True,
            )

        # Should classify as commercial_auto
        assert len(result.lobs) >= 1
        lob_ids = [l.lob_id for l in result.lobs]
        assert "commercial_auto" in lob_ids

        # Should assign forms 125, 127, 137
        form_nums = [a.form_number for a in result.assignments]
        assert "125" in form_nums
        assert "127" in form_nums
        assert "137" in form_nums

        # Should extract business name
        assert result.entities is not None
        assert result.entities.business is not None
        assert result.entities.business.business_name is not None

        # Should have field mappings
        assert "125" in result.field_values
        assert len(result.field_values["125"]) > 5

        # Should have gap report
        assert result.gap_report is not None

    def test_multi_lob_auto_umbrella(self):
        """Multi-LOB pipeline: auto + umbrella."""
        from Custom_model_fa_pf.pipeline import run

        with tempfile.TemporaryDirectory() as tmp:
            result = run(
                email_text=MULTI_LOB_AUTO_UMBRELLA,
                output_dir=Path(tmp),
                json_only=True,
            )

        lob_ids = [l.lob_id for l in result.lobs]
        assert "commercial_auto" in lob_ids
        assert "commercial_umbrella" in lob_ids

        # Should have 4 forms: 125, 127, 137, 163
        form_nums = {a.form_number for a in result.assignments}
        assert form_nums >= {"125", "127", "137", "163"}

        # Form 125 should appear exactly once
        form_125_count = sum(1 for a in result.assignments if a.form_number == "125")
        assert form_125_count == 1

    def test_entities_extraction(self):
        """Verify entity extraction quality."""
        from Custom_model_fa_pf.pipeline import run

        with tempfile.TemporaryDirectory() as tmp:
            result = run(
                email_text=COMMERCIAL_AUTO_FULL,
                output_dir=Path(tmp),
                json_only=True,
            )

        ent = result.entities
        assert ent is not None

        # Business info
        assert ent.business is not None
        biz = ent.business
        assert biz.business_name is not None
        assert biz.tax_id is not None

        # Should have vehicles and drivers
        assert len(ent.vehicles) >= 1
        assert len(ent.drivers) >= 1
