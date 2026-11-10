# Соответствие заданию

Источники: Agent ТЗ Осень 26-27.docx, LLM_for Agent.docx, RecSys_Upper.docx, предоставленные Арсением. Реализованы и базовая, и красная усложнённая части RecSys. Дедлайн из сообщения пользователя: 10 ноября.

## Мультиагентная система

| Требование | Реализация / доказательство | Статус |
|---|---|---|
| Собственное ТЗ | docs/SPEC.md | Выполнено |
| Сравнить движки | docs/RESEARCH.md: Ollama, llama.cpp, vLLM, API | Обоснование; реально запускался Ollama |
| Попробовать >=3 LLM | artifacts/llm_eval_raw.json, llm_eval_summary.json, ollama-models.json | Пять моделей, 40 реальных probes |
| Роутинг моделей | DecisionModel + ModelRouter, small/strong/validator | Реализовано |
| Jev-like Model | Локальный discriminative typed router, probabilities и calibrated CV | Реализован учебный аналог, не Jev |
| Фреймворк | Исполняемый LangGraph StateGraph | Реализовано |
| Общий multi-agent flow | gate → planner → retrieval → curator → validator → final; bounded repair | Реализовано |
| Валидатор другой семьи | Qwen generation, Gemma validation; constructor запрещает ту же семью | Реализовано и протестировано |
| 7 C4 + sequence | docs/diagrams/01…08, SVG/PNG, исходники build_diagrams.py | Созданы |
| Системные промпты | prompts/*.md, загружаются load_instructions | Реализовано |
| Свои навыки | agent_skills/*/SKILL.md, загружаются соответствующей ролью | Реализовано |
| Содержательные Markdown | SOUL.md, POLICIES.md, MEMORY.md | Реализовано; MEMORY описывает lifecycle |
| Tools | Типизированный plan вызывает allowlisted Recommender.recommend | Реально исполняется |
| 2-3 слоя памяти | Request state, эпизоды 7 дней, явные preferences 90 дней | Реализовано; SQLite/TTL/user tests |
| Сравнить memory approaches | Graphiti, Mem0, LangMem, Letta, RAG, SQL | docs/RESEARCH.md |
| Evals: LLM + system + product + infra | Ranking experiment, LLM probes, graph scenarios, latency/tokens/RSS; business definitions | Измерено там, где есть данные; продуктовые эффекты не выдумываются |
| Observability | spans/logs/trace/trajectory, /metrics, JSONL alerts, monitor.py | Реализовано и испытано |
| Изоляция, сравнение вариантов | Bubblewrap + WSL2, no network, read-only sources, bounded UDS | 8 практических probes; ограничения перечислены |
| Подготовка к устной защите | docs/DEFENSE.md + воспроизводимые команды | Вопросы по работе системы и порядок демонстрации |

## Рекомендательная система

| Требование | Реализация / доказательство | Статус |
|---|---|---|
| Любой сервис и датасет | Фильмы, оригинальный MovieLens 100K, manifest hashes | Реальные данные |
| >=2 классических подхода | Genre content-based, item-item collaborative filtering | Реализованы и оценены |
| 1-2 эвристики | Positive popularity, Bayesian rating | Реализованы и оценены |
| Дополнительный hybrid | Reciprocal-rank fusion content + CF | Реализован и оценён |
| Красная часть: research + развернуть современный подход | Обученный Two-Tower, сравнение с GNN и LLM-reranking | Реальная нейросеть и checkpoint |
| Ограничения моделей и способы решения с недостатками | Cold start, popularity bias, weak content features, negative feedback ambiguity | docs/RESEARCH.md / PDF |
| Production-проблемы и компромиссы | Latency, drift, availability, failure, auth, data poisoning, scale | docs/RESEARCH.md / PDF |
| ML-метрики | P/R/NDCG/HitRate/MRR@10, coverage, diversity, novelty, cohorts, bootstrap | artifacts/recsys_results.json, per_user.csv, bootstrap.json |
| Бизнес-метрики и мониторинг | CTR/play rate/retention/watch-through, A/B design, infra/LLM monitoring | Определены; нет заявлений о несуществующем A/B |
| PDF с зафиксированным результатом | output/pdf/CineAgents_отчет.pdf | Описание системы, результаты, ограничения и диаграммы |
| Обязательная ссылка на репозиторий | Исходники сохранены в локальном Git | Ссылку необходимо добавить перед сдачей |

## Что нельзя утверждать при сдаче

Нельзя утверждать, что все LLM защищены от injection; что WSL сама является sandbox; что новый пользователь получил neural personalization; что offline NDCG доказывает рост выручки; что сравнение альтернатив означает их экспериментальный запуск. Нельзя подменять PDF ссылкой и нельзя подставлять несуществующий URL репозитория.
