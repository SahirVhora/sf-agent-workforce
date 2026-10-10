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

touch "$DIST/.nojekyll"
find "$DIST" -type f | sort | sed "s#^$DIST/##"
