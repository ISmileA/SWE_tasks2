#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/KFU/DM/Task2
python3 -m pip install --target vendor/bootstrap virtualenv
PYTHONPATH="$PWD/vendor/bootstrap" python3 -m virtualenv .venv-linux
.venv-linux/bin/python -m pip install --upgrade pip
if [[ -f requirements-linux.lock.txt ]]; then
  .venv-linux/bin/python -m pip install -r requirements-linux.lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
else
  .venv-linux/bin/python -m pip install numpy scipy scikit-learn fastapi uvicorn langgraph psutil pytest httpx reportlab matplotlib pillow
  .venv-linux/bin/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
fi
.venv-linux/bin/python -m pip freeze > requirements-linux.lock.txt
echo PYTHON_READY
