#!/usr/bin/env python3
"""PreToolUse hook — validate `gh issue create` / `gh pr create` body.

Wired in .claude/settings.json. Reads the Bash tool input JSON from stdin,
detects gh issue/pr create commands, extracts the body via `--body` or
`--body-file`, and runs scripts/check_template.py. Blocks the call (exit 2)
when validation fails so Claude sees the diagnostic.

Designed to be permissive on extraction failure — if the body uses a complex
shell construct (heredoc subshell, etc.) we can't parse, allow through and
let the GitHub Action backstop catch it.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VALIDATOR = REPO_ROOT / "scripts" / "check_template.py"


def _extract(command: str) -> tuple[str | None, str | None]:
    """Return (kind, body). Either may be None if not extractable."""
    if "gh issue create" in command:
        kind = "issue"
    elif "gh pr create" in command:
        kind = "pr"
    else:
        return None, None

    try:
        tokens = shlex.split(command)
    except ValueError:
        return kind, None  # unbalanced quotes — let it through

    body: str | None = None
    for i, tok in enumerate(tokens):
        if tok == "--body" and i + 1 < len(tokens):
            body = tokens[i + 1]
            break
        if tok == "--body-file" and i + 1 < len(tokens):
            raw_path = tokens[i + 1]
            path = Path(raw_path)
            if not path.is_absolute():
                path = REPO_ROOT / raw_path
            try:
                body = path.read_text()
            except OSError:
                return kind, None
            break

    return kind, body


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    command = payload.get("tool_input", {}).get("command", "")
    kind, body = _extract(command)
    if not kind or body is None:
        return 0

    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--kind", kind],
        input=body,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return 0

    print(
        f"\n🛑 Blocked: {kind} body fails template check.\n\n"
        f"{result.stderr}\n"
        f"Fix the body and retry — or pass --body-file pointing at a "
        f"validated body file.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
