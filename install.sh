#!/usr/bin/env bash
# prompt-polish installer — symlinks the CLI and prints (or applies) hook
# config snippets for whichever harnesses are detected on this machine.
#
# Usage:
#   ./install.sh          # symlink + print snippets, no config files touched
#   ./install.sh --apply  # also merge the hook into detected harness configs
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
APPLY=0
[[ "${1:-}" == "--apply" ]] && APPLY=1

mkdir -p "$BIN_DIR"
ln -sf "$HERE/polish.py" "$BIN_DIR/polish"
echo "✓ polish -> $BIN_DIR/polish (add $BIN_DIR to PATH if needed)"
echo

HOOK_CMD="python3 $HERE/adapters/polish-hook.py"

merge_json_hook() {
  # $1 = config file, $2 = event name
  python3 - "$1" "$2" "$HOOK_CMD" <<'PYEOF'
import json, sys, shutil
path, event, cmd = sys.argv[1:4]
shutil.copy(path, path + ".bak")
with open(path) as f:
    d = json.load(f)
target = d.setdefault("hooks", {})
target.setdefault(event, [])
if not any(cmd in json.dumps(h) for h in target[event]):
    target[event].append({"hooks": [{"type": "command", "command": cmd}]})
with open(path, "w") as f:
    json.dump(d, f, indent=2)
print(f"  applied to {path} (backup: {path}.bak)")
PYEOF
}

CC_SETTINGS="$HOME/.claude/settings.json"
if [[ -f "$CC_SETTINGS" ]]; then
  echo "Claude Code detected ($CC_SETTINGS)"
  if [[ $APPLY -eq 1 ]]; then
    merge_json_hook "$CC_SETTINGS" "UserPromptSubmit"
  else
    echo "  add to hooks.UserPromptSubmit: {\"hooks\":[{\"type\":\"command\",\"command\":\"$HOOK_CMD\"}]}"
  fi
  echo
fi

CODEX_HOOKS="$HOME/.codex/hooks.json"
if [[ -f "$CODEX_HOOKS" ]]; then
  echo "Codex detected ($CODEX_HOOKS)"
  if [[ $APPLY -eq 1 ]]; then
    merge_json_hook "$CODEX_HOOKS" "UserPromptSubmit"
  else
    echo "  add to hooks.UserPromptSubmit: {\"hooks\":[{\"type\":\"command\",\"command\":\"$HOOK_CMD\"}]}"
  fi
  echo
fi

HERMES_CFG="$HOME/.hermes/config.yaml"
if [[ -f "$HERMES_CFG" ]]; then
  echo "Hermes detected ($HERMES_CFG) — YAML edits are not auto-applied, add manually:"
  echo "  hooks:"
  echo "    pre_llm_call:"
  echo "      - command: $HOOK_CMD"
  echo
fi

echo "Next: polish --setup"
