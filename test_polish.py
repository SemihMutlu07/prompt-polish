#!/usr/bin/env python3
"""Ağ gerektirmeyen path'lerin self-check'i: python3 test_polish.py"""
import io
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

# key yok → exit 1, stderr'de setup önerisi, stdout boş
r = run(["explain recursion please"])
assert r.returncode == 1 and "--setup" in r.stderr and r.stdout == "", r

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

print("ok — 6/6 checks passed")
