"""
Pytest fixtures and configuration for best_project.
Run from project root: pytest tests/ -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure project root is on path when running tests
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def project_root() -> Path:
    """Project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def schemas_dir(project_root: Path) -> Path:
    """Path to schemas directory."""
    return project_root / "schemas"


@pytest.fixture
def test_data_dir(project_root: Path) -> Path:
    """Path to test_data directory."""
    return project_root / "test_data"


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Temporary directory for test outputs."""
    return tmp_path / "test_output"


@pytest.fixture
def sample_schema_125(schemas_dir: Path) -> Path:
    """Path to ACORD 125 schema JSON (if present)."""
    p = schemas_dir / "125.json"
    if not p.exists():
        pytest.skip("schemas/125.json not found")
    return p
