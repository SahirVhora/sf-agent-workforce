"""Reference data model for AI agents held as workers in an HRIS.

Enumerations here are the single source of truth. The JSON Schema in
schema/digital_worker.schema.json and the docs are tested against them.
"""

AGENT_TYPES = {"TASK_AGENT", "ORCHESTRATOR", "ASSISTANT", "RPA_BOT"}

STATUSES = {"ACTIVE", "SUSPENDED", "RETIRED"}

# Risk tier under the EU AI Act (Regulation (EU) 2024/1689 as amended by
# Regulation (EU) 2026/1744).
RISK_CLASSES = {
    "PROHIBITED",
    "HIGH_RISK_ANNEX_III",
    "LIMITED_TRANSPARENCY",
    "MINIMAL",
}

OVERSIGHT_MODES = {
    "HUMAN_IN_THE_LOOP",  # a human approves each output before it takes effect
    "HUMAN_ON_THE_LOOP",  # a human monitors and can intervene or stop
    "NONE",
}

# Decision scopes. Those in EMPLOYMENT_SCOPES map to Annex III point 4
# (employment, workers' management and access to self-employment).
EMPLOYMENT_SCOPES = {
    "recruitment_targeted_ads",  # Annex III 4(a)
    "recruitment_screening",  # Annex III 4(a)
    "candidate_evaluation",  # Annex III 4(a)
    "promotion_decision",  # Annex III 4(b)
    "termination_decision",  # Annex III 4(b)
    "terms_of_work_decision",  # Annex III 4(b)
    "task_allocation_by_traits",  # Annex III 4(b)
    "performance_monitoring",  # Annex III 4(b)
}

# Workplace emotion recognition is prohibited by Article 5(1)(f), save for
# medical or safety reasons. Applies since 2 February 2025.
PROHIBITED_SCOPES = {"workplace_emotion_recognition"}

OTHER_SCOPES = {
    "payroll_calculation_support",
    "data_validation",
    "document_drafting",
    "employee_query_answering",
    "data_migration",
    "reporting",
    "other",
}

DECISION_SCOPES = EMPLOYMENT_SCOPES | PROHIBITED_SCOPES | OTHER_SCOPES

PERMISSION_ACCESS = {"READ", "WRITE", "ADMIN"}
PERMISSION_STATUS = {"ACTIVE", "REVOKED"}

POSITION_STAFFING_TYPES = {"HUMAN", "AGENT", "HYBRID"}

REQUIRED_AGENT_FIELDS = [
    "externalCode",
    "effectiveStartDate",
    "name",
    "agentType",
    "status",
    "ownerUserId",
    "killSwitchOwnerUserId",
    "legalEntity",
    "costCenter",
    "riskClassification",
    "humanOversightMode",
    "decisionScopes",
    "nextReviewDate",
]

REQUIRED_PERMISSION_FIELDS = [
    "system",
    "scope",
    "accessLevel",
    "grantedBy",
    "grantedDate",
    "status",
]

# Article 26(6): deployers keep automatically generated logs for at least
# six months. 183 days is used as the conservative day count.
MIN_LOG_RETENTION_DAYS = 183

MAX_PERMISSION_DAYS = 365
DEFAULT_MAX_AGENTS_PER_OWNER = 10
