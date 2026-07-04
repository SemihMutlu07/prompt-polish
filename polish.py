#!/usr/bin/env python3
"""
polish — Prompt Polish

AI kullanırken İngilizceni geliştiren terminal aracı. Prompt'unu alır,
daha akıcı İngilizce versiyonunu + yapılan düzeltmeleri + kelime
alternatiflerini küçük bir kartta gösterir. Kart stderr'e çizilir,
stdout'a sadece seçilen prompt yazılır — pipe edilebilir.

Kullanım:
  polish "write code for sort algorithm"
  echo "explain recursion" | polish
  polish                             # interactive mode (Ctrl+D)
  polish --file prompt.txt
  polish --setup                     # API key yapılandırma
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from typing import Optional

# ── Konfigürasyon ──────────────────────────────────────────────────

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"
CONFIG_DIR = os.path.expanduser("~/.config/prompt-polish")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
MIN_PROMPT_CHARS = 5
MAX_PROMPT_CHARS = 4000
NARROW_TERMINAL = 40  # altında kart yerine tek satır modu

PROMPT_SYSTEM = """You are an English improvement assistant. Your task is to help non-native speakers write better English prompts for AI.

Given a user's prompt, return a JSON object with these fields:
1. "revised": a rewritten version of the prompt in more fluent, natural English. Keep the same intent. Do NOT change the technical ask — just improve the English expression.
2. "improvements": an array of 2-4 specific improvements made, each as an object with:
   - "what": a concise label like "word choice", "grammar", "tone", "clarity", "structure"
   - "original": the original phrase
   - "revised": the improved version
   - "note": a short explanation in Turkish of why this change helps (1 sentence max)
3. "vocabulary": an array of 1-2 interesting words/phrases from the revised version that the user might learn from, each with:
   - "word": the word or phrase
   - "meaning": short Turkish explanation
   - "alternative": a similar alternative

Rules:
- Keep technical terms, code, and domain-specific jargon untouched
- Do NOT change the prompt's intent or add instructions the user didn't ask for
- The "improvements" should teach, not just rewrite
- Return ONLY valid JSON, no other text"""


# ── Config ─────────────────────────────────────────────────────────

def get_api_config() -> tuple[str, str, str]:
    """Return (api_key, base_url, model): config file first, env overrides."""
    api_key, base_url, model = "", DEFAULT_BASE_URL, DEFAULT_MODEL

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            api_key = cfg.get("api_key", api_key)
            base_url = cfg.get("base_url", base_url)
            model = cfg.get("model", model)
        except (json.JSONDecodeError, OSError):
            print(
                "⚠️  Config dosyası bozuk, `polish --setup` ile yeniden yapılandır.",
                file=sys.stderr,
            )

    api_key = (
        os.environ.get("POLISH_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or api_key
    )
    base_url = os.environ.get("POLISH_BASE_URL", base_url)
    model = os.environ.get("POLISH_MODEL", model)

    return api_key, base_url, model


def setup_config():
    """Interactive setup for API key."""
    print("🔧 Prompt Polish — Setup\n", file=sys.stderr)

    existing_key = get_api_config()[0]
    if existing_key:
        print(f"✓ Mevcut API key bulundu ({existing_key[:8]}...)", file=sys.stderr)
        cont = input("Yeniden yapılandırmak istiyor musun? [y/N] ").strip().lower()
        if cont != "y":
            print("Tamam, mevcut konfigürasyon korundu.", file=sys.stderr)
            return

    print("Bir API key gerekli. Şunlardan birini kullanabilirsin:", file=sys.stderr)
    print("  • OpenRouter (önerilen): https://openrouter.ai/keys", file=sys.stderr)
    print("  • OpenAI: https://platform.openai.com/api-keys\n", file=sys.stderr)

    key = input("API key: ").strip()
    if not key:
        print("⚠️  API key gerekli. Kurulum iptal edildi.", file=sys.stderr)
        sys.exit(1)

    base_url = input(
        f"Base URL (Enter = {DEFAULT_BASE_URL}): "
    ).strip() or DEFAULT_BASE_URL
    model = input(f"Model (Enter = {DEFAULT_MODEL}): ").strip() or DEFAULT_MODEL

    os.makedirs(CONFIG_DIR, exist_ok=True)
    cfg = {"api_key": key, "base_url": base_url, "model": model}
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(CONFIG_FILE, 0o600)

    print(f"\n✓ Konfigürasyon kaydedildi: {CONFIG_FILE}", file=sys.stderr)
    print("İstersen `export POLISH_API_KEY=...` ile env var da kullanabilirsin.", file=sys.stderr)


# ── LLM Call ───────────────────────────────────────────────────────

def call_llm(prompt: str, api_key: str, base_url: str, model: str) -> Optional[dict]:
    """Call the LLM, return parsed JSON — or None on any failure (caller degrades)."""
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": PROMPT_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 800,
    }).encode()

    for attempt in range(3):
        try:
            req = urllib.request.Request(
                f"{base_url}/chat/completions",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
            content = result["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                content = content.rsplit("```", 1)[0]
            return json.loads(content.strip())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(2)
                continue
            print(f"⚠️  API error: HTTP {e.code}", file=sys.stderr)
            return None
        # ValueError covers bozuk base_url ve bozuk JSON (JSONDecodeError)
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError) as e:
            print(f"⚠️  API error: {e}", file=sys.stderr)
            return None
    return None


# ── Terminal Rendering ─────────────────────────────────────────────

def term_width() -> int:
    try:
        return os.get_terminal_size().columns if sys.stderr.isatty() else 80
    except OSError:
        return 80


def print_card(original: str, data: dict):
    """Print a formatted improvement card to stderr."""
    improved = data.get("revised", "")
    improvements = data.get("improvements", [])
    vocabulary = data.get("vocabulary", [])

    H, V, TL, TRC, BL, BR = "─", "│", "╭", "╮", "╰", "╯"

    card_width = min(term_width() - 2, 78)
    content_width = card_width - 4

    def wrap(text: str, indent: int = 0) -> list[str]:
        max_w = content_width - indent
        if max_w < 10:
            return [text]
        words = text.split()
        lines = []
        current = ""
        for w in words:
            if len(current) + len(w) + 1 > max_w:
                lines.append(current)
                current = " " * indent + w
            else:
                current = (current + " " + w) if current else w
        if current:
            lines.append(current)
        if not lines:
            lines = [" " * indent + text]
        return lines

    def card_line(text: str = "") -> str:
        t = str(text) if text else ""
        if len(t) > content_width:
            t = t[: content_width - 3] + "..."
        return f"{V} {t:<{content_width}} {V}"

    # Top
    print(f"{TL}{H * (card_width - 2)}{TRC}", file=sys.stderr)
    print(card_line("✨ Prompt Polish"), file=sys.stderr)
    print(card_line(), file=sys.stderr)

    # Original
    print(card_line("┄" * content_width), file=sys.stderr)
    print(card_line("Original prompt"), file=sys.stderr)
    for l in wrap(original, 2):
        print(card_line(l), file=sys.stderr)

    if improved:
        print(card_line(), file=sys.stderr)
        print(card_line("✓ Revised"), file=sys.stderr)
        for l in wrap(improved, 2):
            print(card_line(l), file=sys.stderr)

    # Improvements
    if improvements:
        print(card_line(), file=sys.stderr)
        print(card_line("┄" * content_width), file=sys.stderr)
        print(card_line("\U0001f4dd Improvements"), file=sys.stderr)
        for imp in improvements:
            label = imp.get("what", "")
            orig = imp.get("original", "")
            rev = imp.get("revised", "")
            note = imp.get("note", "")
            print(card_line(f"  • {label}"), file=sys.stderr)
            if orig:
                print(card_line(f"    ✗ {orig}"), file=sys.stderr)
            if rev:
                print(card_line(f"    ✓ {rev}"), file=sys.stderr)
            if note:
                for l in wrap(note, 6):
                    print(card_line(l), file=sys.stderr)

    # Vocabulary
    if vocabulary:
        print(card_line(), file=sys.stderr)
        print(card_line("┄" * content_width), file=sys.stderr)
        print(card_line("\U0001f4d6 Vocabulary"), file=sys.stderr)
        for voc in vocabulary:
            word = voc.get("word", "")
            meaning = voc.get("meaning", "")
            alt = voc.get("alternative", "")
            print(card_line(f"  • {word}"), file=sys.stderr)
            if meaning:
                print(card_line(f"    → {meaning}"), file=sys.stderr)
            if alt:
                print(card_line(f"    ↩ alt: {alt}"), file=sys.stderr)

    # Bottom
    print(card_line(), file=sys.stderr)
    print(f"{BL}{H * (card_width - 2)}{BR}", file=sys.stderr)


# ── Main ───────────────────────────────────────────────────────────

def get_prompt(args) -> str:
    """Get prompt from args, file, stdin, or interactive input."""
    if args.file:
        try:
            with open(args.file) as f:
                return f.read().strip()
        except OSError as e:
            print(f"⚠️  Dosya okunamadı: {e}", file=sys.stderr)
            sys.exit(1)

    if args.prompt:
        return " ".join(args.prompt).strip()

    if not sys.stdin.isatty():
        return sys.stdin.read().strip()

    # Interactive mode
    print("✍️  Enter your prompt (Ctrl+D to finish):", file=sys.stderr)
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass
    return "\n".join(lines).strip()


def run() -> int:
    parser = argparse.ArgumentParser(
        prog="polish",
        description="İngilizceni geliştiren prompt aracı — kart stderr'de, prompt stdout'ta.",
    )
    parser.add_argument("prompt", nargs="*", help="iyileştirilecek prompt")
    parser.add_argument("--setup", action="store_true", help="API key yapılandırması")
    parser.add_argument("-f", "--file", help="prompt'u dosyadan oku")
    args = parser.parse_args()

    if args.setup:
        setup_config()
        return 0

    prompt = get_prompt(args)
    if not prompt:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 1

    # Degrade path'lerinde her zaman: orijinal stdout'a, uyarı stderr'e, exit 0
    if len(prompt) < MIN_PROMPT_CHARS:
        print("⚠️  Prompt çok kısa, iyileştirme atlandı.", file=sys.stderr)
        print(prompt)
        return 0
    if len(prompt) > MAX_PROMPT_CHARS:
        print(f"⚠️  Prompt çok uzun (>{MAX_PROMPT_CHARS} karakter), iyileştirme atlandı.", file=sys.stderr)
        print(prompt)
        return 0

    api_key, base_url, model = get_api_config()
    if not api_key:
        print("⚠️  API key bulunamadı. `polish --setup` ile yapılandır.", file=sys.stderr)
        print("   Key almak için: https://openrouter.ai/keys", file=sys.stderr)
        return 1

    data = call_llm(prompt, api_key, base_url, model)
    if not data:
        print("⚠️  Prompt iyileştirilemedi. Orijinal kullanılıyor.", file=sys.stderr)
        print(prompt)
        return 0

    revised = data.get("revised", prompt) or prompt

    if term_width() < NARROW_TERMINAL:
        print(f"✓ Improved: {revised[:50]}", file=sys.stderr)
    else:
        print_card(prompt, data)

    # "Use revised?" sadece tam interaktif oturumda sorulur;
    # pipe/redirect modunda direkt revised basılır
    interactive = sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()
    if interactive:
        print(file=sys.stderr)
        sys.stderr.write("│ Use revised? [Y/n] ")
        sys.stderr.flush()
        try:
            choice = input()
        except EOFError:
            choice = "y"
        if choice.strip().lower() not in ("", "y", "yes"):
            print(prompt)
            return 0

    print(revised)
    return 0


def main():
    try:
        sys.exit(run())
    except KeyboardInterrupt:
        print(file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
