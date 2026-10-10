"""CHK-AGT check catalogue.

Each check takes a Context and returns a list of Finding objects.
Checks never mutate input. Dates are ISO strings (YYYY-MM-DD).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Callable

from . import model as m

ERROR = "ERROR"
WARNING = "WARNING"


@dataclass
class Finding:
    check_id: str
    severity: str
    agent: str
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Context:
    as_of: date
    agents: list[dict]
    employees: dict[str, dict]
    positions: dict[str, dict]
    cost_centers: set[str]
    max_agents_per_owner: int = m.DEFAULT_MAX_AGENTS_PER_OWNER
    _active: list[dict] | None = field(default=None, repr=False)

    @property
    def active_agents(self) -> list[dict]:
        """Records with status ACTIVE whose effective window covers as_of."""
        if self._active is None:
            self._active = [a for a in self.agents if is_current(a, self.as_of)
                            and a.get("status") == "ACTIVE"]
        return self._active


def d(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def is_current(agent: dict, as_of: date) -> bool:
    start = d(agent.get("effectiveStartDate"))
    end = d(agent.get("effectiveEndDate")) or date.max
    return start is not None and start <= as_of <= end


def _employee_active(ctx: Context, user_id: str | None) -> bool:
    emp = ctx.employees.get(user_id or "")
    return bool(emp) and emp.get("status") == "ACTIVE"


def is_high_risk(agent: dict) -> bool:
    """Effective high-risk status: declared, or implied by employment scopes.

    Using the implied status stops a misclassification (caught by CHK-AGT-03)
    from also hiding the oversight, logging and worker-information gaps.
    """
    return (agent.get("riskClassification") == "HIGH_RISK_ANNEX_III"
            or bool(set(agent.get("decisionScopes") or []) & m.EMPLOYMENT_SCOPES))


def _code(agent: dict) -> str:
    return agent.get("externalCode", "<missing externalCode>")


# ---------------------------------------------------------------- checks

def chk_00_structure(ctx: Context) -> list[Finding]:
    """Required fields present and enumerations valid, on every record."""
    out = []
    enums = {
        "agentType": m.AGENT_TYPES,
        "status": m.STATUSES,
        "riskClassification": m.RISK_CLASSES,
        "humanOversightMode": m.OVERSIGHT_MODES,
    }
    for a in ctx.agents:
        for f in m.REQUIRED_AGENT_FIELDS:
            if a.get(f) in (None, "", []):
                out.append(Finding("CHK-AGT-00", ERROR, _code(a), f"Missing required field '{f}'"))
        for f, allowed in enums.items():
            if a.get(f) and a[f] not in allowed:
                out.append(Finding("CHK-AGT-00", ERROR, _code(a), f"'{f}' value '{a[f]}' not in {sorted(allowed)}"))
        for s in a.get("decisionScopes") or []:
            if s not in m.DECISION_SCOPES:
                out.append(Finding("CHK-AGT-00", ERROR, _code(a), f"Unknown decision scope '{s}'"))
        for p in a.get("permissions") or []:
            for f in m.REQUIRED_PERMISSION_FIELDS:
                if not p.get(f):
                    out.append(Finding("CHK-AGT-00", ERROR, _code(a),
                                       f"Permission on '{p.get('system', '?')}' missing '{f}'"))
            if p.get("accessLevel") and p["accessLevel"] not in m.PERMISSION_ACCESS:
                out.append(Finding("CHK-AGT-00", ERROR, _code(a), f"Invalid accessLevel '{p['accessLevel']}'"))
            if p.get("status") and p["status"] not in m.PERMISSION_STATUS:
                out.append(Finding("CHK-AGT-00", ERROR, _code(a), f"Invalid permission status '{p['status']}'"))
        for f in ("effectiveStartDate", "effectiveEndDate", "nextReviewDate", "workerRepsInformedDate"):
            try:
                d(a.get(f))
            except ValueError:
                out.append(Finding("CHK-AGT-00", ERROR, _code(a), f"'{f}' is not an ISO date: {a.get(f)!r}"))
    return out


def chk_01_owner(ctx: Context) -> list[Finding]:
    """Every active agent has an active human accountable owner."""
    return [Finding("CHK-AGT-01", ERROR, _code(a),
                    f"Accountable owner '{a.get('ownerUserId')}' is missing or not an active employee")
            for a in ctx.active_agents if not _employee_active(ctx, a.get("ownerUserId"))]


def chk_02_kill_switch(ctx: Context) -> list[Finding]:
    """Every active agent has an active human who can stop it."""
    return [Finding("CHK-AGT-02", ERROR, _code(a),
                    f"Kill-switch owner '{a.get('killSwitchOwnerUserId')}' is missing or not an active employee")
            for a in ctx.active_agents if not _employee_active(ctx, a.get("killSwitchOwnerUserId"))]


def chk_03_classification(ctx: Context) -> list[Finding]:
    """Employment decision scopes force HIGH_RISK_ANNEX_III classification."""
    out = []
    for a in ctx.active_agents:
        hits = sorted(set(a.get("decisionScopes") or []) & m.EMPLOYMENT_SCOPES)
        if hits and a.get("riskClassification") not in ("HIGH_RISK_ANNEX_III", "PROHIBITED"):
            out.append(Finding("CHK-AGT-03", ERROR, _code(a),
                               f"Scopes {hits} fall under Annex III point 4 but classification is "
                               f"'{a.get('riskClassification')}'"))
    return out


def chk_04_oversight(ctx: Context) -> list[Finding]:
    """High-risk agents need a human oversight mode (Art. 14, Art. 26(2))."""
    return [Finding("CHK-AGT-04", ERROR, _code(a), "High-risk agent has humanOversightMode NONE")
            for a in ctx.active_agents
            if is_high_risk(a) and a.get("humanOversightMode") in (None, "NONE")]


def chk_05_log_retention(ctx: Context) -> list[Finding]:
    """High-risk agents keep logs for at least six months (Art. 26(6))."""
    out = []
    for a in ctx.active_agents:
        if not is_high_risk(a):
            continue
        days = a.get("logRetentionDays")
        if not isinstance(days, int) or days < m.MIN_LOG_RETENTION_DAYS:
            out.append(Finding("CHK-AGT-05", ERROR, _code(a),
                               f"logRetentionDays is {days!r}; minimum is {m.MIN_LOG_RETENTION_DAYS}"))
    return out


def chk_06_worker_information(ctx: Context) -> list[Finding]:
    """Workers' representatives informed before a high-risk agent goes live (Art. 26(7))."""
    out = []
    for a in ctx.active_agents:
        if not is_high_risk(a):
            continue
        informed = d(a.get("workerRepsInformedDate"))
        start = d(a.get("effectiveStartDate"))
        if informed is None:
            out.append(Finding("CHK-AGT-06", ERROR, _code(a), "No workerRepsInformedDate recorded"))
        elif start and informed > start:
            out.append(Finding("CHK-AGT-06", ERROR, _code(a),
                               f"Workers informed {informed} after go-live {start}"))
    return out


def chk_07_permission_expiry(ctx: Context) -> list[Finding]:
    """Active permissions carry an expiry no more than 365 days after grant."""
    out = []
    for a in ctx.active_agents:
        for p in a.get("permissions") or []:
            if p.get("status") != "ACTIVE":
                continue
            granted, expiry = d(p.get("grantedDate")), d(p.get("expiryDate"))
            if expiry is None:
                out.append(Finding("CHK-AGT-07", ERROR, _code(a),
                                   f"Permission {p.get('system')}:{p.get('scope')} has no expiryDate"))
            elif granted and (expiry - granted).days > m.MAX_PERMISSION_DAYS:
                out.append(Finding("CHK-AGT-07", ERROR, _code(a),
                                   f"Permission {p.get('system')}:{p.get('scope')} lasts "
                                   f"{(expiry - granted).days} days (max {m.MAX_PERMISSION_DAYS})"))
    return out


def chk_08_expired_permission(ctx: Context) -> list[Finding]:
    """No permission still ACTIVE past its expiry date."""
    out = []
    for a in ctx.agents:  # all records: a stale grant on a suspended agent is still a risk
        if not is_current(a, ctx.as_of):
            continue
        for p in a.get("permissions") or []:
            expiry = d(p.get("expiryDate"))
            if p.get("status") == "ACTIVE" and expiry and expiry < ctx.as_of:
                out.append(Finding("CHK-AGT-08", ERROR, _code(a),
                                   f"Permission {p.get('system')}:{p.get('scope')} expired {expiry} but is ACTIVE"))
    return out


def chk_09_position(ctx: Context) -> list[Finding]:
    """Assigned position exists, is active and is staffed AGENT or HYBRID."""
    out = []
    for a in ctx.active_agents:
        code = a.get("positionCode")
        if not code:
            continue
        pos = ctx.positions.get(code)
        if pos is None:
            out.append(Finding("CHK-AGT-09", ERROR, _code(a), f"Position '{code}' not found"))
        elif pos.get("status") != "ACTIVE":
            out.append(Finding("CHK-AGT-09", ERROR, _code(a), f"Position '{code}' is not active"))
        elif pos.get("staffingType") not in ("AGENT", "HYBRID"):
            out.append(Finding("CHK-AGT-09", ERROR, _code(a),
                               f"Position '{code}' staffingType is '{pos.get('staffingType')}', not AGENT/HYBRID"))
    return out


def chk_10_cost_center(ctx: Context) -> list[Finding]:
    """Cost centre exists in foundation data, so agent cost is chargeable."""
    return [Finding("CHK-AGT-10", ERROR, _code(a), f"Cost centre '{a.get('costCenter')}' not in foundation data")
            for a in ctx.active_agents if a.get("costCenter") not in ctx.cost_centers]


def chk_11_review_due(ctx: Context) -> list[Finding]:
    """Periodic review not overdue."""
    out = []
    for a in ctx.active_agents:
        nrd = d(a.get("nextReviewDate"))
        if nrd and nrd < ctx.as_of:
            out.append(Finding("CHK-AGT-11", WARNING, _code(a),
                               f"Review overdue by {(ctx.as_of - nrd).days} days"))
    return out


def chk_12_effective_overlap(ctx: Context) -> list[Finding]:
    """No overlapping effective-dated records for one externalCode."""
    out = []
    by_code: dict[str, list[dict]] = defaultdict(list)
    for a in ctx.agents:
        if a.get("externalCode") and a.get("effectiveStartDate"):
            by_code[a["externalCode"]].append(a)
    for code, recs in by_code.items():
        recs = sorted(recs, key=lambda r: r["effectiveStartDate"])
        for prev, nxt in zip(recs, recs[1:]):
            prev_end = d(prev.get("effectiveEndDate")) or date.max
            if d(nxt["effectiveStartDate"]) <= prev_end:
                out.append(Finding("CHK-AGT-12", ERROR, code,
                                   f"Record from {nxt['effectiveStartDate']} overlaps record from "
                                   f"{prev['effectiveStartDate']}"))
    return out


def chk_13_owner_span(ctx: Context) -> list[Finding]:
    """One human cannot meaningfully oversee an unlimited number of agents."""
    counts = Counter(a.get("ownerUserId") for a in ctx.active_agents if a.get("ownerUserId"))
    return [Finding("CHK-AGT-13", WARNING, owner,
                    f"Owner accountable for {n} active agents (threshold {ctx.max_agents_per_owner})")
            for owner, n in sorted(counts.items()) if n > ctx.max_agents_per_owner]


def chk_14_prohibited(ctx: Context) -> list[Finding]:
    """Workplace emotion recognition is prohibited (Art. 5(1)(f))."""
    out = []
    for a in ctx.active_agents:
        hits = sorted(set(a.get("decisionScopes") or []) & m.PROHIBITED_SCOPES)
        if hits or a.get("riskClassification") == "PROHIBITED":
            out.append(Finding("CHK-AGT-14", ERROR, _code(a),
                               f"Prohibited practice active {hits or ['riskClassification=PROHIBITED']}; "
                               "suspend unless a documented medical or safety exception applies"))
    return out


CHECKS: list[tuple[str, Callable[[Context], list[Finding]]]] = [
    ("CHK-AGT-00", chk_00_structure),
    ("CHK-AGT-01", chk_01_owner),
    ("CHK-AGT-02", chk_02_kill_switch),
    ("CHK-AGT-03", chk_03_classification),
    ("CHK-AGT-04", chk_04_oversight),
    ("CHK-AGT-05", chk_05_log_retention),
    ("CHK-AGT-06", chk_06_worker_information),
    ("CHK-AGT-07", chk_07_permission_expiry),
    ("CHK-AGT-08", chk_08_expired_permission),
    ("CHK-AGT-09", chk_09_position),
    ("CHK-AGT-10", chk_10_cost_center),
    ("CHK-AGT-11", chk_11_review_due),
    ("CHK-AGT-12", chk_12_effective_overlap),
    ("CHK-AGT-13", chk_13_owner_span),
    ("CHK-AGT-14", chk_14_prohibited),
]
