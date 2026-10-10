"""Generate the JSON Schema for a register export from model.py.

    python -m agent_workforce.schema > schema/agent_register.schema.json

tests/test_schema.py fails if the committed schema drifts from the model.
"""

import json

from . import model as m

DATE = {"type": "string", "format": "date"}


def build_schema() -> dict:
    permission = {
        "type": "object",
        "required": m.REQUIRED_PERMISSION_FIELDS,
        "properties": {
            "system": {"type": "string"},
            "scope": {"type": "string"},
            "accessLevel": {"enum": sorted(m.PERMISSION_ACCESS)},
            "grantedBy": {"type": "string"},
            "grantedDate": DATE,
            "expiryDate": DATE,
            "status": {"enum": sorted(m.PERMISSION_STATUS)},
        },
    }
    agent = {
        "type": "object",
        "required": m.REQUIRED_AGENT_FIELDS,
        "properties": {
            "externalCode": {"type": "string"},
            "effectiveStartDate": DATE,
            "effectiveEndDate": DATE,
            "name": {"type": "string"},
            "agentType": {"enum": sorted(m.AGENT_TYPES)},
            "vendor": {"type": "string"},
            "modelVersion": {"type": "string"},
            "status": {"enum": sorted(m.STATUSES)},
            "ownerUserId": {"type": "string"},
            "killSwitchOwnerUserId": {"type": "string"},
            "legalEntity": {"type": "string"},
            "costCenter": {"type": "string"},
            "positionCode": {"type": "string"},
            "riskClassification": {"enum": sorted(m.RISK_CLASSES)},
            "annexIIIPoint": {"type": "string"},
            "humanOversightMode": {"enum": sorted(m.OVERSIGHT_MODES)},
            "decisionScopes": {"type": "array", "items": {"enum": sorted(m.DECISION_SCOPES)}},
            "fteEquivalent": {"type": "number", "minimum": 0},
            "monthlyRunCost": {"type": "number", "minimum": 0},
            "logRetentionDays": {"type": "integer", "minimum": 0},
            "workerRepsInformedDate": DATE,
            "oversightEvidenceRef": {"type": "string"},
            "nextReviewDate": DATE,
            "permissions": {"type": "array", "items": permission},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://sahirvhora.github.io/sf-agent-workforce/schema/agent_register.schema.json",
        "title": "Agent register export",
        "type": "object",
        "required": ["agents", "employees", "positions", "costCenters"],
        "properties": {
            "agents": {"type": "array", "items": agent},
            "employees": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["userId", "status"],
                    "properties": {
                        "userId": {"type": "string"},
                        "name": {"type": "string"},
                        "status": {"type": "string"},
                    },
                },
            },
            "positions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["code", "status", "staffingType"],
                    "properties": {
                        "code": {"type": "string"},
                        "title": {"type": "string"},
                        "status": {"type": "string"},
                        "staffingType": {"enum": sorted(m.POSITION_STAFFING_TYPES)},
                    },
                },
            },
            "costCenters": {"type": "array", "items": {"type": "string"}},
        },
    }


if __name__ == "__main__":
    print(json.dumps(build_schema(), indent=2))
