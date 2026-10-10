# Agents in the HRIS: reference data model

## The problem

AI agents now do work that used to sit in job descriptions: validating payroll, screening applications, answering employee queries. They consume budget, act with delegated system access and, in HR use cases, can make or shape decisions about people. Most organisations track them nowhere, or in an IT asset list that HR, Finance and Compliance never see.

This model puts agents where the work is planned and paid for: the HRIS. It is written for SAP SuccessFactors Employee Central but the entities are platform neutral.

## Design decision: agents are not employees

**Do not create agents as Users with EmpJob records.** That route breaks four things:

1. **Headcount and statutory reporting.** Agents inflate FTE, gender pay gap denominators and workforce analytics.
2. **Payroll replication.** EC Payroll, ADP Global View and other downstream replications pick up employment records. An agent with a job record is a payroll defect waiting to happen.
3. **Licensing.** Many HCM licences are per employee record.
4. **Semantics.** Employment law concepts (contract, notice, leave) do not apply and will be filled with junk.

Instead, model the agent as its own effective-dated object that **references** the same foundation data, positions and people as employees do. Agents then appear in org, cost and capacity views without polluting employment data.

## Entities

```
Position (existing) ──< cust_DigitalWorker >── Employee (owner, kill-switch owner)
   + cust_staffingType           │
                                 ├──< cust_AgentPermission (composite child)
                                 └── FOCostCenter / FOCompany (foundation data)
```

### cust_DigitalWorker (MDF generic object, effective dated)

| Field | Type | Req | Purpose |
|---|---|---|---|
| externalCode | String | Y | Stable agent ID, for example AGT-PAY-01 |
| effectiveStartDate / effectiveEndDate | Date | Y / N | History of configuration, scope and ownership changes |
| name | String | Y | Business name |
| agentType | Picklist | Y | TASK_AGENT, ORCHESTRATOR, ASSISTANT, RPA_BOT |
| vendor, modelVersion | String | N | What is actually running; a model change is a new effective-dated record |
| status | Picklist | Y | ACTIVE, SUSPENDED, RETIRED |
| ownerUserId | User | Y | The accountable human. One name, not a team |
| killSwitchOwnerUserId | User | Y | Who can stop it, if different from the owner |
| legalEntity | Foundation ref | Y | Which entity deploys it (AI Act duties attach to the deployer) |
| costCenter | Foundation ref | Y | Where its run cost lands |
| positionCode | Position ref | N | The position it fills or shares |
| riskClassification | Picklist | Y | PROHIBITED, HIGH_RISK_ANNEX_III, LIMITED_TRANSPARENCY, MINIMAL |
| annexIIIPoint | String | N | For example 4(a) or 4(b) |
| humanOversightMode | Picklist | Y | HUMAN_IN_THE_LOOP, HUMAN_ON_THE_LOOP, NONE |
| decisionScopes | Multi-select picklist | Y | What it is allowed to decide or influence (see below) |
| fteEquivalent | Decimal | N | Capacity it replaces or adds, for workforce planning |
| monthlyRunCost | Decimal | N | For cost-per-outcome comparison with human capacity |
| logRetentionDays | Integer | High-risk | Article 26(6) minimum six months |
| workerRepsInformedDate | Date | High-risk | Article 26(7) |
| oversightEvidenceRef | String | N | Link to documented oversight procedure |
| nextReviewDate | Date | Y | Periodic re-certification |

### cust_AgentPermission (composite child)

| Field | Type | Req | Purpose |
|---|---|---|---|
| system | String | Y | SF_EC, SF_RCM, ECP, ServiceNow and so on |
| scope | String | Y | Entities, APIs or RBP role granted |
| accessLevel | Picklist | Y | READ, WRITE, ADMIN |
| grantedBy | User | Y | Who approved |
| grantedDate / expiryDate | Date | Y / Y | Grants expire; maximum 365 days by default |
| status | Picklist | Y | ACTIVE, REVOKED |

### Position extension

Add `cust_staffingType` (HUMAN, AGENT, HYBRID) to Position. Position control then answers "how much of this role is done by agents" and stops an agent being assigned to a position budgeted for a person.

## Decision scopes and the EU AI Act

Scopes in this table make an agent high-risk under Annex III point 4 regardless of what the record says. CHK-AGT-03 enforces it.

| Scope | Annex III |
|---|---|
| recruitment_targeted_ads, recruitment_screening, candidate_evaluation | 4(a) |
| promotion_decision, termination_decision, terms_of_work_decision, task_allocation_by_traits, performance_monitoring | 4(b) |
| workplace_emotion_recognition | Prohibited, Article 5(1)(f), unless for medical or safety reasons |

Article 6(3) lets a provider argue an Annex III system is not high-risk in narrow cases (for example a purely preparatory task), but never where the system profiles people. Record that argument in `oversightEvidenceRef` and classify accordingly; the validator will still flag the scope so a human signs it off.

**Dates (Regulation (EU) 2026/1744, in force 27 July 2026):** prohibitions have applied since 2 February 2025 (AI literacy also started then; the Omnibus changed how that duty is framed, so check the consolidated text); Article 50 transparency since 2 August 2026; Annex III high-risk obligations from 2 December 2027.

## Building it in SuccessFactors

1. **Admin Center > Configure Object Definitions > Create New Object Definition.** Create `cust_AgentPermission` first (Effective Dating: None) then `cust_DigitalWorker` (Effective Dating: Basic) with the fields above and a Composite association to `cust_AgentPermission`. Set API Visibility to Editable so the object is exposed through OData v2.
2. Create the picklists listed in `templates/field_mapping.csv` in Picklist Center.
3. Add `cust_staffingType` to the Position object definition.
4. Create an RBP permission category for the object. Grant edit to an HR Tech admin role and read to owners, so owners can see what they are accountable for.
5. Build a Manage Data or custom page view, and an Integration Center or OData pull feeding this validator.
6. Download the import template from **Import and Export Data** after the object exists. Do not hand-build the CSV header; the system template is authoritative for your instance.

## Validation

`python -m agent_workforce.validate export.json --html report.html` runs the CHK-AGT catalogue. See [CHECKS.md](CHECKS.md).
