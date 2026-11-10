#!/usr/bin/env bash
set -eu
ollama --version || true
curl -sf http://127.0.0.1:11434/api/tags || true
python3 - <<'PY'
import importlib.util, os, platform
print(platform.platform(),os.cpu_count())
print({m:bool(importlib.util.find_spec(m)) for m in ['torch','numpy','langgraph','fastapi','venv']})
PY
command -v bwrap || true
command -v systemd-run || true
cat /proc/cpuinfo | head -25
df -h /mnt/c
ls -ld /usr/local/bin/ollama
