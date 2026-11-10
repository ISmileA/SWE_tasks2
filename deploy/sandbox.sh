#!/usr/bin/env bash
# Мы закрываем внешнюю сеть и папки хоста; доступ к моделям оставляем через Unix-сокет.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
BWRAP="$ROOT/vendor/bubblewrap/usr/bin/bwrap"
if [[ ! -x "$BWRAP" ]]; then echo 'Run scripts/setup_sandbox.sh first' >&2; exit 1; fi
mkdir -p runtime/sandbox
SOCKET_ROOT="/tmp/cineagents-$(id -u)"
mkdir -p "$SOCKET_ROOT/api"
if [[ ! -S "$SOCKET_ROOT/gateway/ollama.sock" ]]; then echo 'Start python -m cineagents.gateway first' >&2; exit 1; fi
# Мы ограничиваем виртуальную память, процессорное время и число открытых файлов.
ulimit -v 5242880
ulimit -t 600
ulimit -n 256
exec "$BWRAP" --unshare-all --die-with-parent --new-session --cap-drop ALL \
  --ro-bind /usr /usr --symlink usr/lib /lib --symlink usr/lib64 /lib64 \
  --symlink usr/bin /bin --symlink usr/sbin /sbin \
  --ro-bind /etc/ld.so.cache /etc/ld.so.cache \
  --proc /proc --dev /dev --tmpfs /tmp --dir /home --dir /app --dir /run \
  --ro-bind "$ROOT/cineagents" /app/cineagents \
  --ro-bind "$ROOT/agent_context" /app/agent_context \
  --ro-bind "$ROOT/agent_skills" /app/agent_skills \
  --ro-bind "$ROOT/prompts" /app/prompts \
  --ro-bind "$ROOT/data" /app/data --ro-bind "$ROOT/artifacts" /app/artifacts \
  --ro-bind "$ROOT/.venv-linux" /app/.venv-linux \
  --ro-bind "$ROOT/tests" /app/tests --ro-bind "$ROOT/pytest.ini" /app/pytest.ini \
  --ro-bind "$ROOT/scripts" /app/scripts \
  --bind "$ROOT/runtime/sandbox" /app/runtime \
  --ro-bind "$SOCKET_ROOT/gateway/ollama.sock" /run/ollama.sock \
  --bind "$SOCKET_ROOT/api" /run/api \
  --clearenv --setenv PATH /app/.venv-linux/bin:/usr/bin \
  --setenv HOME /home --setenv LANG C.UTF-8 --setenv PYTHONPATH /app \
  --setenv PYTHONDONTWRITEBYTECODE 1 --setenv OLLAMA_SOCKET /run/ollama.sock \
  --setenv OMP_NUM_THREADS 4 --setenv OPENBLAS_NUM_THREADS 4 \
  --setenv LANGSMITH_TRACING false --setenv TOKENIZERS_PARALLELISM false \
  --chdir /app /app/.venv-linux/bin/python "$@"
