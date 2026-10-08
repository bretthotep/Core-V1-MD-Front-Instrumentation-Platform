# Roadmap, MVP and issue-ready stages — proposed

This is an architecture/design baseline, not permission to implement the entire product.
Every stage follows ISSUE → DESIGN → BRANCH → IMPLEMENT → TEST → SECURITY REVIEW →
DOCUMENT → PR → REVIEW → MERGE. Use small PRs; preserve existing callers/contracts/tests.
No stage is complete solely because its design exists.

## MVP scope

One explicitly approved Excel/VBA workbook, one customer-local agent and one selected
SQL **or** API target demonstrate the full vertical slice:

Registration → safe workbook/VBA discovery → evidence-backed versioned Application Twin →
reviewed capability and mappings → deterministic approved local execution →
authenticated/authorised REST/OpenAPI → approved target → provenance/audit →
business/dependency health → schema/dependency drift → suspension and reviewed recovery.

Include enterprise identity integration, tenant isolation tests, source permission
preservation, secure outbound agent identity, approval/revocation and bounded execution.
Static discovery alone or mock execution cannot satisfy the completed MVP.

Exclude full PDF/folder/Word/Access/mainframe/desktop/SaaS coverage, OCR, composite claims
runtime, MCP/events/queue publication, unattended autonomous remediation, arbitrary
macro execution and a general-purpose workflow/data platform. Design their extension
ports now; implement only after the first slice proves the boundaries.

## Human approval register

| Decision | Proposed direction | Approver / blocking stage |
|---|---|---|
| Product/repository mismatch | Preserve Core V1-MD; choose new repository or isolated `fabric/` | Product sponsor + maintainers / S0 |
| Pilot and authoritative systems | One representative workbook/procedure and SQL or API target | Source owner + product sponsor / S0 |
| Technology/hosting | Evaluate .NET, React/TS, PostgreSQL; no stack selected | Architecture + operations / S0–S1 |
| Excel/VBA feasibility | Static first; approved supported execution only | Source owner + operations + security / S0, S3–S4 |
| Identity/source access | Enterprise OIDC, scoped requester mode with demonstrated source enforcement | Identity team + source owner / S2 |
| Approval separation | Independent reviewers for sensitive access/execution | Security + product owner / S2, S4 |
| Tenant isolation | Explicit storage/job/evidence/telemetry isolation design | Security + architecture / S1–S2 |
| Egress/residency/retention | Metadata by default; classified payload/evidence only by approval | Data owner + security/compliance / S2 |
| Revocation/offline policy | Short leases, no new expired work, safe in-flight handling | Security + operations / S2 |
| Audit/key/update ownership | Standard signing/key stores and protected append-only audit | Security + operations / S2, S8 |
| Health/performance limits | Measured thresholds, quotas, SLOs and RPO/RTO | Source owner + operations / S6, S8 |
| Extension priorities | Claims-folder and MCP after MVP, not automatic scope expansion | Product sponsor + architecture / S9 |

Record decision owner, rationale, approval date and accepted ADR revision when resolved.
All initial ADRs remain **Proposed**. A merged design does not implicitly select technologies
or authorise production effects.

## Issue-ready development stages

The entries below are ready-to-file GitHub Issue specifications with dependencies and
acceptance criteria, **not created GitHub Issues or assigned issue numbers**. Maintainers
must publish them and record actual issue links before work starts; issue creation is
not an implemented feature of this repository or a claim made by this design PR.

### S0 — Approve product placement and pilot feasibility

- **Type:** design/decision. **Depends on:** this design PR review.
- **Scope:** resolve product/repository mismatch; select workbook, capability and target;
  approve feasibility study, source access, execution environment, stack and hosting evaluation.
- **Deliverables:** recorded human decisions, updated proposed ADRs, supported Excel
  discovery/execution feasibility evidence and pilot risk register.
- **Acceptance:** source owner confirms authoritative systems; maintainers choose repository
  location; security/operations confirm supported execution path or explicitly block/revise
  the MVP; no runtime repurposing. Requirements: PROD-01, DISC-01, SEC-02.
- **Validation:** design/security review; verify no unsupported Office automation assumption.

### S1 — Establish protocol-independent domain and contracts

- **Type:** foundation. **Depends on:** S0.
- **Scope:** domain/use-case boundaries and selected persistence ports for Resource, Twin,
  Capability, Schema, Dependency, Connector, Policy, Identity, Observation and Evidence.
- **Deliverables:** immutable versioned contracts, tenant/reference invariants, unknown/
  partial states, approval bindings and fake infrastructure.
- **Acceptance:** no transport/storage SDK in domain; no cross-tenant edges; twin/evidence
  versioning and lifecycle tests pass. Requirements: DOM-01, TWIN-01, EVID-01, SEC-04, QUAL-01.
- **Validation:** domain and migration/compatibility tests; architecture/security review.

### S2 — Establish enterprise identity and outbound agent trust

- **Type:** security foundation. **Depends on:** S0, S1.
- **Scope:** OIDC identity, RBAC/resource attributes, enrollment/mTLS, local roots/policy,
  source identity modes, secret references, leases/revocation and protected audit.
- **Deliverables:** tenant/agent-bound typed work envelope and policy/audit ports; approved
  source entitlement mode and signing/rotation/offline decisions.
- **Acceptance:** forged/cross-tenant/replayed/stale work, unsupported source ACL checks
  and full audit spools deny safely; compromised-agent revocation drill passes.
  Requirements: SEC-01–04, IAM-01, AUD-01, DISC-02.
- **Validation:** identity integration, local/source-denial and tenant-isolation tests;
  threat-model review. No production macro invocation yet.

### S3 — Implement safe Excel/VBA discovery and evidence

- **Type:** adapter. **Depends on:** S1, S2.
- **Scope:** bounded read-only workbook/VBA inspection, schemas, static procedures and
  dependencies; partial twins and evidence/confidence-bearing proposals.
- **Deliverables:** adapter contract/conformance fixtures, unsupported/protected-format
  diagnostics and pilot discovery result.
- **Acceptance:** hidden sheets/names/tables/formulas and accessible static VBA represented;
  macro startup, external links/refresh and unregistered dependency traversal never execute;
  ambiguity stays unknown. Requirements: DISC-01–02, TWIN-01, EVID-01, AI-01.
- **Validation:** corrupt/oversized/path-escape/parser/prompt-injection fixtures and
  source ACL tests; security review. Optional AI is isolated and unnecessary for safe discovery.

### S4 — Approve capabilities and compile deterministic connector plans

- **Type:** governed runtime. **Depends on:** S2, S3 and execution feasibility approval.
- **Scope:** capability/effect/schema lifecycle, reviewed mappings, typed operations,
  supported isolated pilot execution, idempotency and reconciliation.
- **Deliverables:** exact-version approval UI/use cases and allowlisted plan compiler/executor.
- **Acceptance:** no script/SQL/shell/arbitrary-macro input; changed/revoked plans denied;
  known pilot effects and independent approvals demonstrated; uncertain write outcome
  reconciles instead of blind replay. Requirements: CAP-01, CONN-01–02, AI-01.
- **Validation:** lifecycle, compiler negative cases, sandboxed real pilot invocation,
  replay/timeout/concurrency tests and security review.

### S5 — Publish secure REST/OpenAPI capability interface

- **Type:** interface. **Depends on:** S2, S4.
- **Scope:** versioned narrow business route, schemas, scopes/resource policy, quotas,
  safe errors, output validation, audit, revocation and authorised OpenAPI docs.
- **Deliverables:** approved pilot capability projection and contract tests.
- **Acceptance:** authenticated permitted calls succeed; anonymous/source-denied/cross-tenant
  requests and stale contracts fail; docs/health/results do not leak metadata;
  generic execution is impossible. Requirements: API-01, SEC-01, IAM-01, AUD-01.
- **Validation:** positive/negative API and source-permission tests; security review.

### S6 — Implement business health and workbook contract drift

- **Type:** observability. **Depends on:** S3–S5.
- **Scope:** bounded observations, hierarchical dependency impact, freshness baselines,
  schema/dependency diffs, consumer impact and reviewed suspension/recovery.
- **Deliverables:** explainable health records, drift event/impact graph and reapproval flow.
- **Acceptance:** stale Rates.xlsx example has evidence/cause/impact; missing telemetry
  is unknown; renamed field suspends unsafe plans and approved revision restores service;
  unknown consumers remain explicit. Requirements: OBS-01, DRIFT-01.
- **Validation:** fake-clock/rule tests, source edit during execution, dependency failure
  and drift end-to-end tests; security review of metadata/evidence visibility.

### S7 — Deliver selected target and complete the estate journey

- **Type:** MVP integration/UX. **Depends on:** S4–S6.
- **Scope:** one approved SQL or API target plus accessible estate/twin/connector views and
  register → review → connect → approve → deploy → monitor → query journey.
- **Deliverables:** deterministic target binding, reviewed mappings, provenance and real pilot
  end-to-end evidence; no unrelated frontend application rewrites.
- **Acceptance:** pilot execution reaches selected target with least privilege; mismatched
  mapping/source denial/target timeout/drift are understandable; graph is filtered and
  keyboard/list accessible. Requirements: PROD-01, CONN-01–02, UX-01, EVID-01.
- **Validation:** real selected target integration, SSRF or SQL-injection negative tests,
  uncertain-effect reconciliation and accessibility review.

### S8 — Harden and release the first vertical slice

- **Type:** release/operations. **Depends on:** S2–S7.
- **Scope:** signed packaging/upgrade, keys/certificates, audit integrity, retention,
  backup/restore, bounded queues, isolation, capacity limits and incident runbooks.
- **Deliverables:** repeatable deployment and operational evidence; requirement/test/PR
  traceability and accepted decisions.
- **Acceptance:** security review passes; measured/approved SLOs, revocation window,
  recovery objectives and data policies hold; restore/rollback cannot revive revoked
  authority; documentation matches real capability coverage. Requirements: SEC-03–04,
  AUD-01, QUAL-01 and all MVP gates.
- **Validation:** rotation/revocation/update/restore drills, failure/load tests and
  threat-model review. Existing Core V1-MD compatibility remains intact if colocated.

### S9 — Extend with claims-folder adapters and MCP parity

- **Type:** post-MVP extensions; split into adapter and interface issues when approved.
- **Depends on:** S8 plus separate source/identity/security feasibility approval.
- **Scope:** first prove an additional adapter can reuse boundaries; then PDF/folder/Word
  relationships/OCR as selected and approved composite Claim capability; MCP projection.
- **Deliverables:** adapter conformance and claims provenance/ambiguity handling; authorised
  tool/resource enumeration using the same application policy pipeline.
- **Acceptance:** Excel row/PDF joins are evidence-backed and reviewed; uncertain/conflicting
  matches do not silently resolve; REST/MCP policy and source-denial parity holds.
  Requirements: EXT-01, IAM-01, EVID-01, AI-01.
- **Validation:** denied-file, OCR-confidence, prompt-injection and composite provenance
  tests; MCP discovery/execution parity and security review.

## PR boundaries and completion

Break each issue into reviewed subfeatures if needed; do not bundle all stages into one
implementation PR. Each PR documents dependencies/callers/contracts and security effects,
tests failure paths, scans secrets, updates requirements/diagrams/ADRs and seeks review.
No deletions or rewrites of existing instrumentation modules to simplify the new product.
