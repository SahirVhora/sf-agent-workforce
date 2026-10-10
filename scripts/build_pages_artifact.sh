#!/usr/bin/env bash
# Build the public GitHub Pages artifact into dist/. Only allow-listed files ship.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="$ROOT/dist"
rm -rf "$DIST"
mkdir -p "$DIST"

for path in index.html favicon.svg preview.png robots.txt sitemap.xml schema downloads; do
  cp -R "$ROOT/$path" "$DIST/$path"
done

# Sample report, regenerated from the demo register on every build.
# Exit code 1 is expected: the demo register deliberately contains findings.
cd "$ROOT"
rc=0
python3 -m agent_workforce.validate examples/demo_with_findings.json \
  --as-of 2026-10-10 --html "$DIST/sample-report.html" >/dev/null || rc=$?
if [ "$rc" -ne 1 ]; then
  echo "Expected the demo register to produce findings (exit 1), got $rc" >&2
  exit 1
fi

# Give the public sample page proper metadata and a route back to the landing page.
python3 - "$DIST/sample-report.html" <<'PY'
import sys
from pathlib import Path

page = Path(sys.argv[1])
base = "https://sahirvhora.github.io/sf-agent-workforce/"
head = (
    '<meta name="description" content="Sample CHK-AGT validation report for an AI agent register in SAP '
    'SuccessFactors, showing EU AI Act findings such as missing oversight and expired permissions.">\n'
    f'<link rel="canonical" href="{base}sample-report.html">\n'
    '<link rel="icon" type="image/svg+xml" href="favicon.svg">\n'
)
back = f'<p><a href="{base}">&larr; SF Agent Workforce: data model, checks and free EU AI Act HR checklist</a></p>\n'
html = page.read_text(encoding="utf-8")
html = html.replace("<title>Agent Register Validation</title>", "<title>Sample AI Agent Register Validation Report</title>\n" + head, 1)
html = html.replace("<h1>", back + "<h1>", 1)
page.write_text(html, encoding="utf-8")
PY

touch "$DIST/.nojekyll"
find "$DIST" -type f | sort | sed "s#^$DIST/##"
