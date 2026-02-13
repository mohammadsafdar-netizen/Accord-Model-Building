"""
E2E extraction test — runs full pipeline when test_data and GPU are available.
Skip by default: pytest tests/ (excludes e2e). Run on Eureka: pytest tests/ -m e2e -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Mark all tests in this module as e2e (need GPU + test data)
pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def test_data_dir():
    from config import TEST_DATA_DIR
    return TEST_DATA_DIR


def test_discover_test_forms(test_data_dir: Path):
    """Discovery: test_data has at least one form folder with PDF+JSON."""
    if not test_data_dir.exists():
        pytest.skip("test_data not found (set BEST_PROJECT_TEST_DATA or run from project root)")
    subdirs = [d for d in test_data_dir.iterdir() if d.is_dir()]
    assert len(subdirs) >= 1, "test_data should have at least one form subfolder"
    # At least one PDF in some folder
    pdfs = list(test_data_dir.rglob("*.pdf"))
    assert len(pdfs) >= 1, "test_data should contain at least one PDF"


def test_schemas_dir_exists():
    """Schemas directory exists and has JSON files."""
    from config import SCHEMAS_DIR
    if not SCHEMAS_DIR.exists():
        pytest.skip("schemas dir not found")
    jsons = list(SCHEMAS_DIR.glob("*.json"))
    assert len(jsons) >= 1, "schemas dir should have at least one .json"
