"""Stage 2: Extract structured entities from customer email text."""

import logging
from typing import Optional

from Custom_model_fa_pf.prompts import EXTRACTION_SYSTEM, EXTRACTION_PROMPT
from Custom_model_fa_pf.entity_schema import CustomerSubmission

logger = logging.getLogger(__name__)


def extract(
    email_text: str,
    llm_engine,
    knowledge_store=None,
) -> CustomerSubmission:
    """Extract structured entities from email using LLM.

    Args:
        email_text: Raw customer email/message text
        llm_engine: LLMEngine instance for text generation
        knowledge_store: Optional InsuranceKnowledgeStore for context enrichment

    Returns:
        CustomerSubmission with all extracted entities
    """
    # Build optional knowledge context
    knowledge_context = ""
    if knowledge_store:
        try:
            results = knowledge_store.query_all(email_text, n_results=3)
            if results:
                context = knowledge_store.format_context(results, max_chars=2000)
                knowledge_context = f"\nRelevant insurance context:\n{context}\n"
        except Exception as e:
            logger.warning(f"Knowledge store query failed: {e}")

    prompt = EXTRACTION_PROMPT.format(
        email_text=email_text,
        knowledge_context=knowledge_context,
    )

    logger.info("Extracting entities from email...")
    response = llm_engine.generate(
        prompt=prompt,
        system=EXTRACTION_SYSTEM,
        max_tokens=4096,
    )
    parsed = llm_engine.parse_json(response)

    if not parsed:
        logger.warning("Failed to parse entity extraction response")
        return CustomerSubmission(raw_email=email_text)

    submission = CustomerSubmission.from_llm_json(parsed)
    submission.raw_email = email_text

    # Log extraction summary
    summary_parts = []
    if submission.business and submission.business.business_name:
        summary_parts.append(f"business={submission.business.business_name}")
    if submission.vehicles:
        summary_parts.append(f"vehicles={len(submission.vehicles)}")
    if submission.drivers:
        summary_parts.append(f"drivers={len(submission.drivers)}")
    if submission.coverages:
        summary_parts.append(f"coverages={len(submission.coverages)}")
    logger.info(f"Extracted entities: {', '.join(summary_parts) or 'minimal data'}")

    return submission
