"""Run the CHK-AGT catalogue over an agent register export.

Usage:
    python -m agent_workforce.validate data.json [--as-of YYYY-MM-DD]
        [--json findings.json] [--html report.html] [--max-agents-per-owner N]

Exit code: 0 no errors, 1 errors found, 2 input could not be read.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import date
from pathlib import Path

from .checks import CHECKS, ERROR, WARNING, Context, Finding
from . import model as m


def build_context(data: dict, as_of: date, max_agents_per_owner: int | None = None) -> Context:
    return Context(
        as_of=as_of,
        agents=data.get("agents", []),
        employees={e["userId"]: e for e in data.get("employees", [])},
        positions={p["code"]: p for p in data.get("positions", [])},
        cost_centers=set(data.get("costCenters", [])),
        max_agents_per_owner=(m.DEFAULT_MAX_AGENTS_PER_OWNER if max_agents_per_owner is None
                              else max_agents_per_owner),
    )


def run(ctx: Context) -> list[Finding]:
    findings: list[Finding] = []
    for check_id, fn in CHECKS:
        try:
            findings.extend(fn(ctx))
        except (ValueError, TypeError, KeyError) as exc:
            # Malformed input already reported by CHK-AGT-00; never fail silently.
            findings.append(Finding(check_id, ERROR, "*", f"Check could not run: {exc}"))
    return findings


def summary(findings: list[Finding], ctx: Context) -> dict:
    return {
        "asOf": ctx.as_of.isoformat(),
        "records": len(ctx.agents),
        "activeAgents": len(ctx.active_agents),
        "errors": sum(f.severity == ERROR for f in findings),
        "warnings": sum(f.severity == WARNING for f in findings),
    }


def render_html(findings: list[Finding], summ: dict) -> str:
    rows = "\n".join(
        f"<tr class='{f.severity.lower()}'><td>{html.escape(f.check_id)}</td>"
        f"<td>{f.severity}</td><td>{html.escape(f.agent)}</td><td>{html.escape(f.message)}</td></tr>"
        for f in sorted(findings, key=lambda x: (x.severity != ERROR, x.check_id, x.agent))
    ) or "<tr><td colspan='4'>No findings. Register passes all checks.</td></tr>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Register Validation</title>
<style>
:root{{--bg:#fff;--fg:#1b1f24;--muted:#5b6470;--err:#b42318;--warn:#a15c07;--line:#e3e6ea}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111418;--fg:#e8eaed;--muted:#9aa3ad;--err:#ff8a80;--warn:#ffcc80;--line:#2a2f36}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0;padding:24px 16px}}
h1{{font-size:20px;margin:0 0 4px}}p{{color:var(--muted);margin:0 0 16px}}
.tiles{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}}
.tile{{border:1px solid var(--line);border-radius:8px;padding:10px 14px;min-width:110px}}
.tile b{{display:block;font-size:22px}}
.wrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;min-width:560px}}
th,td{{text-align:left;padding:8px;border-bottom:1px solid var(--line);vertical-align:top}}
tr.error td:nth-child(2){{color:var(--err);font-weight:600}}tr.warning td:nth-child(2){{color:var(--warn);font-weight:600}}
</style></head><body>
<h1>Agent register validation</h1>
<p>As of {summ['asOf']}. CHK-AGT catalogue, EU AI Act references per Regulation (EU) 2024/1689 as amended by 2026/1744.</p>
<div class="tiles">
<div class="tile"><b>{summ['records']}</b>records</div>
<div class="tile"><b>{summ['activeAgents']}</b>active agents</div>
<div class="tile"><b>{summ['errors']}</b>errors</div>
<div class="tile"><b>{summ['warnings']}</b>warnings</div>
</div>
<div class="wrap"><table><thead><tr><th>Check</th><th>Severity</th><th>Agent / owner</th><th>Finding</th></tr></thead>
<tbody>
{rows}
</tbody></table></div></body></html>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path)
    ap.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    ap.add_argument("--json", type=Path)
    ap.add_argument("--html", type=Path)
    ap.add_argument("--max-agents-per-owner", type=int)
    args = ap.parse_args(argv)

    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Cannot read {args.input}: {exc}", file=sys.stderr)
        return 2

    ctx = build_context(data, args.as_of, args.max_agents_per_owner)
    findings = run(ctx)
    summ = summary(findings, ctx)

    for f in sorted(findings, key=lambda x: (x.check_id, x.agent)):
        print(f"{f.check_id}  {f.severity:<7}  {f.agent:<18}  {f.message}")
    print(f"\n{summ['activeAgents']} active of {summ['records']} records: "
          f"{summ['errors']} errors, {summ['warnings']} warnings")

    if args.json:
        args.json.write_text(json.dumps({"summary": summ, "findings": [f.to_dict() for f in findings]},
                                        indent=2), encoding="utf-8")
    if args.html:
        args.html.write_text(render_html(findings, summ), encoding="utf-8")
    return 1 if summ["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
