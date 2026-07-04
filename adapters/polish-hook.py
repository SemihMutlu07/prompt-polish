#!/usr/bin/env python3
"""
polish-hook — universal prompt-polish adapter for Claude Code, Codex, and Hermes.

Reads the harness's hook JSON from stdin, extracts the user's prompt text,
calls polish.py --hook to get a revised English version, prints the card to
the terminal (best-effort via /dev/tty), and emits the harness-specific
context payload on stdout so the LLM sees the revised phrasing.

Wire formats (verified empirically against each harness, 2026-07-05):
  - Claude Code / Codex UserPromptSubmit: stdin top-level "prompt" field;
    plain text printed to stdout is added as additionalContext (exit 0).
  - Hermes pre_llm_call: stdin "extra.user_message" field;
    stdout must be {"context": "..."} JSON (exit 0).

Fail-open everywhere: any error, missing key, timeout, or skip condition
produces empty stdout and exit 0 — the user's prompt is never blocked or
delayed beyond the timeout.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
POLISH_PY = os.path.join(HERE, "..", "polish.py")
SUBPROCESS_TIMEOUT = 20  # hard ceiling; polish.py's own POLISH_TIMEOUT is 15s by default


def extract_prompt(payload: dict) -> tuple[str, str]:
    """Return (prompt_text, harness_kind) where harness_kind is 'hermes' or 'generic'."""
    if payload.get("hook_event_name") == "pre_llm_call":
        return str(payload.get("extra", {}).get("user_message", "") or ""), "hermes"
    return str(payload.get("prompt", "") or ""), "generic"


def main() -> int:
    if os.environ.get("POLISH_HOOK_DISABLE"):
        return 0

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        return 0

    prompt, harness = extract_prompt(payload)
    prompt = prompt.strip()
    if not prompt or prompt.startswith("/"):
        return 0

    try:
        proc = subprocess.run(
            [sys.executable, POLISH_PY, "--hook", prompt],
            capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT,
        )
        result = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return 0

    revised = result.get("revised")
    if not revised:
        return 0

    card = result.get("card", "")
    if card:
        try:
            with open("/dev/tty", "w") as tty:
                print(card, file=tty)
        except OSError:
            pass  # no tty available (e.g. headless session) — skip visual card

    context = result.get("context", "")
    if harness == "hermes":
        print(json.dumps({"context": context}))
    else:
        print(context)
    return 0


if __name__ == "__main__":
    sys.exit(main())
