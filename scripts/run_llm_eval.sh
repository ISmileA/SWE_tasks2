#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/KFU/DM/Task2
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 LANGSMITH_TRACING=false
.venv-linux/bin/python -m scripts.eval_llm >artifacts/llm-eval.log 2>&1
