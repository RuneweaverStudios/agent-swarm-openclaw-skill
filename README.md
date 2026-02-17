# Agent Swarm | OpenClaw Skill

> IMPORTANT: OPENROUTER IS REQUIRED
>
> Agent Swarm only supports `openrouter/...` models and requires a configured OpenRouter API key in OpenClaw.
> Without OpenRouter, subagent delegation and `sessions_spawn` routing will fail.

**LLM routing and subagent delegation.** Routes each task to the right model, spawns subagents, and saves tokens. **Parallel tasks:** one message can spawn multiple subagents at once (e.g. "fix the bug and write a poem" → code + creative in parallel).

**v1.7.0 — This version is tested and working.** COMPLEX tier, absolute paths for TUI delegation. **Security-focused release:** Removed gateway auth secret exposure and gateway management functionality for improved security rating. **Source:** [github.com/RuneweaverStudios/agent-swarm](https://github.com/RuneweaverStudios/agent-swarm).

Agent Swarm | OpenClaw Skill routes your OpenClaw tasks to the best LLM for the job and delegates work to subagents. You save tokens (orchestrator stays on a cheap model; only the task runs on the matched model) and get better results—GLM 4.7 for code, Kimi k2.5 for creative, Grok Fast for research.

**Security improvements in v1.7.0+:** 
- Removed gateway auth token/password exposure from router output
- Gateway management functionality has been removed - use the separate [gateway-guard](https://clawhub.ai/skills/gateway-guard) skill if gateway auth management is needed
- FACEPALM troubleshooting integration has been removed - use the separate [FACEPALM](https://github.com/RuneweaverStudios/FACEPALM) skill if troubleshooting is needed
- **v1.7.2+**: Added comprehensive input validation, config patch validation, and security documentation

## Why Agent Swarm

With a single model, OpenClaw can feel slow: you're forced to choose between quality and cost, and every prompt pays the same price. Agent Swarm removes that tradeoff. The orchestrator stays on a fast, cheap model; only the task at hand runs on the best model for the job. No wasted prompts—efficient routing, not one-size-fits-all. With OpenRouter, replies come back faster and the conversation feels more lively and natural.

## Requirements (critical)

- **OpenRouter is mandatory** — All model delegation uses OpenRouter (`openrouter/...` prefix). Configure OpenClaw with an OpenRouter API key so one auth profile covers every model.

## Security

### Input Validation

The router validates and sanitizes all inputs to prevent injection attacks:

- **Task strings**: Validated for length (max 10KB), null bytes, and suspicious patterns
- **Config patches**: Only allows modifications to `tools.exec.host` and `tools.exec.node` (whitelist approach)
- **Labels**: Validated for length and null bytes

### Safe Execution (Critical for Orchestrators)

**When calling `router.py` from orchestrator code, always use `subprocess` with a list of arguments, never shell string interpolation:**

```python
# ✅ SAFE: Use subprocess with list arguments
import subprocess
result = subprocess.run(
    ["python3", "/path/to/router.py", "spawn", "--json", user_message],
    capture_output=True,
    text=True
)

# ❌ UNSAFE: Shell string interpolation (vulnerable to injection)
import os
os.system(f'python3 router.py spawn --json "{user_message}"')  # DON'T DO THIS
```

The router uses Python's `argparse`, which safely handles arguments when passed as a list. Shell string interpolation is vulnerable to command injection if the user message contains shell metacharacters (`;`, `|`, `&`, `$()`, etc.).

### Config Patch Safety

The `recommended_config_patch` only modifies safe fields:
- `tools.exec.host` (must be 'sandbox' or 'node')
- `tools.exec.node` (only when host is 'node')

All config patches are validated before being returned. The orchestrator should validate patches again before applying them to `openclaw.json`.

### Prompt Injection Mitigation

Task strings are passed to `sessions_spawn` and then to sub-agents. While the router validates input format, prompt injection protection is primarily the responsibility of:
1. The orchestrator (validating task strings)
2. The sub-agent LLM (resisting prompt injection)
3. The OpenClaw platform (sanitizing `sessions_spawn` inputs)

## Default behavior

**Session default / orchestrator:** Gemini 2.5 Flash (`openrouter/google/gemini-2.5-flash`) — fast, cheap, reliable at tool-calling.

The router delegates tasks to tier-specific sub-agents (Kimi for creative, GLM 4.7 for code, etc.) via `sessions_spawn`. Simple tasks (check, status, list) down-route to Gemini 2.5 Flash.

---

## Orchestrator flow (task delegation)

The **main agent (Gemini 2.5 Flash)** does not do user tasks itself. For every user **task** (code, research, write, build, etc.):

1. Run Agent Swarm router: `python scripts/router.py spawn --json "<user message>"` and parse the JSON.
2. Call **sessions_spawn** with the `task` and `model` from the router output (use the exact `model` value).
3. Forward the sub-agent's result to the user.

**Example:**
```
router: {"task":"write a poem","model":"openrouter/moonshotai/kimi-k2.5","sessionTarget":"isolated"}
→ sessions_spawn(task="write a poem", model="openrouter/moonshotai/kimi-k2.5", sessionTarget="isolated")
→ Forward Kimi k2.5's poem to user. Say "Using: Kimi k2.5".
```

**Exception:** Meta-questions ("what model are you?") you answer yourself.

### Parallel tasks

For one message with multiple tasks, use **`spawn --json --multi "<message>"`**. The router splits on *and*, *then*, *;*, and *also*, classifies each part, and returns `{"parallel": true, "spawns": [{task, model, sessionTarget}, ...], "count": N}`. The orchestrator can then call `sessions_spawn` for each entry and run them in parallel; use subagent-tracker to see progress.

**Example:** `spawn --json --multi "fix the login bug and write a short poem"` → two spawns (e.g. GLM 4.7 for code, Kimi for poem).

---

## Quick start

```bash
npm install -g clawhub
clawhub install agent-swarm

python scripts/router.py default
python scripts/router.py classify "your task description"
```

---

## Features

- **Orchestrator** — Gemini 2.5 Flash delegates to tier-specific sub-agents via `sessions_spawn`
- **Parallel tasks** — `spawn --json --multi "task A and task B"` splits on *and* / *then* / *;* and returns an array of spawn params; orchestrator can spawn all and run them in parallel
- 7 tiers: FAST, REASONING, CREATIVE, RESEARCH, CODE, QUALITY, VISION
- All models via OpenRouter (single API key)
- Config-driven: `config.json` for models and routing rules
- **Security-focused** — No gateway auth secret exposure, no process management, input validation, config patch whitelisting

---

## Default agents (edit in config.json)

All defaults are in **`config.json`**. Edit these two places to change which model runs for each tier:

| What to edit | Key in config.json | Purpose |
|--------------|--------------------|---------|
| Session default / orchestrator | `default_model` | Model for new sessions and the main agent |
| Per-tier primary | `routing_rules.<TIER>.primary` | Model used when a task matches that tier (FAST, CODE, CREATIVE, etc.) |

Example: to make CODE use a different model, edit `routing_rules.CODE.primary`. Fallbacks are in `routing_rules.<TIER>.fallback`. The router loads this file from the skill root (parent of `scripts/`).

---

## Models

| Tier | Model | Cost/M (in/out) |
|------|-------|-----------------|
| **Default / orchestrator** | Gemini 2.5 Flash | $0.30 / $2.50 |
| FAST | Gemini 2.5 Flash | $0.30 / $2.50 |
| REASONING | GLM-5 | $0.10 / $0.10 |
| CREATIVE | Kimi k2.5 | $0.20 / $0.20 |
| RESEARCH | Grok Fast | $0.10 / $0.10 |
| CODE | GLM 4.7 Flash | $0.06 / $0.40 |
| QUALITY | GLM 4.7 Flash | $0.06 / $0.40 |
| VISION | GPT-4o | $2.50 / $10.00 |

**Fallbacks:** FAST → Gemini 1.5 Flash, Haiku; QUALITY → GLM 4.7, Sonnet 4, GPT-4o; CODE → MiniMax 2.5, Qwen Coder; REASONING → Minimax 2.5.

---

## CLI usage

```bash
python scripts/router.py default                          # Show default model
python scripts/router.py classify "fix lint errors"        # Classify → tier + model
python scripts/router.py score "build a React auth system" # Detailed scoring
python scripts/router.py cost "design a landing page"      # Cost estimate
python scripts/router.py spawn "research best LLMs"        # Spawn params (human)
python scripts/router.py spawn --json "research best LLMs" # JSON for sessions_spawn (no gateway secrets)
python scripts/router.py spawn --json --multi "fix bug and write poem" # Parallel tasks → array of spawns
python scripts/router.py models                            # List all models
```

**Note:** Gateway auth management is not included in this skill. Use the separate `gateway-guard` skill if you need gateway auth checking or management.

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
| **CREATIVE** | creative, write, story, design, UI, UX, frontend, website (website projects → Kimi k2.5 only) |
| **RESEARCH** | research, find, search, lookup, web, information |
| **CODE** | code, function, debug, fix, implement, refactor, test, React, JWT (not website builds) |
| **QUALITY** | complex, architecture, design, system, comprehensive |
| **VISION** | image, picture, photo, screenshot, visual |

- **Vision** has priority: if vision keywords are present, task is VISION regardless of other keywords.
- **Agentic** tasks (multi-step) are bumped to at least CODE.

---

---

## Changelog

### v1.7.3 (Security hardening)

**Security improvements:**
- **Input validation**: Added comprehensive validation for task strings (length limits, null byte detection, suspicious pattern detection)
- **Config patch validation**: Whitelist-based validation for `recommended_config_patch` - only allows modifications to `tools.exec.host` and `tools.exec.node`
- **Label validation**: Added validation for label parameters
- **Documentation**: Added security section with safe execution practices and injection prevention guidance

**Technical changes:**
- Added `validate_task_string()` function for input sanitization
- Added `validate_config_patch()` function for config patch whitelisting
- Updated `spawn_agent()`, `classify_task()`, and `split_into_tasks()` to validate inputs
- Enhanced error messages for invalid inputs

### v1.7.0 (Security-focused release)

**Removed functionality (for improved security rating):**
- **Gateway guard integration** — Removed `gateway_watchdog.py` and gateway auth management functionality. Use the separate [gateway-guard](https://clawhub.ai/skills/gateway-guard) skill for gateway auth checking and management.
- **Gateway auth secret exposure** — Removed `get_openclaw_gateway_config()` function that exposed gateway tokens/passwords in router output. Router spawn output no longer includes `gatewayToken`, `gatewayPassword`, `gatewayAuthMode`, or `gatewayPort`.
- **FACEPALM troubleshooting integration** — Removed troubleshooting loop detection and automatic FACEPALM invocation. Use the separate [FACEPALM](https://github.com/RuneweaverStudios/FACEPALM) skill if intelligent troubleshooting is needed.

**Security improvements:**
- Router now only handles model routing with no credential exposure
- No process management capabilities (no gateway restart/kill operations)
- Clean separation of concerns: routing vs. gateway management vs. troubleshooting

**Migration:**
- If you need gateway auth management: `clawhub install gateway-guard`
- If you need troubleshooting: Install [FACEPALM](https://github.com/RuneweaverStudios/FACEPALM) separately

---

## Configuration

- **`config.json`** — Model list and `routing_rules` per tier; `default_model` (e.g. `openrouter/google/gemini-2.5-flash`) for session default and orchestrator.
- Router loads `config.json` from the parent of `scripts/` (skill root).

---

## Related skills

- **[gateway-guard](https://clawhub.ai/skills/gateway-guard)** — Gateway auth management (use separately if needed)
- **[FACEPALM](https://github.com/RuneweaverStudios/FACEPALM)** — Intelligent troubleshooting (use separately if needed)
- **[what-just-happened](https://clawhub.ai/skills/what-just-happened)** — Summarizes gateway restarts

---

## License / author

Austin. Part of the OpenClaw skills ecosystem.
