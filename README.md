# CineAgents

Мы изучаем мультиагентные и рекомендательные системы на примере подбора фильмов.
Наша команда: Игнатьев Арсений и Николаева Полина, 3 курс, КФУ, ИТИС.

Распределение ответственности:
- Арсений: данные, классические методы RecSys, Two-Tower и оценка качества.
- Полина: мультиагентный граф, промпты, навыки, память и наблюдаемость.
- Совместно: архитектура, изоляция, интеграционные проверки, отчёт и защита.

Подробное описание зон ответственности: [docs/TEAM.md](docs/TEAM.md).

## Что мы используем в проекте

- Content-based и item-based collaborative filtering.
- Две эвристики: popularity и Bayesian rating; дополнительно RRF hybrid.
- Обученная нейросетевая Two-Tower с отдельными MLP и BPR loss.
- Общий LangGraph: decision gate, planner, retrieval tool, curator, независимый validator, один repair.
- Пять локальных LLM для сравнения: Qwen3 0.6B / 1.7B, Qwen3.5 0.8B, Gemma3 1B / 4B; финальный валидатор 4B. Никаких платных API.
- Jev-like локальный классификатор типизированных решений с вероятностями; это не официальный Jev.
- Три слоя памяти, свои системные промпты, навыки и контекстные Markdown-файлы.
- FastAPI, traces/spans/trajectories, метрики, JSONL-алерты.
- Bubblewrap внутри WSL2: нет внешней сети и Windows mounts, source/data read-only, inference через ограниченный UNIX gateway.
- Воспроизводимые RecSys/LLM/agent evals и восемь диаграмм.

## Системные требования

Для основного запуска мы используем Ubuntu 22.04 в WSL2, Python 3.10, Ollama 0.32.6,
CPU Ryzen 7 5800U, 16 ГБ RAM у Windows / 7.5 GiB у WSL. GPU не используется.
Основной запуск приложения и экспериментов выполняется в Linux.
Понадобятся примерно 7-9 ГБ диска для моделей и Python-зависимостей.

## Первый запуск

Из PowerShell в этой папке (WSL-дистрибутив Ubuntu-22.04 уже установлен):

```powershell
wsl -d Ubuntu-22.04 --cd /mnt/c/KFU/DM/Task2 -- bash scripts/setup_python_linux.sh
wsl -d Ubuntu-22.04 --cd /mnt/c/KFU/DM/Task2 -- bash scripts/setup_linux.sh
wsl -d Ubuntu-22.04 --cd /mnt/c/KFU/DM/Task2 -- bash scripts/setup_sandbox.sh
wsl -d Ubuntu-22.04 --cd /mnt/c/KFU/DM/Task2 -- .venv-linux/bin/python -m scripts.download_data
```

Установка не требует sudo: virtualenv и bubblewrap размещены в проекте. Ollama должен
быть установлен в Linux. Скрипт setup_linux использует отдельный порт 11435 и хранит
модели в models/ollama, не меняя существующий сервис :11434.
На Windows-диске установка PyTorch может занять несколько минут из-за DrvFS.
Все Unix-сокеты создаются на Linux /tmp, поскольку /mnt/c их не поддерживает.

Для работающей системы запустите в отдельном терминале и оставьте его открытым:

```powershell
wsl -d Ubuntu-22.04 --cd /mnt/c/KFU/DM/Task2 -- bash deploy/serve.sh
```

Открыть http://127.0.0.1:8000/docs — интерактивная документация API.
Health: http://127.0.0.1:8000/health ; метрики: http://127.0.0.1:8000/metrics .
Сервис слушает только localhost. user_id демонстрационный: это не production auth.

Пример через PowerShell:

```powershell
$request = @{user_id=10001; query='Посоветуй три комедии'; genre='Comedy'; k=3} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/agent -Method Post -ContentType 'application/json; charset=utf-8' -Body ([System.Text.Encoding]::UTF8.GetBytes($request))
Invoke-RestMethod 'http://127.0.0.1:8000/recommend/1?method=two_tower&k=5'
```

PUT /memory/{user_id} принимает {"genre":"Drama"}; GET показывает действующую память,
DELETE удаляет предпочтения и эпизоды. /traces/{trace_id} показывает trajectory.
При недоступной LLM /agent возвращает ошибку, не имитацию ответа.
Детерминированный /recommend доступен отдельно.

## Воспроизведение экспериментов

```powershell
wsl -d Ubuntu-22.04 --cd /mnt/c/KFU/DM/Task2 -- bash scripts/run_experiments.sh
wsl -d Ubuntu-22.04 --cd /mnt/c/KFU/DM/Task2 -- bash scripts/run_llm_eval.sh
wsl -d Ubuntu-22.04 --cd /mnt/c/KFU/DM/Task2 -- bash deploy/sandbox.sh -m scripts.eval_agents
wsl -d Ubuntu-22.04 --cd /mnt/c/KFU/DM/Task2 -- bash deploy/sandbox.sh -m scripts.sandbox_probe
```

Последние два запуска требуют работающий inference gateway из deploy/serve.sh.
Мы обучаем модель 20 эпох для каждой из двух заданных скоростей обучения и выбираем
лучшую версию по NDCG@10 на проверочной выборке. Тестовую выборку для выбора не используем. Финальная
нейросеть находится в artifacts/two_tower.pt. Зафиксированные Linux-версии — requirements-linux.lock.txt.
Повторная проверка CPU latency зависит от нагрузки; bitwise identity между версиями BLAS не обещается.

## Где смотреть результат

- `docs/RESEARCH.md` — обоснование и ограничения со ссылками.
- `docs/DEFENSE.md` — подготовка к защите и вопросы.
- `docs/REQUIREMENTS.md` — соответствие исходному ТЗ.
- `docs/diagrams/` — семь C4 видов + sequence, SVG и PNG.
- `artifacts/` — измерения, manifest split, checkpoints, raw outputs и логи испытаний.
- `data/manifest.json` — хеши оригинального MovieLens.
- `runtime/sandbox/observability/` — действующие логи и алерты sandbox; не коммитятся.

## Ограничения и честность результата

MovieLens исторический, а глобальный temporal split создаёт много cold users.
Оценки пользователей не равны impression/click logs. Бизнес-эффект без A/B не измерен.
Небольшие LLM делают ошибки и уязвимы к injection; JSON schema не решает grounding.
У sandbox общий Linux kernel с WSL; нет seccomp allowlist/cgroup memory.max.
Локальный JSONL monitoring уступает production observability platform.
Сырой текст запросов в рабочие логи не сохраняется; eval fixtures содержат только тестовые запросы.

Перед сдачей в отчёт необходимо добавить действующую ссылку на репозиторий.
