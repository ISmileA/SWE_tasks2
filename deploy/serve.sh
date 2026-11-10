#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 LANGSMITH_TRACING=false
export OLLAMA_HOST=127.0.0.1:11435 NO_PROXY=127.0.0.1,localhost
mkdir -p runtime/sandbox
pids=()
cleanup() { for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done; }
trap cleanup EXIT INT TERM
if ! curl --noproxy 127.0.0.1 -sf --max-time 3 http://127.0.0.1:11435/api/tags >/dev/null; then
  OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_MODELS="$PWD/models/ollama" ollama serve >runtime/ollama-server.log 2>&1 &
  pids+=("$!")
fi
ready=0
for i in $(seq 1 30); do if curl --noproxy 127.0.0.1 -sf --max-time 3 http://127.0.0.1:11435/api/tags >/dev/null; then ready=1; break; fi; sleep 1; done
if [[ "$ready" != 1 ]]; then echo 'Ollama not ready; inspect runtime/ollama-server.log' >&2; exit 1; fi
SOCKET_ROOT="/tmp/cineagents-$(id -u)"
if ! curl --noproxy localhost --unix-socket "$SOCKET_ROOT/gateway/ollama.sock" -sf --max-time 3 http://localhost/api/tags >/dev/null; then
  .venv-linux/bin/python -m cineagents.gateway >runtime/gateway.log 2>&1 &
  pids+=("$!")
fi
for i in $(seq 1 30); do curl --noproxy localhost --unix-socket "$SOCKET_ROOT/gateway/ollama.sock" -sf --max-time 3 http://localhost/api/tags >/dev/null && break; sleep 1; done
bash deploy/sandbox.sh -m uvicorn cineagents.api:app --uds /run/api/api.sock --workers 1 >runtime/api.log 2>&1 &
pids+=("$!")
.venv-linux/bin/python -m cineagents.api_proxy >runtime/api-proxy.log 2>&1 &
pids+=("$!")
.venv-linux/bin/python -m scripts.monitor --interval 60 --agent-every 10 >runtime/monitor.log 2>&1 &
pids+=("$!")
echo 'CineAgents running: http://127.0.0.1:8000/docs (Ctrl+C stops processes started here)'
wait -n "${pids[@]}"
