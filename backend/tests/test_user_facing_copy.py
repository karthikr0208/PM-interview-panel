"""The em-dash ban, enforced against the code rather than trusted to reviewers.

CLAUDE.md § Design: "No em-dashes in user-facing UI copy. Docs are exempt;
anything a candidate reads is not." Story 1.2 shipped three em-dashes into
candidate-facing error messages anyway, in a function whose own docstring said
"the message is written for the candidate reading it" - so the author knew the
strings were user-facing and the rule still did not survive contact. That is
the definition of a rule needing a test instead of a reviewer.

Deliberately narrow: it inspects only strings passed to `HTTPException(...)`
and to `*Error(...)` constructors, which is what actually reaches a candidate.
Docstrings, comments, and developer-facing exceptions are exempt by the rule
itself, and a check that flagged them would be noise nobody keeps green.

Offline, no network, no database.
"""

from __future__ import annotations

import ast
import pathlib

APP_ROOT = pathlib.Path(__file__).resolve().parent.parent / "app"

EM_DASH = "—"
EN_DASH = "–"

# Raised at import/wiring time and read only by a developer. Phase 1 leaves the
# real graph unwired on purpose; story 1.4 replaces this.
DEVELOPER_FACING = {"NotImplementedError", "ConfigError", "StructuredOutputError"}


def _literal(node: ast.AST) -> str | None:
    """Best-effort constant text of an argument. Handles plain strings,
    implicit concatenation (a BinOp of constants after parsing), and f-strings,
    reading only their constant parts.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value for v in node.values if isinstance(v, ast.Constant))
    if isinstance(node, ast.BinOp):
        return "".join(
            c.value
            for c in ast.walk(node)
            if isinstance(c, ast.Constant) and isinstance(c.value, str)
        )
    return None


def _user_facing_strings() -> list[tuple[str, int, str, str]]:
    found: list[tuple[str, int, str, str]] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            name = node.func.id
            if name in DEVELOPER_FACING:
                continue
            if not (name == "HTTPException" or name.endswith("Error")):
                continue
            for arg in node.args:
                text = _literal(arg)
                if text:
                    found.append((path.name, node.lineno, name, text))
    return found


def test_the_check_finds_real_user_facing_strings() -> None:
    """Guards the guard. An AST walk that silently matches nothing would make
    every assertion below vacuously true - the same failure shape as a
    cross-session denial test whose token is malformed.
    """
    strings = _user_facing_strings()
    assert len(strings) >= 5, f"expected to find real user-facing copy, got {strings}"
    assert any("PDF" in text for _, _, _, text in strings), (
        "story 1.2's upload error messages should be in scope for this check"
    )


def test_no_em_dashes_in_user_facing_copy() -> None:
    offenders = [
        f"{f}:{line} {call}() -> {text[:80]}"
        for f, line, call, text in _user_facing_strings()
        if EM_DASH in text
    ]
    assert not offenders, "em-dash in candidate-facing copy (CLAUDE.md § Design):\n" + "\n".join(
        offenders
    )


def test_no_en_dashes_in_user_facing_copy() -> None:
    offenders = [
        f"{f}:{line} {call}() -> {text[:80]}"
        for f, line, call, text in _user_facing_strings()
        if EN_DASH in text
    ]
    assert not offenders, "en-dash in candidate-facing copy:\n" + "\n".join(offenders)
