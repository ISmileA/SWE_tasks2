#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 LANGSMITH_TRACING=false
.venv-linux/bin/python -m scripts.eval_llm --models qwen3.5:0.8b --append >artifacts/llm-eval-qwen35.log 2>&1
