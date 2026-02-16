---
name: friday-router
description: Austin's intelligent model router with fixed scoring, his preferred models, and OpenClaw integration
version: 1.0.0
---

# Friday Router

Austin's intelligent model routing skill with fixed bugs from the original intelligent-router and customized for his preferred models.

**Default model:** OpenRouter Claude Sonnet 4 — capable of basic coding and complex tasks. The router **down-routes** to cheaper/faster models (e.g. Gemini 2.5 Flash) only when the task is clearly simple (FAST tier). So you start capable by default; simple tasks save cost.

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
| **Default (session)** | OpenRouter Claude Sonnet 4 | — |
| **Fast/F cheap** | Gemini 2.5 Flash (OpenRouter) | Gemini 1.5 Flash, Haiku |
| **Reasoning** | GLM-5 | Minimax 2.5 |
| **Creative/Frontend** | Kimi k2.5 | — |
| **Research** | Grok Fast | — |
| **Code/Engineering** | DeepSeek-Coder-V2 | Qwen2.5-Coder |
| **Quality/Complex** | OpenRouter Claude Sonnet 4 | Claude 3.5 Sonnet, GPT-4o |
| **Vision/Images** | GPT-4o | — |

When the skill is installed, OpenClaw's **default model** is set to OpenRouter Claude Sonnet 4 so every new session is capable by default. The router then recommends Gemini 2.5 Flash only for clearly simple tasks (check, status, list, etc.).

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

# Get OpenClaw spawn params
python scripts/router.py spawn "research the best LLMs"

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
