"""Stage 1: Classify customer email into insurance lines of business."""

import json
import logging
from dataclasses import dataclass
from typing import List, Optional

from Custom_model_fa_pf.config import DEFAULT_CONFIDENCE_THRESHOLD
from Custom_model_fa_pf.prompts import CLASSIFICATION_SYSTEM, CLASSIFICATION_PROMPT
from Custom_model_fa_pf.lob_rules import LOB_DEFINITIONS

logger = logging.getLogger(__name__)


@dataclass
class LOBClassification:
    lob_id: str
    confidence: float
    reasoning: str
    display_name: str = ""

    def __post_init__(self):
        if not self.display_name and self.lob_id in LOB_DEFINITIONS:
            self.display_name = LOB_DEFINITIONS[self.lob_id].display_name

    def to_dict(self):
        return {
            "lob_id": self.lob_id,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "display_name": self.display_name,
        }


def classify(
    email_text: str,
    llm_engine,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> List[LOBClassification]:
    """Classify email text into LOBs using LLM.

    Args:
        email_text: Raw customer email/message text
        llm_engine: LLMEngine instance for text generation
        confidence_threshold: Minimum confidence to include a LOB

    Returns:
        List of LOBClassification sorted by confidence descending
    """
    prompt = CLASSIFICATION_PROMPT.format(email_text=email_text)

    logger.info("Classifying LOBs from email...")
    response = llm_engine.generate(prompt=prompt, system=CLASSIFICATION_SYSTEM)
    parsed = llm_engine.parse_json(response)

    if not parsed or "lobs" not in parsed:
        logger.warning("Failed to parse LOB classification response")
        return []

    results = []
    for lob_data in parsed["lobs"]:
        lob_id = lob_data.get("lob_id", "")
        confidence = float(lob_data.get("confidence", 0))

        # Only include known LOBs above threshold
        if lob_id in LOB_DEFINITIONS and confidence >= confidence_threshold:
            results.append(
                LOBClassification(
                    lob_id=lob_id,
                    confidence=confidence,
                    reasoning=lob_data.get("reasoning", ""),
                )
            )

    results.sort(key=lambda x: x.confidence, reverse=True)
    logger.info(f"Classified {len(results)} LOBs: {[r.lob_id for r in results]}")
    return results
