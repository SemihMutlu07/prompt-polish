# Changelog

## v0.1.0 (2026-07-05)

### Features
- Initial release: CLI tool for improving English prompts with Turkish explanations
- **Three backends:** OpenRouter/OpenAI API key, or `claude -p` fallback (reuses Claude Code auth — no extra API key needed)
- **Interactive mode:** Shows a formatted card with Original → Revised + Improvements + Vocabulary
- **Slash-command skip:** Prompts starting with `/` are ignored (hooks don't interfere with commands)
- **Fail-open everywhere:** Any error, timeout, or auth failure passes the original prompt through untouched

### Hooks & Integration
- **Claude Code:** `UserPromptSubmit` hook via `adapters/polish-hook.py`
- **Codex CLI:** `UserPromptSubmit` hook via `adapters/polish-hook.py`
- **AGY (Antigravity/Gemini CLI):** System instruction embedding in `GEMINI.md` (zero-token, no extra API call)
- **Hermes:** `pre_llm_call` hook (YAML config)
- **Auto-installer:** `./install.sh --apply` detects and configures Claude Code + Codex (Hermes: manual YAML edit)
- **Universal adapter:** Single `polish-hook.py` handles all three harness formats (Claude/Codex plain JSON, Hermes `extra.user_message`, fail-open on all)

### Proof
- `PROOF-claude.md`, `PROOF-codex.md`, `PROOF-AGY.md` — verified integration docs
- `adapters/AGY_GEMINI.md.example` — ready-to-copy GEMINI.md config
- GitHub Actions CI (Python 3.10–3.13) on every push

### Distribution
- Source: `pip install git+https://github.com/SemihMutlu07/prompt-polish`
- PyPI: (pending — `pip install prompt-polish` TBD)
- Zero dependencies (stdlib only, Python 3.10+)

### Technical
- `call_claude()` — uses `claude -p --print` subprocess when no API key configured
- `_get_polish()` — tries API key first, falls back to claude
- All functionality tested (15/15 checks in `test_polish.py`, no network required)
