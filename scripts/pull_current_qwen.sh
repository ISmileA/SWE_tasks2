#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export OLLAMA_HOST=127.0.0.1:11435
ollama pull qwen3.5:0.8b >runtime/pull-qwen35-08b.log 2>&1
curl --noproxy 127.0.0.1 -sf http://127.0.0.1:11435/api/tags >artifacts/ollama-models.json
