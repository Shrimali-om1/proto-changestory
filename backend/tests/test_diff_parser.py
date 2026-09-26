import pytest

from app.analysis.diff_parser import DiffParseError, parse_unified_diff


def test_parser_tracks_added_and_deleted_lines() -> None:
    diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -2,2 +2,2 @@
-old
+new
 same
"""
    files = parse_unified_diff(diff)
    assert files[0].path == "a.py"
    assert files[0].added_lines == [(2, "new")]
    assert files[0].deleted_lines == [(2, "old")]


@pytest.mark.parametrize("text", ["", "not a diff"])
def test_parser_rejects_empty_or_malformed_change(text: str) -> None:
    with pytest.raises(DiffParseError):
        parse_unified_diff(text)
