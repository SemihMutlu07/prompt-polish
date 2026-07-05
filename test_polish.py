#!/usr/bin/env python3
"""Ağ gerektirmeyen path'lerin self-check'i: python3 test_polish.py"""
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# Config dosyasını ve env key'lerini gizle → key'siz davranış test edilebilir
ENV = {k: v for k, v in os.environ.items()
       if k not in ("POLISH_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY")}
ENV["HOME"] = "/nonexistent"


def run(args, inp=""):
    return subprocess.run(
        [sys.executable, os.path.join(HERE, "polish.py"), *args],
        input=inp, capture_output=True, text=True, env=ENV,
    )


# boş prompt → exit 1
r = run([], inp="")
assert r.returncode == 1, r

# çok kısa prompt → orijinal passthrough, exit 0
r = run(["hi"])
assert r.returncode == 0 and r.stdout.strip() == "hi", r

# çok uzun prompt → orijinal passthrough, exit 0
long = "x" * 5000
r = run([long])
assert r.returncode == 0 and r.stdout.strip() == long, r

# key yok + claude unavailable → exit 0, original stdout, uyarı (fallback çalıştı ama claude da auth'suz)
r = run(["explain recursion please"])
assert r.returncode == 0 and r.stdout.strip() == "explain recursion please", r
assert "Orijinal kullanılıyor" in r.stderr, r

# geçersiz base_url → zarif degrade: orijinal stdout'a, exit 0 (traceback yok)
env2 = {**ENV, "POLISH_API_KEY": "fake", "POLISH_BASE_URL": "not-a-url"}
r = subprocess.run(
    [sys.executable, os.path.join(HERE, "polish.py"), "explain recursion please"],
    capture_output=True, text=True, env=env2,
)
assert r.returncode == 0 and r.stdout.strip() == "explain recursion please", r
assert "Traceback" not in r.stderr, r

# kart render crash etmiyor
sys.path.insert(0, HERE)
import polish  # noqa: E402

sys.stderr = io.StringIO()
polish.print_card("orig prompt", {
    "revised": "a much better prompt " * 10,
    "improvements": [{"what": "word choice", "original": "a", "revised": "b", "note": "n" * 200}],
    "vocabulary": [{"word": "w", "meaning": "m", "alternative": "alt"}],
})
card = sys.stderr.getvalue()
sys.stderr = sys.__stderr__
assert "Prompt Polish" in card and "Vocabulary" in card

# --hook: kısa prompt → {"revised": null}, exit 0, geçerli JSON
r = run(["--hook", "hi"])
assert r.returncode == 0, r
assert json.loads(r.stdout) == {"revised": None}, r

# --hook: key yok → {"revised": null}, exit 0 (fail-open, hook modunda 1 değil)
env3 = {**ENV}
r = subprocess.run(
    [sys.executable, os.path.join(HERE, "polish.py"), "--hook", "explain recursion please"],
    capture_output=True, text=True, env=env3,
)
assert r.returncode == 0, r
assert json.loads(r.stdout) == {"revised": None}, r

# --hook: bozuk base_url → {"revised": null}, exit 0, traceback yok
env4 = {**ENV, "POLISH_API_KEY": "fake", "POLISH_BASE_URL": "not-a-url"}
r = subprocess.run(
    [sys.executable, os.path.join(HERE, "polish.py"), "--hook", "explain recursion please"],
    capture_output=True, text=True, env=env4,
)
assert r.returncode == 0, r
assert json.loads(r.stdout) == {"revised": None}, r
assert "Traceback" not in r.stderr, r

# --hook: stdin tty değilse ve boş prompt geldiyse asla interactive'e düşmez (bloklamaz)
r = run(["--hook"], inp="")
assert r.returncode == 0, r
assert json.loads(r.stdout) == {"revised": None}, r

ADAPTER = os.path.join(HERE, "adapters", "polish-hook.py")


def run_adapter(stdin_text, extra_env=None):
    env = {**ENV, **(extra_env or {})}
    return subprocess.run(
        [sys.executable, ADAPTER], input=stdin_text, capture_output=True, text=True, env=env,
    )

# adapter: slash command → skip, exit 0, boş stdout
r = run_adapter('{"prompt":"/model","hook_event_name":"UserPromptSubmit"}')
assert r.returncode == 0 and r.stdout == "", r

# adapter: POLISH_HOOK_DISABLE → skip, exit 0, boş stdout
r = run_adapter('{"prompt":"explain recursion","hook_event_name":"UserPromptSubmit"}',
                {"POLISH_HOOK_DISABLE": "1"})
assert r.returncode == 0 and r.stdout == "", r

# adapter: bozuk JSON stdin → fail-open, exit 0, boş stdout, traceback yok
r = run_adapter("not json")
assert r.returncode == 0 and r.stdout == "" and "Traceback" not in r.stderr, r

# adapter: key yok (Claude Code/Codex şeması) → fail-open, exit 0, boş stdout
r = run_adapter('{"prompt":"explain recursion please","hook_event_name":"UserPromptSubmit"}')
assert r.returncode == 0 and r.stdout == "", r

# adapter: key yok (Hermes şeması, extra.user_message) → fail-open, exit 0, boş stdout
r = run_adapter('{"hook_event_name":"pre_llm_call","extra":{"user_message":"explain recursion"}}')
assert r.returncode == 0 and r.stdout == "", r

print("ok — 15/15 checks passed")
