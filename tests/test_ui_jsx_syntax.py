"""JSX syntax smoke test -- catches known parse-error patterns."""

import re
from pathlib import Path

import pytest

JSX_DIR = Path(__file__).parent.parent / "src" / "dual_research" / "ui" / "static"

# Pattern: a JSX prop expression slot (`prop={`) immediately followed
# (with optional whitespace/newline) by a JSX comment opening (`{/*`).
# Babel cannot parse `prop={ {/* ... */} <Child/>}` -- the outer `{` is
# interpreted as starting a nested object literal.
#
# Was the root cause of the v0.63.0 white-screen regression on the
# run-detail page (see SPEC-0077).
BROKEN_PROP_COMMENT = re.compile(r"=\{\s*\n?\s*\{\s*/\*")


def jsx_files():
    return sorted(JSX_DIR.glob("*.jsx"))


@pytest.mark.parametrize("path", jsx_files(), ids=lambda p: p.name)
def test_no_jsx_comment_in_prop_expression_slot(path):
    """JSX comments {/* */} inside prop expression slots (prop={ {/* */} })
    cause a Babel parse error. This pattern caused SPEC-0077."""
    text = path.read_text()
    matches = list(BROKEN_PROP_COMMENT.finditer(text))
    if matches:
        snippets = []
        for m in matches:
            lineno = text[: m.start()].count("\n") + 1
            line = text.splitlines()[lineno - 1]
            snippets.append(f"  {path.name}:{lineno}: {line.strip()}")
        pytest.fail(
            "Found JSX-comment-in-prop-expression pattern "
            "(prop={ {/* ... */} ...) -- Babel will fail to parse this. "
            "Move the comment out of the prop expression slot.\n"
            + "\n".join(snippets)
        )
