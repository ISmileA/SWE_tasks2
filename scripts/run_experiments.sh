#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/KFU/DM/Task2
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 LANGSMITH_TRACING=false
.venv-linux/bin/python -m pytest -q > artifacts/test-results.txt 2>&1
.venv-linux/bin/python -m scripts.train_eval --epochs 20 > artifacts/training.log 2>&1
