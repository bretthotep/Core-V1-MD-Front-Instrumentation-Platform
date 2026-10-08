# Application Twin — proposed model

Every registered Resource receives a tenant-scoped Application Twin immediately.
Empty/failed/partial discovery is a valid twin, not fabricated knowledge. A resource
may be a file, folder, application, API or database; child twins and typed relationships
represent composites without copying the authoritative source.

## Versioned envelope

| Area | Suggested fields / semantics |
|---|---|
| Identity | Twin/resource/tenant IDs, type, display name, owner, source-system identity |
| Location | Agent-bound locator reference and configured root; sensitive paths access-controlled |
| Version | Twin schema version, immutable revision, source fingerprint, discovery run ID |
| Structure | Files, sheets (including hidden), tables, fields, named ranges, formulas, procedures, API endpoints |
| Semantics | Capabilities, schemas, inputs/outputs, dependency/relationship edges |
| Access | Source permission observations, execution modes, policy references and classification; no secrets |
| Configuration | Adapter/version, approved bounds and secret references |
| Operations | Linked timestamped health/performance/failure/change observations and normal-behaviour baselines |
| Knowledge | Evidence-backed assertions, conflicts, unknowns and discovery coverage |
| Lifecycle | Registered/discovering/partial/ready/failed/unsupported/retired; this is separate from capability approval |

High-volume telemetry is linked rather than rewriting the twin on every heartbeat.
A twin revision is an immutable metadata snapshot; “latest” is an authorised pointer.
Stable IDs must survive display-name changes. Deletion retires references according
to retention policy; history cannot keep an executable entitlement alive.

## Assertions and confidence

Each inferred assertion contains a stable ID, subject/property/value, one or more
protected evidence references, source locator/version, observed timestamp, discovery
method and tool/model version, confidence, review status, reviewer/decision timestamp
and reason. Status is proposed/approved/rejected/superseded; source observations are
distinguished from semantic inference. Approval binds the specific assertion revision.

Confidence is in a documented range (proposed 0–1) with method/calibration notes.
Absent confidence is unknown, not zero or certainty; parser observations need not
invent probabilities. A high score is not proof, permission, or automatic approval.
Conflicting observations remain visible; explanations cannot erase contradictory evidence.

| Example assertion | Value |
|---|---|
| Capability candidate | CalculatePremium |
| Evidence | VBA procedure location plus static read/write references |
| Reads / dependency | Policy.State, Policy.Limit, Policy.ClassCode; Rates.xlsx |
| Writes | RatingOutput |
| Method | VBA static analysis; dynamic/indirect references may be unresolved |
| Confidence | Illustrative 0.94, not a measured result |
| Review | Proposed; no execution authority |

Static analysis cannot guarantee side effects or completeness. Runtime behaviour may
be inspected only by separately approved, isolated execution. Protected/obfuscated VBA,
encrypted workbooks and unsupported formats yield explicit gaps.

## Invariants and evolution

No cross-tenant references; evidence permissions are at least as restrictive as the
source. Assertions referencing inaccessible evidence must not leak its contents.
Capabilities depend on explicit twin/schema revisions. Material source drift makes
affected approvals stale; human review creates a new revision rather than editing history.
Twin schema migration/version negotiation must retain older reader compatibility.

See [twin diagram](diagrams/application-twin.mmd), [provenance](provenance.md) and
[contract drift](contract-drift.md).
