# CHK-AGT check catalogue

Active means status ACTIVE and the effective window covers the as-of date. "High-risk" means declared HIGH_RISK_ANNEX_III **or** carrying an employment decision scope, so a misclassification cannot hide the downstream gaps.

| ID | Severity | Rule | Basis |
|---|---|---|---|
| CHK-AGT-00 | ERROR | Required fields present, enumerations and dates valid | Data quality |
| CHK-AGT-01 | ERROR | Accountable owner is an active employee | Art. 26(2) competent oversight; governance |
| CHK-AGT-02 | ERROR | Kill-switch owner is an active employee | Art. 14(4)(e) ability to stop the system |
| CHK-AGT-03 | ERROR | Employment scopes force HIGH_RISK_ANNEX_III | Annex III point 4; Art. 6(3) |
| CHK-AGT-04 | ERROR | High-risk agent has an oversight mode other than NONE | Art. 14, Art. 26(2) |
| CHK-AGT-05 | ERROR | High-risk agent keeps logs at least 183 days | Art. 26(6) six months minimum |
| CHK-AGT-06 | ERROR | Workers' representatives informed on or before go-live | Art. 26(7) |
| CHK-AGT-07 | ERROR | Active permissions expire within 365 days of grant | Least privilege; house rule |
| CHK-AGT-08 | ERROR | No permission ACTIVE past expiry, including on suspended agents | Least privilege |
| CHK-AGT-09 | ERROR | Assigned position exists, is active and is AGENT or HYBRID | Position control |
| CHK-AGT-10 | ERROR | Cost centre exists in foundation data | Cost allocation |
| CHK-AGT-11 | WARNING | Periodic review not overdue | Governance |
| CHK-AGT-12 | ERROR | No overlapping effective-dated records per agent | Data integrity |
| CHK-AGT-13 | WARNING | Owner accountable for more than N active agents (default 10) | Meaningful oversight capacity |
| CHK-AGT-14 | ERROR | No active prohibited practice (workplace emotion recognition) | Art. 5(1)(f) |

Thresholds (183 days, 365 days, 10 agents) live in `agent_workforce/model.py`. 365 days and 10 agents are house defaults, not legal requirements; tune them to your policy.

These checks test the register, not the legal position. A passing register is evidence of control, not a conformity assessment.
