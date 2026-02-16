# Friday Router

Austin's intelligent model routing skill for OpenClaw.

## Quick Start

```bash
# Install
cd friday-router
npm install -g clawhub
clawhub install ./friday-router

# Use
python scripts/router.py classify "your task description"
```

## Features

- Fixed scoring bugs from original intelligent-router
- Austin's preferred models (Flash, GLM-5, Kimi, Grok, DeepSeek Coder)
- OpenClaw integration for spawning sub-agents
- 7 tiers: FAST, REASONING, CREATIVE, RESEARCH, CODE, QUALITY, VISION

## Models

| Tier | Model | Cost/M |
|------|-------|--------|
| FAST | Gemini 1.5 Flash | $0.075/$0.30 |
| REASONING | GLM-5 | $0.10/$0.10 |
| CREATIVE | Kimi k2.5 | $0.20/$0.20 |
| RESEARCH | Grok Fast | $0.10/$0.10 |
| CODE | DeepSeek Coder V2 | $0.14/$0.28 |
| QUALITY | Claude 3.5 Sonnet | $3.00/$15.00 |
| VISION | GPT-4o | $2.50/$10.00 |

## Usage

```bash
# Classify task
python scripts/router.py classify "fix lint errors"

# Show scoring
python scripts/router.py score "build React auth system"

# Estimate cost
python scripts/router.py cost "design landing page"

# Get spawn params for OpenClaw
python scripts/router.py spawn "research LLMs"

# List models
python scripts/router.py models
```
