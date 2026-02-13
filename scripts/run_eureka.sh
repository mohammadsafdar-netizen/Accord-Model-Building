#!/usr/bin/env bash
# Run best_project on Eureka: set env from project root and run tests or extraction.
# Usage:
#   ./scripts/run_eureka.sh                    # run unit tests (no GPU)
#   ./scripts/run_eureka.sh e2e                # run e2e tests (GPU + test_data)
#   ./scripts/run_eureka.sh pipeline            # run full test_pipeline.py (all forms)
#   ./scripts/run_eureka.sh extract <pdf>       # run main.py on one PDF

set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

export BEST_PROJECT_ROOT="$ROOT"
export BEST_PROJECT_TEST_DATA="${BEST_PROJECT_TEST_DATA:-$ROOT/test_data}"
export BEST_PROJECT_OUTPUT="${BEST_PROJECT_OUTPUT:-$ROOT/test_output}"
export BEST_PROJECT_SCHEMAS="${BEST_PROJECT_SCHEMAS:-$ROOT/schemas}"
# Optional: use GPU by default on Eureka
export USE_GPU="${USE_GPU:-1}"

echo "BEST_PROJECT_ROOT=$BEST_PROJECT_ROOT"
echo "TEST_DATA=$BEST_PROJECT_TEST_DATA"
echo "OUTPUT=$BEST_PROJECT_OUTPUT"

case "${1:-tests}" in
  tests)
    pytest tests/ -v -m "not e2e"
    ;;
  e2e)
    pytest tests/ -v -m e2e
    ;;
  pipeline)
    # Pass extra flags after pipeline, e.g. pipeline --use-rag or pipeline --vision --vision-model llava:7b
    python test_pipeline.py --gpu "${@:2}"
    ;;
  extract)
    if [ -z "${2:-}" ]; then
      echo "Usage: $0 extract <path/to/form.pdf> [--form-type 125|127|137]"
      exit 1
    fi
    python main.py "$2" --docling --gpu --text-llm "${@:3}"
    ;;
  *)
    echo "Usage: $0 [tests|e2e|pipeline|extract [pdf]]"
    exit 1
    ;;
esac
