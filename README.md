# sf-agent-workforce

**A reference data model and validator for AI agents held as workers in SAP SuccessFactors.**

Agents already validate payroll, screen applications and answer employee queries. Almost nobody records them where work is planned, costed and governed. This repo gives you:

- **A data model** (`docs/DATA_MODEL.md`) for an effective-dated `cust_DigitalWorker` MDF object with accountable owner, kill-switch owner, cost centre, position, decision scopes, oversight mode and expiring permissions. Agents sit beside employees, never as employees.
- **An EU AI Act mapping** from decision scopes to Annex III point 4 and the Article 5(1)(f) prohibition, using the dates in Regulation (EU) 2026/1744.
- **A validator** running 15 CHK-AGT checks over a register export, with console, JSON and HTML output and a CI-friendly exit code.

## Quick start

```bash
python -m agent_workforce.validate examples/demo_with_findings.json --as-of 2026-10-10 --html report.html
python -m pytest -q
```

No runtime dependencies. Python 3.10+. Tests need `pytest`.

Exit codes: `0` clean, `1` errors found, `2` input unreadable.

## Input

One JSON file: `agents`, `employees` (userId, status), `positions` (code, status, staffingType) and `costCenters`. Schema: `schema/agent_register.schema.json`, generated from `agent_workforce/model.py` and tested for drift. Pull it from SuccessFactors via OData v2 on `cust_DigitalWorker`, `PerPerson`/`EmpEmployment`, `Position` and `FOCostCenter`.

## Layout

```
agent_workforce/  model.py (enums, thresholds)  checks.py (CHK-AGT-00..14)  validate.py (CLI)  schema.py
docs/             DATA_MODEL.md  CHECKS.md
examples/         clean_register.json  demo_with_findings.json
schema/           agent_register.schema.json
templates/        field_mapping.csv (register field to MDF field and picklist)
tests/            37 tests incl. boundary cases and doc/schema drift guards
```

## Limits

This checks the register, not the law. A clean run is evidence of control, not a conformity assessment or legal advice. The 365-day permission cap and 10-agents-per-owner threshold are house defaults.

Part of [SF Compass](https://sahirvhora.github.io/sf-compass/).
