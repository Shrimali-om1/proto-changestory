from __future__ import annotations

from dataclasses import dataclass, field


class DiffParseError(ValueError):
    pass


@dataclass
class FileChange:
    path: str
    change_type: str = "modified"
    added_lines: list[tuple[int, str]] = field(default_factory=list)
    deleted_lines: list[tuple[int, str]] = field(default_factory=list)


def _path(value: str) -> str:
    value = value.strip().split("\t", 1)[0]
    return value[2:] if value.startswith(("a/", "b/")) else value


def parse_unified_diff(diff_text: str) -> list[FileChange]:
    """Parse the structural portions of a standard unified Git diff."""
    if not diff_text.strip():
        raise DiffParseError("A unified diff is required.")
    result: list[FileChange] = []
    current: FileChange | None = None
    old_line = new_line = 0
    in_hunk = False

    for raw in diff_text.splitlines():
        if raw.startswith("diff --git "):
            parts = raw.split()
            if len(parts) < 4:
                raise DiffParseError("Malformed Git diff file header.")
            current = FileChange(path=_path(parts[3]))
            result.append(current)
            in_hunk = False
            continue
        if current is None:
            continue
        if raw.startswith("new file mode"):
            current.change_type = "added"
        elif raw.startswith("deleted file mode"):
            current.change_type = "deleted"
        elif raw.startswith("rename from ") or raw.startswith("rename to "):
            current.change_type = "renamed"
            if raw.startswith("rename to "):
                current.path = raw.removeprefix("rename to ").strip()
        elif raw.startswith("+++ "):
            path = raw[4:].strip()
            if path == "/dev/null":
                current.change_type = "deleted"
            else:
                current.path = _path(path)
        elif raw.startswith("@@ "):
            try:
                pieces = raw.split("@@", 2)[1].strip().split()
                old = pieces[0][1:].split(",")[0]
                new = pieces[1][1:].split(",")[0]
                old_line, new_line = int(old), int(new)
            except (IndexError, ValueError) as error:
                raise DiffParseError("Malformed unified diff hunk header.") from error
            in_hunk = True
        elif in_hunk and raw.startswith("+") and not raw.startswith("+++"):
            current.added_lines.append((new_line, raw[1:]))
            new_line += 1
        elif in_hunk and raw.startswith("-") and not raw.startswith("---"):
            current.deleted_lines.append((old_line, raw[1:]))
            old_line += 1
        elif in_hunk and raw.startswith(" "):
            old_line += 1
            new_line += 1
        elif in_hunk and raw.startswith("\\ No newline"):
            continue
    if not result or not any(f.added_lines or f.deleted_lines for f in result):
        raise DiffParseError("No changed lines were found in the unified diff.")
    return sorted(result, key=lambda item: item.path)
