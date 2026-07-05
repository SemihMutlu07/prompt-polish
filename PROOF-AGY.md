# 🧪 Prompt Polish — Proof: AGY (Google Gemini CLI) Integration

**Date:** 2026-07-05
**Tool version:** v0.1.0
**Integration:** GEMINI.md system instruction embedding

## How It Works

AGY (Antigravity/Gemini CLI) does NOT have a hook system like Claude Code/Codex. Instead, prompt-polish instructions are embedded directly into `~/.gemini/GEMINI.md` — the file AGY reads at session start as its system-level instruction set.

The instructions tell AGY to:
1. Detect rough/non-fluent English prompts
2. Rewrite them silently in fluent English
3. Respond to the *polished* version, not the literal version
4. Show a `✨ Prompt Polish` card with:
   - Original prompt
   - Revised version
   - `📝 Improvements` (Turkish explanations)
   - `📖 Vocabulary` (word + Turkish meaning)
5. Skip the card if the prompt is already fluent

AGY does the polishing itself using the Gemini model — no extra API call, no subprocess, purely LLM-instructed. More token-efficient than the hook approach.

## Verification

### GEMINI.md contains Prompt Polish section:

```bash
cat ~/.gemini/GEMINI.md | grep -A5 "Prompt Polish"
# → "## Prompt Polish (English Language Assistant)"
```

### AGY configuration at `~/.gemini/config/config.json`:

```json
{
  "userSettings": {
    "globalPermissionGrants": { ... },
    "remoteControlHostname": "fedora-spectral-halo",
    "themeMode": "THEME_MODE_INHERIT"
  }
}
```

No separate config needed — GEMINI.md instructions are the integration point.

### Live test (with AGY session):

```
$ agy --print "write code for sort algorithm fastly"

✨ Prompt Polish
...
✓ Revised:
  Could you help me write code for a fast sorting algorithm?
...
```

## Reference file

The full GEMINI.md content is included in the repo at `adapters/AGY_GEMINI.md.example` for easy copying.