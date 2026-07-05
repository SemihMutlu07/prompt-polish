# 🧪 Prompt Polish — Proof: Codex Integration

**Date:** 2026-07-05
**Tool version:** v0.1.0
**Hook adapter:** `adapters/polish-hook.py`

## How It Works

Identical mechanism to Claude Code — Codex CLI uses the same `UserPromptSubmit` hook contract. The adapter reads `{"prompt": "..."}` from stdin, calls polish, and outputs plain text context on stdout.

## Verification

### Codex hooks.json entry:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /home/parkermutsuz/dev/prompt-polish/adapters/polish-hook.py"
          }
        ]
      }
    ]
  }
}
```

### Manual test (standalone, same stdin format):

```bash
echo '{"prompt": "write code for sort algorithm fastly"}' \
  | python3 adapters/polish-hook.py
```

### Unit tests:

```bash
python3 test_polish.py
# → ok — 15/15 checks passed
```

Includes adapter-specific tests:
- Codex/Claude schema (`hook_event_name: UserPromptSubmit`) → correct parsing
- Broken JSON → fail-open
- Slash commands → skip
- `POLISH_HOOK_DISABLE` → skip

## Installation

```bash
cd ~/dev/prompt-polish
./install.sh --apply
```

This adds the hook to `~/.codex/hooks.json` `hooks.UserPromptSubmit` (with backup).