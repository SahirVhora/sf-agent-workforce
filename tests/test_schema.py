import json
from pathlib import Path

from agent_workforce.schema import build_schema

ROOT = Path(__file__).resolve().parents[1]


def test_committed_schema_matches_model():
    committed = json.loads((ROOT / "schema" / "agent_register.schema.json").read_text())
    assert committed == build_schema(), (
        "Regenerate: python -m agent_workforce.schema > schema/agent_register.schema.json"
    )


def test_examples_use_only_schema_fields():
    props = build_schema()["properties"]["agents"]["items"]["properties"]
    for name in ("clean_register.json", "demo_with_findings.json"):
        for a in json.loads((ROOT / "examples" / name).read_text())["agents"]:
            assert set(a) <= set(props), f"{name}: unknown fields {set(a) - set(props)}"


def test_every_check_documented():
    from agent_workforce.checks import CHECKS

    doc = (ROOT / "docs" / "CHECKS.md").read_text()
    missing = [cid for cid, _ in CHECKS if f"| {cid} |" not in doc]
    assert not missing, missing


def test_field_mapping_covers_schema():
    import csv

    props = build_schema()["properties"]["agents"]["items"]["properties"]
    with open(ROOT / "templates" / "field_mapping.csv", newline="") as fh:
        mapped = {r["register_field"] for r in csv.DictReader(fh)}
    assert mapped == set(props), set(props) ^ mapped
