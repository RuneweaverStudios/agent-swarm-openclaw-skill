---
name: agent-swarm
displayName: Agent Swarm | OpenClaw Skill
description: "IMPORTANT: OpenRouter is required. Routes tasks to the right model and always delegates work through sessions_spawn."
version: 1.7.3
---

# Agent Swarm | OpenClaw Skill

## What this skill does

Agent Swarm is a traffic cop for AI models.
It picks the best model for each task, then starts a sub-agent to do the work.

### IMPORTANT: OpenRouter is required

- You must have an OpenRouter API key set in OpenClaw.
- Model IDs must use `openrouter/...`.
- If OpenRouter is not set, delegation will fail.

## Why this helps

- Faster replies (cheap orchestrator, smart sub-agent routing)
- Better quality (code tasks go to code models, writing tasks go to writing models)
- Lower cost (you do not run every task on the most expensive model)

## Core rule (non-negotiable)

For user tasks, the orchestrator must delegate.
It must NOT answer the task itself.

Use this flow every time:

1. Run router:
   ```bash
   python3 /Users/ghost/.openclaw/workspace/skills/agent-swarm/scripts/router.py spawn --json "<user message>"
   ```
2. If `needs_config_patch` is true: stop and report that patch to the user.
3. Otherwise call:
   `sessions_spawn(task=..., model=..., sessionTarget=...)`
4. Wait for `sessions_spawn` result.
5. Return the sub-agent result to the user.

If `sessions_spawn` fails, return only a delegation failure message.
Do not do the task yourself.

## Quick examples

### Single task

Router output:
`{"task":"write a poem","model":"openrouter/moonshotai/kimi-k2.5","sessionTarget":"isolated"}`

Then call:
`sessions_spawn(task="write a poem", model="openrouter/moonshotai/kimi-k2.5", sessionTarget="isolated")`

### Parallel tasks

```bash
python3 /Users/ghost/.openclaw/workspace/skills/agent-swarm/scripts/router.py spawn --json --multi "fix bug and write poem"
```

This returns multiple spawn configs. Start one sub-agent per config.

## Commands

```bash
python scripts/router.py default
python scripts/router.py classify "fix lint errors"
python scripts/router.py spawn --json "write a poem"
python scripts/router.py spawn --json --multi "fix bug and write poem"
python scripts/router.py models
```

## Config basics

Edit `config.json` to change routing:

- `default_model` = orchestrator default
- `routing_rules.<TIER>.primary` = main model for tier
- `routing_rules.<TIER>.fallback` = backups

## Security

### Input Validation

The router validates and sanitizes all inputs to prevent injection attacks:

- **Task strings**: Validated for length (max 10KB), null bytes, and suspicious patterns
- **Config patches**: Only allows modifications to `tools.exec.host` and `tools.exec.node` (whitelist approach)
- **Labels**: Validated for length and null bytes

### Safe Execution

**Critical**: When calling `router.py` from orchestrator code, always use `subprocess` with a list of arguments, **never** shell string interpolation:

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

The router uses Python's `argparse`, which safely handles arguments when passed as a list. Shell string interpolation is vulnerable to command injection if the user message contains shell metacharacters.

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

### Other Security Notes

- This skill does not expose gateway secrets.
- Use `gateway-guard` separately for gateway/auth management.
- The router does not execute arbitrary code or modify files outside of config patches.
