#!/usr/bin/env bash
set -euo pipefail
cd /mnt/c/KFU/DM/Task2
mkdir -p runtime artifacts
export OLLAMA_HOST=127.0.0.1:11435
export NO_PROXY=127.0.0.1,localhost
if ! curl --noproxy 127.0.0.1 -sf http://127.0.0.1:11435/api/tags > runtime/ollama-initial.json; then
  OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_MODELS="$PWD/models/ollama" nohup ollama serve >runtime/ollama-server.log 2>&1 </dev/null &
  for i in $(seq 1 30); do
    if curl --noproxy 127.0.0.1 -sf http://127.0.0.1:11435/api/tags > runtime/ollama-initial.json; then break; fi
    sleep 1
  done
fi
ollama --version > artifacts/ollama-version.txt
for model in qwen3:0.6b qwen3:1.7b gemma3:1b gemma3:4b qwen3.5:0.8b; do
  echo "PULL $model"
  ollama pull "$model" > "runtime/pull-${model//:/-}.log" 2>&1
done
curl --noproxy 127.0.0.1 -sf http://127.0.0.1:11435/api/tags > artifacts/ollama-models.json
echo MODELS_READY
