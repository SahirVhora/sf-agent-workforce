import copy
import json
from datetime import date
from pathlib import Path

import pytest

from agent_workforce.validate import build_context, run, main
from agent_workforce.checks import CHECKS

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 10, 10)


@pytest.fixture
def clean():
    return json.loads((ROOT / "examples" / "clean_register.json").read_text())


def ids(data, as_of=AS_OF, **kw):
    return sorted({f.check_id for f in run(build_context(data, as_of, **kw))})


def agent(data, code="AGT-PAY-01"):
    return next(a for a in data["agents"] if a["externalCode"] == code)


def test_clean_register_passes(clean):
    assert run(build_context(clean, AS_OF)) == []


def test_catalogue_ids_unique_and_sequential():
    got = [cid for cid, _ in CHECKS]
    assert got == [f"CHK-AGT-{i:02d}" for i in range(15)]


def test_00_missing_field(clean):
    del agent(clean)["costCenter"]
    assert "CHK-AGT-00" in ids(clean)


def test_00_bad_enum_and_scope(clean):
    agent(clean)["agentType"] = "ROBOT"
    agent(clean)["decisionScopes"].append("mind_reading")
    msgs = [f.message for f in run(build_context(clean, AS_OF)) if f.check_id == "CHK-AGT-00"]
    assert any("agentType" in m for m in msgs) and any("mind_reading" in m for m in msgs)


def test_00_bad_date_does_not_crash(clean):
    agent(clean)["nextReviewDate"] = "31/12/2026"
    found = ids(clean)
    assert "CHK-AGT-00" in found  # reported, and the run completed


def test_01_inactive_owner(clean):
    clean["employees"][0]["status"] = "TERMINATED"
    assert "CHK-AGT-01" in ids(clean)


def test_02_missing_kill_switch(clean):
    agent(clean)["killSwitchOwnerUserId"] = "E0000"
    assert "CHK-AGT-02" in ids(clean)


def test_03_employment_scope_misclassified(clean):
    agent(clean)["decisionScopes"] = ["promotion_decision"]
    assert "CHK-AGT-03" in ids(clean)


def test_04_high_risk_without_oversight(clean):
    agent(clean, "AGT-REC-01")["humanOversightMode"] = "NONE"
    assert "CHK-AGT-04" in ids(clean)


def test_04_applies_to_implied_high_risk(clean):
    a = agent(clean)
    a["decisionScopes"] = ["termination_decision"]
    a["humanOversightMode"] = "NONE"
    assert {"CHK-AGT-03", "CHK-AGT-04"} <= set(ids(clean))


@pytest.mark.parametrize("days,flag", [(182, True), (183, False), (None, True)])
def test_05_log_retention_boundary(clean, days, flag):
    a = agent(clean, "AGT-REC-01")
    if days is None:
        a.pop("logRetentionDays")
    else:
        a["logRetentionDays"] = days
    assert ("CHK-AGT-05" in ids(clean)) is flag


def test_06_worker_info_after_go_live(clean):
    agent(clean, "AGT-REC-01")["workerRepsInformedDate"] = "2026-09-02"
    assert "CHK-AGT-06" in ids(clean)


def test_06_same_day_is_allowed(clean):
    agent(clean, "AGT-REC-01")["workerRepsInformedDate"] = "2026-09-01"
    assert "CHK-AGT-06" not in ids(clean)


def test_07_no_expiry(clean):
    agent(clean)["permissions"][0].pop("expiryDate")
    assert "CHK-AGT-07" in ids(clean)


@pytest.mark.parametrize("expiry,flag", [("2027-04-01", False), ("2027-04-02", True)])
def test_07_max_duration_boundary(clean, expiry, flag):
    agent(clean)["permissions"][0]["expiryDate"] = expiry  # granted 2026-04-01; 365 days = 2027-04-01
    assert ("CHK-AGT-07" in ids(clean)) is flag


def test_08_expired_still_active(clean):
    p = agent(clean)["permissions"][0]
    p["grantedDate"], p["expiryDate"] = "2025-10-01", "2026-10-09"
    assert "CHK-AGT-08" in ids(clean)


def test_08_revoked_expired_is_fine(clean):
    p = agent(clean)["permissions"][0]
    p["grantedDate"], p["expiryDate"], p["status"] = "2025-10-01", "2026-10-09", "REVOKED"
    assert "CHK-AGT-08" not in ids(clean)


def test_08_catches_suspended_agent(clean):
    a = agent(clean)
    a["status"] = "SUSPENDED"
    a["permissions"][0].update(grantedDate="2025-10-01", expiryDate="2026-10-01")
    assert "CHK-AGT-08" in ids(clean)


@pytest.mark.parametrize("change", [
    {"positionCode": "POS-NOPE"},
])
def test_09_unknown_position(clean, change):
    agent(clean).update(change)
    assert "CHK-AGT-09" in ids(clean)


def test_09_human_position(clean):
    clean["positions"][0]["staffingType"] = "HUMAN"
    assert "CHK-AGT-09" in ids(clean)


def test_10_unknown_cost_center(clean):
    agent(clean)["costCenter"] = "CC-XXX"
    assert "CHK-AGT-10" in ids(clean)


def test_11_review_overdue_is_warning(clean):
    agent(clean)["nextReviewDate"] = "2026-10-09"
    f = [x for x in run(build_context(clean, AS_OF)) if x.check_id == "CHK-AGT-11"]
    assert f and f[0].severity == "WARNING"


def test_12_overlap(clean):
    dup = copy.deepcopy(agent(clean))
    dup["effectiveStartDate"] = "2026-09-01"
    clean["agents"].append(dup)
    assert "CHK-AGT-12" in ids(clean)


def test_12_contiguous_records_ok(clean):
    a = agent(clean)
    a["effectiveEndDate"] = "2026-08-31"
    nxt = copy.deepcopy(a)
    nxt["effectiveStartDate"], nxt["effectiveEndDate"] = "2026-09-01", None
    nxt.pop("effectiveEndDate")
    clean["agents"].append(nxt)
    assert "CHK-AGT-12" not in ids(clean)


def test_13_owner_span(clean):
    assert "CHK-AGT-13" in ids(clean, max_agents_per_owner=0)
    assert "CHK-AGT-13" not in ids(clean, max_agents_per_owner=1)


def test_14_prohibited_scope(clean):
    agent(clean)["decisionScopes"] = ["workplace_emotion_recognition"]
    assert "CHK-AGT-14" in ids(clean)


def test_future_dated_agent_not_active(clean):
    agent(clean)["effectiveStartDate"] = "2026-12-01"
    agent(clean)["ownerUserId"] = "NOBODY"
    assert "CHK-AGT-01" not in ids(clean)


def test_demo_register_hits_every_designed_check():
    data = json.loads((ROOT / "examples" / "demo_with_findings.json").read_text())
    expected = {f"CHK-AGT-{i:02d}" for i in range(15)} - {"CHK-AGT-13"}
    assert expected <= set(ids(data))


def test_cli_exit_codes_and_reports(tmp_path):
    out_json, out_html = tmp_path / "f.json", tmp_path / "r.html"
    assert main([str(ROOT / "examples" / "clean_register.json"), "--as-of", "2026-10-10"]) == 0
    rc = main([str(ROOT / "examples" / "demo_with_findings.json"), "--as-of", "2026-10-10",
               "--json", str(out_json), "--html", str(out_html)])
    assert rc == 1
    report = json.loads(out_json.read_text())
    assert report["summary"]["errors"] > 0
    assert "<table>" in out_html.read_text()


def test_cli_unreadable_input(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert main([str(bad)]) == 2
