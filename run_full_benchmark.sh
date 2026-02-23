#!/bin/bash
# Comprehensive Flag Benchmark: 19 configs x 4 forms (one-per-form)
# Tests all meaningful flag combinations against the finetuned VLM via vLLM.
#
# Prerequisites:
#   - vLLM running with: --max-model-len 16384
#   - Ollama running for text LLM (qwen2.5:7b)
#
# Usage: bash run_full_benchmark.sh [config_name ...]
#   No args = run all configs
#   With args = run only named configs, e.g.: bash run_full_benchmark.sh default_all vlm_only

set -euo pipefail
cd "$(dirname "$0")"

MODEL_PATH="/home/inevoai/Development/Accord-Model-Building/finetune/export/merged_full"
COMMON="--gpu --one-per-form --vlm-extract --vlm-extract-model $MODEL_PATH --vllm-base-url http://localhost:8000"
RESULTS_DIR="benchmark_results/full"
PYTHON=".venv/bin/python"

mkdir -p "$RESULTS_DIR"

# Track timing
BENCH_START=$(date +%s)

run_config() {
    local name="$1"
    shift
    local flags="$*"

    # If specific configs requested, skip others
    if [ ${#SELECTED[@]} -gt 0 ]; then
        local found=0
        for sel in "${SELECTED[@]}"; do
            if [ "$sel" = "$name" ]; then found=1; break; fi
        done
        if [ $found -eq 0 ]; then
            echo "  [SKIP] $name (not in selection)"
            return 0
        fi
    fi

    # Skip if already completed
    local outfile="$RESULTS_DIR/${name}.log"
    if [ -f "$outfile" ] && grep -q "OVERALL SUMMARY" "$outfile" 2>/dev/null; then
        echo "  [SKIP] $name (already completed — delete $outfile to re-run)"
        return 0
    fi

    echo ""
    echo "=================================================================="
    echo "  CONFIG: $name"
    echo "  FLAGS:  $COMMON $flags"
    echo "  START:  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=================================================================="

    local start_ts=$(date +%s)
    $PYTHON test_pipeline.py $COMMON $flags 2>&1 | tee "$outfile"
    local end_ts=$(date +%s)
    local elapsed=$((end_ts - start_ts))

    echo ""
    echo "--- $name DONE (${elapsed}s) ---"
    echo ""
}

# Parse optional config selection
SELECTED=()
for arg in "$@"; do
    SELECTED+=("$arg")
done

echo "=================================================================="
echo "  COMPREHENSIVE FLAG BENCHMARK"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "  Configs: ${#SELECTED[@]} selected (0 = all)"
echo "  Results: $RESULTS_DIR/"
echo "=================================================================="

# ─── Baseline configs ───────────────────────────────────────────────
# 1. True default: all defaults ON (VLM+LLM+multimodal+smart-ensemble+positional+semantic)
run_config "01_default_all"

# 2. Disable semantic matching
run_config "02_no_semantic" --no-semantic-matching

# ─── VLM-only configs (no text LLM) ────────────────────────────────
# 3. VLM + positional only (fastest possible)
run_config "03_vlm_only" --no-text-llm --no-multimodal

# 4. VLM + multimodal, no text LLM
run_config "04_vlm_multimodal" --no-text-llm

# 5. VLM + checkbox crops only (no text LLM, no multimodal)
run_config "05_vlm_checkbox" --no-text-llm --no-multimodal --checkbox-crops

# 6. VLM + multimodal + checkbox crops (no text LLM)
run_config "06_vlm_cb_mm" --no-text-llm --checkbox-crops

# ─── Full pipeline ablations ───────────────────────────────────────
# 7. Default minus multimodal
run_config "07_no_multimodal" --no-multimodal

# 8. Default + checkbox crops (multimodal already ON)
run_config "08_checkbox" --checkbox-crops

# 9. Default + cross-field validation
run_config "09_validate" --validate-fields

# 10. Default + dual LLM verification
run_config "10_dual_llm" --dual-llm-validate

# 11. Default + image preprocessing (deskew+denoise+binarize+CLAHE)
run_config "11_preprocess" --preprocess

# 12. Default + cropped VLM regions
run_config "12_vlm_crop" --vlm-crop-extract

# ─── Confidence routing ablations ──────────────────────────────────
# 13. Default without confidence routing
run_config "13_no_routing" --no-confidence-routing

# 14. Lower routing threshold (0.85)
run_config "14_threshold_85" --confidence-threshold 0.85

# 15. Higher routing threshold (0.95)
run_config "15_threshold_95" --confidence-threshold 0.95

# ─── Feature ablations ─────────────────────────────────────────────
# 16. Default without positional atlas
run_config "16_no_positional" --no-positional

# 17. Default + template anchoring
run_config "17_templates" --use-templates

# 18. Default + table transformer
run_config "18_table_tf" --table-transformer

# ─── Kitchen sink ──────────────────────────────────────────────────
# 19. Everything ON
run_config "19_kitchen_sink" --checkbox-crops --validate-fields --preprocess --vlm-crop-extract --dual-llm-validate --use-templates

BENCH_END=$(date +%s)
BENCH_ELAPSED=$((BENCH_END - BENCH_START))

echo ""
echo "=================================================================="
echo "  ALL CONFIGS COMPLETE (total: ${BENCH_ELAPSED}s)"
echo "=================================================================="
echo ""

# ─── Summary extraction ────────────────────────────────────────────
echo "=================================================================="
echo "  BENCHMARK SUMMARY"
echo "=================================================================="
echo ""
printf "%-25s  %6s  %6s  %6s  %6s  %6s  %8s\n" "Config" "F125" "F127" "F137" "F163" "Avg" "Time(s)"
printf "%-25s  %6s  %6s  %6s  %6s  %6s  %8s\n" "-------------------------" "------" "------" "------" "------" "------" "--------"

extract_accuracy() {
    # Extract Aggregate Accuracy for a given form number from a log file
    # Uses: "FORM 125 SUMMARY" followed by "Aggregate Accuracy: XX.XX%"
    local logfile="$1" form="$2"
    grep -A5 "FORM $form SUMMARY" "$logfile" 2>/dev/null | grep -oP 'Aggregate Accuracy:\s+\K[0-9.]+' | head -1
}

for f in "$RESULTS_DIR"/*.log; do
    [ -f "$f" ] || continue
    name=$(basename "$f" .log)

    # Extract per-form accuracy from "FORM XXX SUMMARY" blocks
    a125=$(extract_accuracy "$f" 125); a125=${a125:-"-"}
    a127=$(extract_accuracy "$f" 127); a127=${a127:-"-"}
    a137=$(extract_accuracy "$f" 137); a137=${a137:-"-"}
    a163=$(extract_accuracy "$f" 163); a163=${a163:-"-"}

    # Sum per-form times from ">>> ...: ... Time=XXX.XXs" lines
    total_time=$(grep -oP 'Time=\K[0-9.]+(?=s)' "$f" 2>/dev/null | awk '{s+=$1}END{if(s>0)printf "%.0f",s; else print "-"}')

    # Compute average accuracy
    avg="-"
    if [ "$a125" != "-" ] && [ "$a127" != "-" ] && [ "$a137" != "-" ] && [ "$a163" != "-" ]; then
        avg=$(echo "$a125 $a127 $a137 $a163" | awk '{printf "%.2f", ($1+$2+$3+$4)/4}')
    fi

    printf "%-25s  %6s  %6s  %6s  %6s  %6s  %8s\n" "$name" "$a125" "$a127" "$a137" "$a163" "$avg" "$total_time"
done

echo ""

# Also save summary to file
SUMMARY_FILE="$RESULTS_DIR/SUMMARY.txt"
{
    echo "Comprehensive Flag Benchmark - $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Total benchmark time: ${BENCH_ELAPSED}s"
    echo ""
    printf "%-25s  %6s  %6s  %6s  %6s  %6s  %8s\n" "Config" "F125" "F127" "F137" "F163" "Avg" "Time(s)"
    printf "%-25s  %6s  %6s  %6s  %6s  %6s  %8s\n" "-------------------------" "------" "------" "------" "------" "------" "--------"

    for f in "$RESULTS_DIR"/*.log; do
        [ -f "$f" ] || continue
        name=$(basename "$f" .log)
        a125=$(extract_accuracy "$f" 125); a125=${a125:-"-"}
        a127=$(extract_accuracy "$f" 127); a127=${a127:-"-"}
        a137=$(extract_accuracy "$f" 137); a137=${a137:-"-"}
        a163=$(extract_accuracy "$f" 163); a163=${a163:-"-"}
        total_time=$(grep -oP 'Time=\K[0-9.]+(?=s)' "$f" 2>/dev/null | awk '{s+=$1}END{if(s>0)printf "%.0f",s; else print "-"}')
        avg="-"
        if [ "$a125" != "-" ] && [ "$a127" != "-" ] && [ "$a137" != "-" ] && [ "$a163" != "-" ]; then
            avg=$(echo "$a125 $a127 $a137 $a163" | awk '{printf "%.2f", ($1+$2+$3+$4)/4}')
        fi
        printf "%-25s  %6s  %6s  %6s  %6s  %6s  %8s\n" "$name" "$a125" "$a127" "$a137" "$a163" "$avg" "$total_time"
    done
} > "$SUMMARY_FILE"

echo "Summary saved to: $SUMMARY_FILE"
echo ""
