---
name: friday-router
description: Austin's intelligent model router with fixed scoring, his preferred models, and OpenClaw integration
version: 1.3.0
---

# Friday Router

Austin's intelligent model routing skill with fixed bugs from the original intelligent-router and customized for his preferred models.

**Requirements:** **OpenRouter** — All router model delegation (default, orchestrator, and sub-agents) goes through OpenRouter. Model IDs use the `openrouter/...` prefix. Configure OpenClaw with an OpenRouter API key so one auth profile is used for every tier.

**Default model:** GLM 4.7 Flash (openrouter/z-ai/glm-4.7-flash via OpenRouter) — default and orchestrator; faster than full GLM 4.7. The router **down-routes** to cheaper/faster models (e.g. Gemini 2.5 Flash) for simple tasks (FAST tier).

## Orchestrator flow (mandatory for task requests)

When you are the **main agent** (GLM 4.7 Flash) and the user gives you a **task** (something to do: code, research, check, build, fix, **write**, **create**, design, poem, story, etc.), you must **delegate** it. You do **not** perform the task yourself; a sub-agent does.

**Steps (both required):**

1. **Run the Friday Router** to get spawn params:
   ```bash
   python3 workspace/skills/friday-router/scripts/router.py spawn --json "<user message>"
   ```
   The `--json` output is a single JSON object with `model`, `task`, `sessionTarget`, and optionally `label`.

2. **Call `sessions_spawn`** with the `task` and `model` (and any other params the tool accepts) from the router output. Use exactly the `model` value from the router—do not substitute a different model. The sub-agent will run with that model (e.g. Kimi k2.5 for CREATIVE) and do the work.

3. **Forward or summarize** the sub-agent's result to the user. You may briefly say you're delegating to the recommended model, then present the sub-agent's reply.

**Anti-pattern (forbidden):** Running the router, seeing e.g. "Kimi k2.5 recommended", and then doing the creative task yourself in the same turn. That bypasses the sub-agent: Kimi is never used and logs will show only the main model (e.g. GLM 4.7 Flash). Always call `sessions_spawn` after the router so the recommended model actually runs the task.

**Exception:** Meta-questions (e.g. "what model are you?", "how does routing work?") you answer yourself. Only delegate when the user is asking for work to be done.

## What Changed from Original

| Bug | Fix |
|-----|-----|
| Simple indicators inverted (high match = complex) | Now correctly: high simple keyword match = FAST tier |
| Agentic tasks not bumping tier | Multi-step tasks now properly bump to CODE tier |
| Vision tasks misclassified | Vision keywords now take priority over other classifications |
| Code keywords not detected | Added React, JWT, API, and other common code terms |
| Confidence always low | Now varies appropriately based on keyword match strength |

## Model Selection (Austin's Prefs)

| Use Case | Primary | Fallback |
|----------|---------|----------|
| **Default (session / orchestrator)** | GLM 4.7 Flash (z-ai/glm-4.7-flash) | GLM 4.7, Claude Sonnet 4 |
| **Fast/F cheap** | Gemini 2.5 Flash (OpenRouter) | Gemini 1.5 Flash, Haiku |
| **Reasoning** | GLM-5 | Minimax 2.5 |
| **Creative/Frontend** | Kimi k2.5 | — |
| **Research** | Grok Fast | — |
| **Code/Engineering** | DeepSeek-Coder-V2 | Qwen2.5-Coder |
| **Quality/Complex** | GLM 4.7 Flash | GLM 4.7, Claude Sonnet 4, GPT-4o |
| **Vision/Images** | GPT-4o | — |

When the skill is installed, OpenClaw's **default model** is GLM 4.7 Flash so every new session and the orchestrator use it. The router recommends Gemini 2.5 Flash for simple tasks (check, status, list, etc.).

## Usage

### CLI

```bash
# Show session default model (capable by default)
python scripts/router.py default

# Classify a task
python scripts/router.py classify "fix lint errors in utils.js"

# Show detailed scoring
python scripts/router.py score "build a React auth system"

# Estimate cost
python scripts/router.py cost "design a landing page"

# Get OpenClaw spawn params (human-readable)
python scripts/router.py spawn "research the best LLMs"

# Get spawn params as JSON (for sessions_spawn: parse and pass model, task, etc.)
python scripts/router.py spawn --json "research the best LLMs"

# List all models
python scripts/router.py models
```

### In Code

```python
from scripts.router import FridayRouter

router = FridayRouter()

# Classify task
tier = router.classify_task("check server status")
# → "FAST"

# Get model recommendation
result = router.recommend_model("build authentication system")
# → {tier: "CODE", model: {...}, fallback: {...}}

# Spawn with correct model
spawn_params = router.spawn_agent("fix this bug", label="bugfix")
# → {params: {model: "deepseek-ai/deepseek-coder-v2", ...}}
```

## Tier Detection

- **FAST**: check, get, list, show, status, monitor, fetch, simple
- **REASONING**: prove, logic, analyze, derive, math, step by step
- **CREATIVE**: creative, write, story, design, UI, UX, frontend, website
- **RESEARCH**: research, find, search, lookup, web, information
- **CODE**: code, function, debug, fix, implement, refactor, test, React, JWT
- **QUALITY**: complex, architecture, design, system, comprehensive
- **VISION**: image, picture, photo, screenshot, visual

## Examples

```bash
# Simple monitoring → FAST
python scripts/router.py classify "check server status"
# → FAST (Gemini 2.5 Flash)

# Code task → CODE
python scripts/router.py classify "fix lint errors in utils.js"
# → CODE (DeepSeek Coder)

# Multi-step build → CODE (bumped from default)
python scripts/router.py classify "build React auth with JWT, tests, CI"
# → CODE (DeepSeek Coder) - agentic task detected

# Mathematical proof → REASONING
python scripts/router.py classify "prove sqrt(2) is irrational"
# → REASONING (GLM-5)

# Design task → CREATIVE
python scripts/router.py classify "design a beautiful landing page"
# → CREATIVE (Kimi k2.5)

# Research → RESEARCH
python scripts/router.py classify "find information about GPT-5"
# → RESEARCH (Grok Fast)

# Vision → VISION (priority over other keywords)
python scripts/router.py classify "analyze this screenshot"
# → VISION (GPT-4o)
```
