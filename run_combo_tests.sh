#!/bin/bash
set -e

PYTHON=".venv/bin/python"
BASE="test_pipeline.py --gpu --one-per-form --forms 125 127 137 --unload-wait 5"
RESULTS_DIR="test_output/combo_results"
mkdir -p "$RESULTS_DIR"

echo "=============================================="
echo " COMPREHENSIVE COMBO TEST MATRIX"
echo " Started: $(date)"
echo "=============================================="

# Test 1: VLM Extract only (fixed)
echo ""
echo ">>>>> TEST 1/6: VLM Extract Only <<<<<"
echo "CMD: $PYTHON $BASE --vlm-extract --vlm-extract-model qwen3-vl:8b"
START=$(date +%s)
$PYTHON $BASE --vlm-extract --vlm-extract-model qwen3-vl:8b 2>&1 | tee "$RESULTS_DIR/test1_vlm_only.log"
END=$(date +%s)
echo "TEST 1 DONE in $((END-START))s"
cp test_output/test_summary.json "$RESULTS_DIR/test1_vlm_only.json"
echo ""

# Test 2: Text LLM only (baseline) 
echo ""
echo ">>>>> TEST 2/6: Text LLM Only (Baseline) <<<<<"
echo "CMD: $PYTHON $BASE --text-llm"
START=$(date +%s)
$PYTHON $BASE --text-llm 2>&1 | tee "$RESULTS_DIR/test2_textllm_only.log"
END=$(date +%s)
echo "TEST 2 DONE in $((END-START))s"
cp test_output/test_summary.json "$RESULTS_DIR/test2_textllm_only.json"
echo ""

# Test 3: VLM Extract + Text LLM (combined, no ensemble)
echo ""
echo ">>>>> TEST 3/6: VLM Extract + Text LLM <<<<<"
echo "CMD: $PYTHON $BASE --vlm-extract --vlm-extract-model qwen3-vl:8b --text-llm"
START=$(date +%s)
$PYTHON $BASE --vlm-extract --vlm-extract-model qwen3-vl:8b --text-llm 2>&1 | tee "$RESULTS_DIR/test3_vlm_plus_textllm.log"
END=$(date +%s)
echo "TEST 3 DONE in $((END-START))s"
cp test_output/test_summary.json "$RESULTS_DIR/test3_vlm_plus_textllm.json"
echo ""

# Test 4: VLM Extract + Positional
echo ""
echo ">>>>> TEST 4/6: VLM Extract + Positional <<<<<"
echo "CMD: $PYTHON $BASE --vlm-extract --vlm-extract-model qwen3-vl:8b --use-positional"
START=$(date +%s)
$PYTHON $BASE --vlm-extract --vlm-extract-model qwen3-vl:8b --use-positional 2>&1 | tee "$RESULTS_DIR/test4_vlm_positional.log"
END=$(date +%s)
echo "TEST 4 DONE in $((END-START))s"
cp test_output/test_summary.json "$RESULTS_DIR/test4_vlm_positional.json"
echo ""

# Test 5: VLM + Text LLM + Positional + Ensemble (max accuracy)
echo ""
echo ">>>>> TEST 5/6: VLM + Text LLM + Positional + Ensemble <<<<<"
echo "CMD: $PYTHON $BASE --vlm-extract --vlm-extract-model qwen3-vl:8b --text-llm --use-positional --ensemble"
START=$(date +%s)
$PYTHON $BASE --vlm-extract --vlm-extract-model qwen3-vl:8b --text-llm --use-positional --ensemble 2>&1 | tee "$RESULTS_DIR/test5_vlm_textllm_pos_ens.log"
END=$(date +%s)
echo "TEST 5 DONE in $((END-START))s"
cp test_output/test_summary.json "$RESULTS_DIR/test5_vlm_textllm_pos_ens.json"
echo ""

# Test 6: Current best known combo (baseline with positional + vision checkboxes)
echo ""
echo ">>>>> TEST 6/6: Positional + Vision Checkboxes (Current Best) <<<<<"
echo "CMD: $PYTHON $BASE --text-llm --use-positional --vision-checkboxes-only --vision-model qwen2.5vl:7b"
START=$(date +%s)
$PYTHON $BASE --text-llm --use-positional --vision-checkboxes-only --vision-model qwen2.5vl:7b 2>&1 | tee "$RESULTS_DIR/test6_pos_visioncb.log"
END=$(date +%s)
echo "TEST 6 DONE in $((END-START))s"
cp test_output/test_summary.json "$RESULTS_DIR/test6_pos_visioncb.json"
echo ""

echo "=============================================="
echo " ALL TESTS COMPLETE: $(date)"
echo "=============================================="
echo ""
echo "Results in: $RESULTS_DIR/"
ls -la "$RESULTS_DIR"/*.json
