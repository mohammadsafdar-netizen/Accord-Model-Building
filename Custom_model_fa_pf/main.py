"""CLI entry point for the ACORD Form Assignment & Pre-Filling CoPilot."""

import argparse
import logging
import sys
from pathlib import Path

# Ensure project root is in path
from Custom_model_fa_pf.config import ROOT, DEFAULT_MODEL, DEFAULT_OLLAMA_URL, DEFAULT_CONFIDENCE_THRESHOLD
from Custom_model_fa_pf import pipeline


def main():
    parser = argparse.ArgumentParser(
        description="ACORD Form Assignment & Pre-Filling CoPilot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From inline text
  python -m Custom_model_fa_pf.main --email "We need commercial auto insurance for our 3 trucks..."

  # From file
  python -m Custom_model_fa_pf.main --email-file customer_request.txt

  # JSON only (no PDF filling)
  python -m Custom_model_fa_pf.main --email "..." --json-only

  # With gap analysis
  python -m Custom_model_fa_pf.main --email "..." --show-gaps --verbose

  # Custom model
  python -m Custom_model_fa_pf.main --email "..." --model qwen3:8b
        """,
    )

    # Input
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--email", type=str, help="Customer email/message text")
    input_group.add_argument("--email-file", type=Path, help="Path to email text file")

    # Output
    parser.add_argument("--output-dir", type=Path, help="Output directory (auto-generated if not set)")
    parser.add_argument("--json-only", action="store_true", help="Skip PDF filling, output JSON only")

    # Analysis
    parser.add_argument("--show-gaps", action="store_true", help="Run gap analysis and suggest follow-up questions")

    # Model
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help=f"Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--ollama-url", type=str, default=DEFAULT_OLLAMA_URL, help="Ollama API URL")
    parser.add_argument(
        "--confidence-threshold", type=float, default=DEFAULT_CONFIDENCE_THRESHOLD,
        help=f"Minimum LOB confidence threshold (default: {DEFAULT_CONFIDENCE_THRESHOLD})",
    )

    # Logging
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--debug", action="store_true", help="Debug logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.WARNING
    if args.verbose:
        log_level = logging.INFO
    if args.debug:
        log_level = logging.DEBUG
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Get email text
    if args.email_file:
        if not args.email_file.exists():
            print(f"Error: file not found: {args.email_file}")
            sys.exit(1)
        email_text = args.email_file.read_text()
    else:
        email_text = args.email

    if not email_text.strip():
        print("Error: empty email text")
        sys.exit(1)

    # Run pipeline
    result = pipeline.run(
        email_text=email_text,
        output_dir=args.output_dir,
        json_only=args.json_only,
        show_gaps=args.show_gaps,
        model=args.model,
        ollama_url=args.ollama_url,
        confidence_threshold=args.confidence_threshold,
        verbose=args.verbose,
    )

    # Exit code based on results
    if not result.lobs:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
