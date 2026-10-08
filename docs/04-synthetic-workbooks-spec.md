# Synthetic Operational Workbooks Specification

To reflect Acentra Health's real-world enterprise domain (Medicaid MMIS, CMS guidelines, Atrezzo care management), the system relies on three realistic operational workbooks:

---

## 1. Prior Authorization & Intake Routing Matrix (`matrix_prior_auth.csv`)

Defines state-level Medicaid and commercial prior authorization thresholds and routing rules.

| Row ID | State | Service Category | CPT / HCPCS Code | Dollar Threshold | Prior Auth Required? | Required Fields Schema ID | Clearance Required | Escalation Trigger |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PA-MAT-001` | VA | Outpatient Surgery | `47562` (Laparoscopic Cholecystectomy) | $5,000 | Yes | `SCHEMA-PA-SURG-01` | `FRONT_DESK` | Amount > $15,000 OR Out-of-State Provider |
| `PA-MAT-002` | VA | Durable Medical Equipment | `E0601` (CPAP Device) | $1,000 | Yes | `SCHEMA-PA-DME-01` | `FRONT_DESK` | Sleep study > 12 months old |
| `PA-MAT-003` | MD | Diagnostic Imaging | `70553` (MRI Brain w/ Contrast) | $0 | Yes | `SCHEMA-PA-RAD-01` | `FRONT_DESK` | Non-participating imaging center |
| `PA-MAT-004` | PA | Behavioral Health | `90837` (Psychotherapy 60m) | $0 | No (Up to 12 sessions/yr) | `SCHEMA-PA-BH-01` | `CARE_MANAGER` | Sessions > 12 requested |
| `PA-MAT-005` | ALL | Experimental / High-Cost Biotech | `J9999` (Unclassified Biologic) | $25,000 | Yes | `SCHEMA-PA-BIO-01` | `SUPERVISOR` | Always escalates to Medical Director |

---

## 2. Claims Adjudication & Modifier Rules (`matrix_claims_rules.csv`)

Adjudication matrix for claims processors triaging denials and filing limits.

| Rule ID | Claim Type | Denial Code | Description | Root Cause Checklist | Allowed Action | Authority Level |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CLM-ADJ-101` | Professional (837P) | `CO-16` | Missing/Incomplete Information | Check Box 24D (Modifier) & Box 33 (Billing NPI) | Prompt for missing modifier; Re-adjudicate | `CLAIMS_PROCESSOR` |
| `CLM-ADJ-102` | Institutional (837I) | `CO-29` | Timely Filing Limit Expired | Verify date of service vs state 95-day / 365-day rule | Deny claim OR check extenuating proof | `CLAIMS_PROCESSOR` |
| `CLM-ADJ-103` | Professional (837P) | `CO-97` | Service Bundled (CCI Edit) | Verify if Modifier -59 or -X{EPSU} is supported by records | Request operative notes; Supervisor sign-off | `SUPERVISOR` |
| `CLM-ADJ-104` | All | `PR-204` | Service not covered under plan | Verify member eligibility on Date of Service | Route to Patient Financial Assistance | `FRONT_DESK` |

---

## 3. Stepwise Field Schemas (`schemas_field_definitions.json`)

Machine-readable schemas that the Symbolic Engine uses to enforce deterministic form filling:

```json
{
  "SCHEMA-PA-SURG-01": {
    "workflow_name": "Surgical Prior Authorization Request",
    "governing_sop": "SOP-VA-MED-04",
    "required_fields": [
      {"name": "member_id", "type": "string", "regex": "^[A-Z0-9]{9,12}$", "description": "Medicaid Beneficiary ID"},
      {"name": "patient_dob", "type": "date", "description": "Patient Date of Birth (YYYY-MM-DD)"},
      {"name": "cpt_code", "type": "string", "regex": "^[0-9]{5}$", "description": "5-digit CPT Procedure Code"},
      {"name": "primary_icd10", "type": "string", "regex": "^[A-Z][0-9]{2}(\\.[0-9]{1,4})?$", "description": "Primary ICD-10 Diagnosis Code"},
      {"name": "servicing_npi", "type": "string", "regex": "^[0-9]{10}$", "description": "10-digit National Provider Identifier"},
      {"name": "facility_id", "type": "string", "description": "Servicing Hospital/Facility ID"},
      {"name": "estimated_cost", "type": "number", "description": "Estimated cost in USD"}
    ]
  }
}
```

---

## 4. Standard Operating Procedures (SOPs) Knowledge Base

Unstructured operational guidelines structured into identifiable chunks:
- `SOP-OPS-001`: General Intake & Verification Protocol (Section 1.1: Verification of Identity, Section 1.2: Medicaid Eligibility Check).
- `SOP-VA-MED-04`: Virginia Medicaid Surgical Prior-Authorization Guidelines (Section 3.1: Pre-requisite Conservative Therapy, Section 3.2: Urgent/Emergent Fast-track).
- `SOP-CLM-012`: Claims Timely Filing Appeals & Dispute Resolution (Section 2.1: Proof of Timely Filing Standards, Section 4.3: Supervisor Override Thresholds).
- `SOP-CLIN-GUARD-09`: Clinical Boundary Enforcement & Medical Director Escalation Matrix.
