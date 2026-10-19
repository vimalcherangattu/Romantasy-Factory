#!/usr/bin/env bash
# Prepares a fresh Claude Code cloud container to run the factory. Runs from the
# SessionStart hook in .claude/settings.json; does nothing on the owner's Mac.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "$(dirname "$0")/.."

python3 -c "import typer, yaml, PIL, docx, pytest, weasyprint" 2>/dev/null \
  || pip install --break-system-packages -q -e ".[dev]" >/dev/null 2>&1 \
  || pip install --break-system-packages -q typer pyyaml pillow python-docx pytest weasyprint >/dev/null 2>&1
python3 -c "import factory" 2>/dev/null || pip install --break-system-packages -q -e . >/dev/null 2>&1 || true

# epubcheck: the PyPI wheel bundles the official jar; Java is preinstalled.
if [ ! -f "$HOME/.local/share/epubcheck/epubcheck.jar" ]; then
  tmp=$(mktemp -d)
  pip download --no-deps -q epubcheck -d "$tmp" >/dev/null 2>&1 \
    && (cd "$tmp" && python3 -m zipfile -e epubcheck-*.whl x >/dev/null) \
    && mkdir -p "$HOME/.local/share/epubcheck" \
    && cp -r "$tmp"/x/epubcheck/epubcheck.jar "$tmp"/x/epubcheck/lib "$HOME/.local/share/epubcheck/" || true
  rm -rf "$tmp"
fi

git config user.name >/dev/null || git config user.name "Romantasy Factory"
git config user.email >/dev/null || git config user.email "factory@users.noreply.github.com"
echo "Romantasy Factory: cloud container ready"
