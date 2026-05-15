#!/usr/bin/env python3
"""Validate GitHub issue / PR body against the Rich template.

Usage:
    cat body.md | python scripts/check_template.py --kind issue
    python scripts/check_template.py --kind pr --file /tmp/body.md

Exit codes:
    0 — body passes; required sections present with non-trivial content
    1 — body fails; diagnostic printed to stderr listing missing / empty sections
    2 — usage error

The script is reused by:
- .claude/hooks/validate_gh_body.sh (PreToolUse — blocks `gh issue/pr create`)
- .github/workflows/check-pr-body.yml (PR-open backstop)
- Manual invocation when drafting

Template spec is anchored in .github/ISSUE_TEMPLATE/feature.md and
.github/pull_request_template.md — keep REQUIRED_SECTIONS in sync if you
change the template structure.
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Final

MIN_SECTION_CHARS: Final[int] = 30

REQUIRED_SECTIONS: Final[dict[str, tuple[str, ...]]] = {
    "issue": (
        "Problem",
        "Outcome",
        "Demo",
        "Scope",
        "Acceptance criteria",
        "Risk",
        "Anchor",
    ),
    "pr": (
        "What changed",
        "Why this matters",
        "Demo",
        "Risk",
        "Reviewer checklist",
        "Tests",
    ),
}


def _split_sections(body: str) -> dict[str, str]:
    """Return {heading_text: section_body} for every `## Heading` block.

    Heading match is case-sensitive and exact (after stripping trailing
    whitespace). Body is everything until the next `## ` or end-of-file.
    """
    sections: dict[str, str] = {}
    pattern = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(body))
    for i, m in enumerate(matches):
        heading = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[heading] = body[start:end].strip()
    return sections


def _find_section(sections: dict[str, str], canonical: str) -> str | None:
    """Match a heading by case-insensitive prefix.

    `canonical='What changed'` matches `## What changed` and also longer
    elaborations like `## What changed for a dashboard user`. This lets PR
    authors write more descriptive headings without breaking validation.
    Returns the section body, or None if no heading starts with `canonical`.
    """
    canon = canonical.lower()
    for heading, content in sections.items():
        if heading.lower().startswith(canon):
            return content
    return None


def validate(body: str, kind: str) -> list[str]:
    """Return list of human-readable errors. Empty list = passes."""
    required = REQUIRED_SECTIONS[kind]
    sections = _split_sections(body)
    errors: list[str] = []

    for name in required:
        content = _find_section(sections, name)
        if content is None:
            errors.append(f"missing required section: `## {name}`")
            continue
        # Strip HTML comments (inline template hints) before counting chars.
        stripped = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL).strip()
        if len(stripped) < MIN_SECTION_CHARS:
            errors.append(
                f"section `## {name}` is too short "
                f"({len(stripped)} chars, need ≥{MIN_SECTION_CHARS}). "
                f"Did you fill in the scaffold?"
            )

    return errors


def _read_body(path: str | None) -> str:
    if path:
        with open(path, encoding="utf-8") as f:
            return f.read()
    return sys.stdin.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate issue/PR body against the Rich template."
    )
    parser.add_argument(
        "--kind",
        choices=sorted(REQUIRED_SECTIONS),
        required=True,
        help="What kind of body to validate.",
    )
    parser.add_argument(
        "--file",
        help="Path to body file. If omitted, reads from stdin.",
        default=None,
    )
    args = parser.parse_args(argv)

    body = _read_body(args.file)
    if not body.strip():
        print("template check: empty body", file=sys.stderr)
        return 1

    errors = validate(body, args.kind)
    if errors:
        print(
            f"template check FAILED for {args.kind} body — {len(errors)} issue(s):",
            file=sys.stderr,
        )
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(
            f"\nExpected sections: {', '.join(f'## {s}' for s in REQUIRED_SECTIONS[args.kind])}",
            file=sys.stderr,
        )
        print(
            "See .github/ISSUE_TEMPLATE/feature.md or "
            ".github/pull_request_template.md for the canonical scaffold.",
            file=sys.stderr,
        )
        return 1

    print(f"template check: {args.kind} body OK", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
