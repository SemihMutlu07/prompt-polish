# 🧪 Prompt Polish — Proof: Claude Code Integration

**Date:** 2026-07-05
**Tool version:** v0.1.0
**Hook adapter:** `adapters/polish-hook.py`

## How It Works

1. `polish-hook.py` is registered as a `UserPromptSubmit` hook in Claude Code's `~/.claude/settings.json`
2. Every prompt you type in Claude Code is intercepted before reaching the LLM
3. The hook calls `polish.py --hook` which:
   - Tries OpenRouter/OpenAI API key if configured
   - Falls back to `claude -p` sub-call (uses Claude Code's own auth — no extra API key needed)
4. If polish succeeds: the card is printed to your terminal and a context note is injected telling Claude "this user is practicing English, treat this revised version as authoritative"
5. If polish fails: the prompt passes through untouched (fail-open, never blocks)

## Verification

### Manual test (standalone hook):

```bash
echo '{"prompt": "write code for sort algorithm fastly"}' \
  | python3 adapters/polish-hook.py
```

Expected output (when Claude Code has active auth):
```json
{
  "revised": "Could you help me write code for a fast sorting algorithm?",
  "context": "[prompt-polish] The user is practicing English...",
  "card": "╭──────────────────────────────────────╮\n│ ✨ Prompt Polish..."
}
```

And the card renders to your terminal via `/dev/tty`.

### Unit tests:

```bash
python3 test_polish.py
# → ok — 15/15 checks passed
```

### Hook edge cases verified:
| Scenario | Result |
|----------|--------|
| Claude auth active | Card shown, context injected |
| No API key, no claude auth | Fail-open: empty stdout, exit 0 |
| Slash command (`/model`) | Skipped immediately |
| `POLISH_HOOK_DISABLE=1` | Skipped immediately |
| Broken JSON stdin | Fail-open: empty stdout, exit 0 |
| Hermes schema (pre_llm_call) | Correctly parsed |

## Installation

```bash
cd ~/dev/prompt-polish
./install.sh --apply
```

This adds the hook to `~/.claude/settings.json` `hooks.UserPromptSubmit` (with backup).