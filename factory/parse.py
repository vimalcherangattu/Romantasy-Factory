"""Parses agent output. Agents return files as delimited blocks (agents/_output-format.md)."""

import json
import re

FILE_BLOCK = re.compile(
    r"^=== FILE: (?P<name>[^\n=]+?) ===[ \t]*\n(?P<body>.*?)\n=== END FILE ===[ \t]*$",
    re.DOTALL | re.MULTILINE,
)


class OutputError(ValueError):
    """Agent output is missing or malformed. The stage is retried once with this message."""


def files(text: str) -> dict[str, str]:
    found = {m.group("name").strip(): m.group("body").strip() + "\n" for m in FILE_BLOCK.finditer(text)}
    return found


def require_files(text: str, names: list[str]) -> dict[str, str]:
    found = files(text)
    missing = [n for n in names if n not in found]
    if missing:
        raise OutputError(
            f"Missing file block(s): {', '.join(missing)}. Return each as "
            "'=== FILE: <name> ===' ... '=== END FILE ==='."
        )
    return found


def json_text(text: str, label: str = "output"):
    """Parse JSON that may be wrapped in a code fence or surrounded by prose."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*\n(.*?)\n```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as exc:
                raise OutputError(f"{label} is not valid JSON: {exc}") from exc
        raise OutputError(f"{label} is not valid JSON")


def marker_list(markdown: str, name: str) -> list[str]:
    """Bullet items between <!-- name:start --> and <!-- name:end --> in a canon file."""
    m = re.search(rf"<!-- {name}:start -->(.*?)<!-- {name}:end -->", markdown, re.DOTALL)
    if not m:
        return []
    items = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip().lower())
    return items
