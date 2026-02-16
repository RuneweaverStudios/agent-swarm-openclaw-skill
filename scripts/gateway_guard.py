#!/usr/bin/env python3
"""
Gateway auth guard for IntentRouter (friday-router skill).

Purpose:
- Detect gateway auth drift (config vs running gateway process)
- Optionally auto-fix by restarting gateway with config auth credentials
- Output machine-readable JSON for orchestration flows
"""

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import time
from pathlib import Path


def _run(cmd, timeout=8):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _openclaw_home():
    return Path(os.environ.get("OPENCLAW_HOME") or os.path.expanduser("~/.openclaw"))


def _guard_state_path():
    return _openclaw_home() / "logs" / "gateway-guard.state.json"


def _secret_hash(secret):
    return hashlib.sha256((secret or "").encode("utf-8")).hexdigest()


def _load_guard_state():
    p = _guard_state_path()
    if not p.exists():
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_guard_state(pid, mode, port, secret):
    p = _guard_state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "pid": pid,
        "mode": mode,
        "port": port,
        "secretHash": _secret_hash(secret),
        "updatedAt": int(time.time()),
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(state, f)


def load_openclaw_config():
    cfg_path = _openclaw_home() / "openclaw.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return cfg_path, data


def auth_from_config(data):
    gateway = data.get("gateway") or {}
    auth = gateway.get("auth") or {}
    mode = auth.get("mode", "token")
    port = int(gateway.get("port", 18789))
    secret = auth.get("token") if mode == "token" else auth.get("password")
    return {
        "mode": mode,
        "port": port,
        "secret": secret,
    }


def _extract_pid_on_port(port):
    # macOS-friendly way to get listener PID(s)
    proc = _run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"])
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    first = proc.stdout.strip().splitlines()[0].strip()
    try:
        return int(first)
    except ValueError:
        return None


def _extract_gateway_secret_from_cmd(cmd, mode):
    if not cmd:
        return None
    if mode == "token":
        # --token abc OR --token=abc
        m = re.search(r"--token(?:=|\s+)(\S+)", cmd)
        return m.group(1) if m else None
    if mode == "password":
        # --password abc OR --password=abc
        m = re.search(r"--password(?:=|\s+)(\S+)", cmd)
        return m.group(1) if m else None
    return None


def gateway_runtime_status(port, mode, expected_secret):
    pid = _extract_pid_on_port(port)
    if not pid:
        return {
            "running": False,
            "pid": None,
            "cmd": None,
            "runtimeSecretDetected": None,
            "secretMatchesConfig": False,
            "reason": "gateway_not_running",
        }

    ps = _run(["ps", "-p", str(pid), "-o", "command="])
    cmd = ps.stdout.strip() if ps.returncode == 0 else ""
    runtime_secret = _extract_gateway_secret_from_cmd(cmd, mode)
    if runtime_secret:
        matches = bool(expected_secret and expected_secret == runtime_secret)
        reason = "ok" if matches else "secret_mismatch"
    else:
        # Some gateway binaries do not expose auth secrets in process args.
        state = _load_guard_state()
        if (
            state
            and state.get("pid") == pid
            and state.get("mode") == mode
            and int(state.get("port", -1)) == int(port)
            and state.get("secretHash") == _secret_hash(expected_secret)
        ):
            matches = True
            reason = "ok_guard_state"
        else:
            matches = False
            reason = "secret_not_detectable"
    return {
        "running": True,
        "pid": pid,
        "cmd": cmd,
        "runtimeSecretDetected": runtime_secret,
        "secretMatchesConfig": matches,
        "reason": reason,
    }


def _kill_pid(pid):
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        return
    time.sleep(0.7)
    try:
        os.kill(pid, 0)
    except OSError:
        return
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def _restart_gateway(port, mode, secret):
    _run(["openclaw", "gateway", "stop"], timeout=10)

    stale = _extract_pid_on_port(port)
    if stale:
        _kill_pid(stale)

    cmd = ["openclaw", "gateway", "--port", str(port), "--auth", mode]
    if mode == "token":
        cmd += ["--token", secret]
    elif mode == "password":
        cmd += ["--password", secret]
    else:
        raise ValueError(f"Unsupported auth mode: {mode}")

    log_path = _openclaw_home() / "logs" / "gateway-guard.restart.log"
    with open(log_path, "a", encoding="utf-8") as logf:
        logf.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] restart: {' '.join(cmd)}\n")
        subprocess.Popen(
            cmd,
            stdout=logf,
            stderr=logf,
            start_new_session=True,
        )

    time.sleep(2.0)
    status = gateway_runtime_status(port, mode, secret)
    if status.get("running") and status.get("pid"):
        _save_guard_state(status["pid"], mode, port, secret)
        # Recheck once state is recorded for binaries that hide secrets.
        status = gateway_runtime_status(port, mode, secret)
    return status


def build_result(cfg_path, mode, port, runtime, fixed=False):
    return {
        "ok": runtime.get("secretMatchesConfig", False),
        "fixed": fixed,
        "configPath": str(cfg_path),
        "authMode": mode,
        "gatewayPort": port,
        "running": runtime.get("running"),
        "pid": runtime.get("pid"),
        "reason": runtime.get("reason"),
        "secretMatchesConfig": runtime.get("secretMatchesConfig"),
        "recommendedAction": (
            "none"
            if runtime.get("secretMatchesConfig")
            else "run gateway_guard.py ensure --apply and restart client session"
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Gateway auth consistency guard")
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Check gateway auth consistency")
    p_status.add_argument("--json", action="store_true", help="JSON output")

    p_ensure = sub.add_parser("ensure", help="Ensure gateway auth consistency")
    p_ensure.add_argument("--apply", action="store_true", help="Auto-fix by restart")
    p_ensure.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()

    cfg_path, cfg = load_openclaw_config()
    auth = auth_from_config(cfg)
    mode, port, secret = auth["mode"], auth["port"], auth["secret"]

    if mode not in ("token", "password"):
        out = {
            "ok": False,
            "error": f"Unsupported gateway auth mode: {mode}",
            "configPath": str(cfg_path),
        }
        print(json.dumps(out) if getattr(args, "json", False) else out["error"])
        raise SystemExit(2)

    if not secret:
        out = {
            "ok": False,
            "error": f"Missing gateway auth secret in openclaw.json for mode={mode}",
            "configPath": str(cfg_path),
        }
        print(json.dumps(out) if getattr(args, "json", False) else out["error"])
        raise SystemExit(2)

    runtime = gateway_runtime_status(port, mode, secret)
    if args.command == "status":
        result = build_result(cfg_path, mode, port, runtime, fixed=False)
        if args.json:
            print(json.dumps(result))
        else:
            print(f"Auth mode: {mode}")
            print(f"Gateway port: {port}")
            print(f"Running: {result['running']} (pid={result['pid']})")
            print(f"Secret matches config: {result['secretMatchesConfig']}")
            print(f"Reason: {result['reason']}")
        raise SystemExit(0 if result["ok"] else 1)

    # ensure
    if runtime.get("secretMatchesConfig"):
        result = build_result(cfg_path, mode, port, runtime, fixed=False)
        if args.json:
            print(json.dumps(result))
        else:
            print("Gateway auth is already consistent.")
        raise SystemExit(0)

    if not args.apply:
        result = build_result(cfg_path, mode, port, runtime, fixed=False)
        if args.json:
            print(json.dumps(result))
        else:
            print("Gateway auth mismatch detected.")
            print("Re-run with --apply to restart gateway using openclaw.json auth.")
        raise SystemExit(2)

    after = _restart_gateway(port, mode, secret)
    result = build_result(cfg_path, mode, port, after, fixed=True)
    if args.json:
        print(json.dumps(result))
    else:
        print("Gateway restart attempted.")
        print(f"Secret matches config: {result['secretMatchesConfig']}")
        print(f"PID: {result['pid']}")
    raise SystemExit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()

