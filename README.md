# IntentRouter

**Your AI's Smart Traffic Director: Precisely Matching Your OpenClaw Tasks to the Perfect LLM.**

**v1.5.0 — This version is tested and working.** Gateway guard, watchdog, COMPLEX tier, absolute paths for TUI delegation.

IntentRouter is the intelligent LLM orchestration skill for OpenClaw. It precisely analyzes your tasks and directs them to the best LLM for the job—DeepSeek Coder for complex code, Kimi k2.5 for creative prose, Grok Fast for web research. Route with purpose; stop wasting resources.

## Instruction scope (what this skill does)

Runtime instructions tell the agent to: (1) run the included Python script (`router.py spawn --json "<message>"`), and (2) call OpenClaw's **sessions_spawn** with the script output. The instructions are **narrowly scoped** to **classification and delegating work to sub-agents**—nothing more.

**Delegation mandate:** When the skill is active, the main agent is instructed to **delegate** user "tasks" (code, write, research, build, fix, etc.) to sub-agents via `sessions_spawn`. The main agent does not perform those tasks itself. Be aware of this behavioral mandate.

**No install-time config change:** This skill does **not** set OpenClaw's default model on install. There is no install spec or code that modifies global OpenClaw config; any claim that the skill changes the default on install is **unsupported** (no such install step exists). The orchestrator/default model (e.g. Gemini 2.5 Flash) is defined in this skill's `config.json` and in your workspace agent instructions; your OpenClaw default is whatever you configure separately.

## Persistence & privilege

This skill is **not** force-included (always: false) and **does not request elevated privileges**. It does, however, prescribe a **runtime orchestration pattern** that causes the main agent to spawn sub-agents for most "task" requests. If you enable **autonomous agent invocation**, the platform will routinely follow this delegation policy—the main agent will delegate to other models by default. Consider whether you want that behavior before enabling autonomous invocation.

## Requirements

- **OpenRouter** — All model delegation uses OpenRouter (`openrouter/...` prefix). Configure OpenClaw with an OpenRouter API key so one auth profile covers every model.

## Default behavior

**Session default / orchestrator:** Gemini 2.5 Flash (`openrouter/google/gemini-2.5-flash`) — fast, cheap, reliable at tool-calling.

The router delegates tasks to tier-specific sub-agents (Kimi for creative, DeepSeek for code, etc.) via `sessions_spawn`. Simple tasks (check, status, list) down-route to Gemini 2.5 Flash.

---

## Orchestrator flow (task delegation)

The **main agent (Gemini 2.5 Flash)** does not do user tasks itself. For every user **task** (code, research, write, build, etc.):

1. Run IntentRouter: `python scripts/router.py spawn --json "<user message>"` and parse the JSON.
2. Call **sessions_spawn** with the `task` and `model` from the router output (use the exact `model` value).
3. Forward the sub-agent's result to the user.

**Example:**
```
router: {"task":"write a poem","model":"openrouter/moonshotai/kimi-k2.5","sessionTarget":"isolated"}
→ sessions_spawn(task="write a poem", model="openrouter/moonshotai/kimi-k2.5", sessionTarget="isolated")
→ Forward Kimi k2.5's poem to user. Say "Using: Kimi k2.5".
```

**Exception:** Meta-questions ("what model are you?") you answer yourself.

---

## Quick start

```bash
npm install -g clawhub
clawhub install friday-router

python scripts/gateway_guard.py status --json
python scripts/router.py default
python scripts/router.py classify "your task description"
```

---

## Features

- **Orchestrator** — Gemini 2.5 Flash delegates to tier-specific sub-agents via `sessions_spawn`
- Fixed scoring bugs from original intelligent-router
- 7 tiers: FAST, REASONING, CREATIVE, RESEARCH, CODE, QUALITY, VISION
- All models via OpenRouter (single API key)
- Config-driven: `config.json` for models and routing rules

---

## Models

| Tier | Model | Cost/M (in/out) |
|------|-------|-----------------|
| **Default / orchestrator** | Gemini 2.5 Flash | $0.30 / $2.50 |
| FAST | Gemini 2.5 Flash | $0.30 / $2.50 |
| REASONING | GLM-5 | $0.10 / $0.10 |
| CREATIVE | Kimi k2.5 | $0.20 / $0.20 |
| RESEARCH | Grok Fast | $0.10 / $0.10 |
| CODE | DeepSeek Coder V2 | $0.14 / $0.28 |
| QUALITY | GLM 4.7 Flash | $0.06 / $0.40 |
| VISION | GPT-4o | $2.50 / $10.00 |

**Fallbacks:** FAST → Gemini 1.5 Flash, Haiku; QUALITY → GLM 4.7, Sonnet 4, GPT-4o; CODE → Qwen 2.5 Coder; REASONING → Minimax 2.5.

---

## CLI usage

```bash
python scripts/gateway_guard.py status --json              # Check gateway auth consistency
python scripts/gateway_guard.py ensure --apply --json      # Auto-fix mismatch by restarting gateway
# For automatic gateway recovery (every 10s), install the gateway-watchdog skill and run its install_watchdog.sh
python scripts/router.py default                          # Show default model
python scripts/router.py classify "fix lint errors"        # Classify → tier + model
python scripts/router.py score "build a React auth system" # Detailed scoring
python scripts/router.py cost "design a landing page"      # Cost estimate
python scripts/router.py spawn "research best LLMs"        # Spawn params (human)
python scripts/router.py spawn --json "research best LLMs" # JSON includes gatewayAuthMode + token/password + port
python scripts/router.py models                            # List all models
```

---

## In-code usage

```python
from scripts.router import FridayRouter

router = FridayRouter()

default = router.get_default_model()
tier = router.classify_task("check server status")        # → "FAST"
result = router.recommend_model("build auth system")       # → {tier, model, fallback, reasoning}
spawn = router.spawn_agent("fix this bug", label="bugfix") # → {params: {task, model, sessionTarget}}
cost = router.estimate_cost("design landing page")         # → {tier, model, cost, currency}
```

---

## Tier detection

| Tier | Example keywords |
|------|------------------|
| **FAST** | check, get, list, show, status, monitor, fetch, simple |
| **REASONING** | prove, logic, analyze, derive, math, step by step |
| **CREATIVE** | creative, write, story, design, UI, UX, frontend, website |
| **RESEARCH** | research, find, search, lookup, web, information |
| **CODE** | code, function, debug, fix, implement, refactor, test, React, JWT |
| **QUALITY** | complex, architecture, design, system, comprehensive |
| **VISION** | image, picture, photo, screenshot, visual |

- **Vision** has priority: if vision keywords are present, task is VISION regardless of other keywords.
- **Agentic** tasks (multi-step) are bumped to at least CODE.

---

## Configuration

- **`config.json`** — Model list and `routing_rules` per tier; `default_model` (e.g. `openrouter/google/gemini-2.5-flash`) for session default and orchestrator.
- Router loads `config.json` from the parent of `scripts/` (skill root).

---

## License / author

Austin. Part of the OpenClaw skills ecosystem.
