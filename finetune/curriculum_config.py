"""Curriculum training configuration for multi-phase fine-tuning.

Defines PhaseConfig and CurriculumConfig dataclasses for structured
multi-phase training (general → hard → error-specific).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import json


@dataclass
class PhaseConfig:
    """Configuration for a single training phase."""

    name: str           # "general", "hard", "error_specific"
    data_path: Path     # Path to JSONL training file
    epochs: int = 1
    lr: float = 2e-4
    warmup_ratio: float = 0.1

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "data_path": str(self.data_path),
            "epochs": self.epochs,
            "lr": self.lr,
            "warmup_ratio": self.warmup_ratio,
        }

    @classmethod
    def from_dict(cls, d: dict) -> PhaseConfig:
        return cls(
            name=d["name"],
            data_path=Path(d["data_path"]),
            epochs=d.get("epochs", 1),
            lr=d.get("lr", 2e-4),
            warmup_ratio=d.get("warmup_ratio", 0.1),
        )


@dataclass
class CurriculumConfig:
    """Multi-phase curriculum training configuration."""

    phases: list[PhaseConfig] = field(default_factory=list)

    @classmethod
    def default_3phase(cls, data_dir: Path) -> CurriculumConfig:
        """Create a default 3-phase curriculum: general → hard → error-specific.

        LR decays across phases (2e-4 → 1e-4 → 5e-5) to prevent forgetting.
        """
        return cls(phases=[
            PhaseConfig("general", data_dir / "train.jsonl", epochs=2, lr=2e-4),
            PhaseConfig("hard", data_dir / "hard_examples.jsonl", epochs=2, lr=1e-4),
            PhaseConfig("error_specific", data_dir / "error_examples.jsonl", epochs=1, lr=5e-5),
        ])

    def to_dict(self) -> dict:
        return {"phases": [p.to_dict() for p in self.phases]}

    @classmethod
    def from_dict(cls, d: dict) -> CurriculumConfig:
        return cls(phases=[PhaseConfig.from_dict(p) for p in d["phases"]])

    @classmethod
    def from_json(cls, path: Path) -> CurriculumConfig:
        """Load curriculum config from a JSON file."""
        data = json.loads(path.read_text())
        return cls.from_dict(data)

    def save_json(self, path: Path) -> None:
        """Save curriculum config to a JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))
