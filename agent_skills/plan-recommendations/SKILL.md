---
name: plan-recommendations
description: Select a typed retrieval plan from explicit user constraints and known memory.
---
1. Read requested_genre, then stored_genre, query and default_method.
2. Choose a single permitted retrieval method; no shell, SQL or networking is available.
3. Infer only constraints supported by the query. Missing constraints remain null.
4. Emit the plan schema. The application validates and executes the plan.
