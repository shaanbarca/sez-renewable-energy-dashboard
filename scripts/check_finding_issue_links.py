#!/usr/bin/env python3
"""Pre-commit hook: every "(Finding N)" reference in docs/refinement/*.md must
carry a "[#NN](https://github.com/.../issues/NN)" link to a tracked GitHub issue.

Convention established 2026-05-07. F-findings are the unit of trackable work for
refinement-spec releases (v4.0.5, v4.1a, v4.1b, v4.2, ...). Each finding gets
its own GitHub issue on shaanbarca/eez. The spec links to the issue inline so a
reader can jump from finding text → issue → branch/PR without cross-referencing
TODOS.md.

This hook fails when a finding reference exists without an issue link, which
forces the issue to be filed before the spec is committed.

Run manually:
    uv run python scripts/check_finding_issue_links.py docs/refinement/*.md

Pre-commit invocation: passes file paths as positional args.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Pattern A: "(Finding N)" — needs issue link added
# Pattern B: "(Finding N, [#NN](...))" — already linked, OK
PATTERN_BARE = re.compile(r"\(Finding (\d+)\)(?!,)")
PATTERN_LINKED = re.compile(r"\(Finding (\d+), \[#(\d+)\]\(https://github\.com/[^)]+\)\)")


def check_file(path: Path) -> list[str]:
    """Return list of error messages (empty = clean)."""
    errors: list[str] = []
    if not path.exists():
        return errors
    text = path.read_text()
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in PATTERN_BARE.finditer(line):
            n = m.group(1)
            errors.append(
                f"{path}:{lineno} — Finding {n} has no issue link. "
                f'Add "(Finding {n}, [#NN](https://github.com/shaanbarca/eez/issues/NN))" '
                f"and file the issue if it doesn't exist yet."
            )
    return errors


def main() -> int:
    paths = [Path(p) for p in sys.argv[1:]] or list(Path("docs/refinement").glob("*.md"))
    paths = [p for p in paths if p.suffix == ".md" and "refinement" in str(p)]

    all_errors: list[str] = []
    for p in paths:
        all_errors.extend(check_file(p))

    if all_errors:
        print("\n".join(all_errors), file=sys.stderr)
        print(
            f"\n{len(all_errors)} F-finding reference(s) missing issue links. "
            f"File issues at https://github.com/shaanbarca/eez/issues then add the "
            f"`[#NN](.../issues/NN)` link to the spec.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
