# Requirements — proposed baseline

All requirements below are design requirements, not implemented features. Stages S0–S9
are [issue-ready milestones](roadmap.md#issue-ready-development-stages). Acceptance must
include negative cases and evidence; a UI preview is not implementation.

| ID | Requirement | Acceptance evidence | Stage |
|---|---|---|---|
| PROD-01 | Preserve authoritative source systems; do not become CRM/ERP/warehouse | Pilot reads/invokes source; no replicated business system of record | S0, S7 |
| DOM-01 | Protocol-independent Resource, Twin, Capability, Schema, Dependency, Connector, Policy, Identity, Observation, Evidence | Domain tests do not depend on REST/MCP/storage SDKs | S1 |
| TWIN-01 | Every registration has a versioned twin, even if discovery fails | Unknown/partial/unsupported states shown with reasons | S1, S3 |
| EVID-01 | Every inferred assertion has evidence, confidence, source, timestamp, method and approval state | Missing provenance cannot be published as verified truth | S1, S3 |
| DISC-01 | Register a local workbook without a source API; inspect through adapter ports | Static workbook/VBA discovery fixture reports structures and explicit limits | S3 |
| DISC-02 | Discovery is bounded, read-only by default, and respects configured roots/ACLs | Traversal, reparse-point, denied-ACL and oversized-file tests fail safely | S2, S3 |
| CAP-01 | Proposed capabilities require version-specific approval before publication/execution | Pending, expired, revoked or changed plans cannot execute | S4, S5 |
| CONN-01 | Validate schemas, mapping, identity, source permissions and egress before deployment | Incompatible mapping or absent source permission prevents deployment | S4, S7 |
| SEC-01 | Authenticate and authorise every operation, including metadata and health reads | Anonymous, cross-tenant and unauthorised access denied | S2, S5 |
| SEC-02 | Agents connect outbound over authenticated encryption; no arbitrary commands | Wrong tenant/agent, expired/replayed/tampered work rejected locally | S2 |
| IAM-01 | Enterprise OIDC identity, RBAC plus resource/attribute policy, source ACL enforcement | REST/MCP parity and source-denial tests | S2, S5, S9 |
| SEC-03 | Protect secrets, encrypt stored data, rotate/revoke credentials and agent identity | Rotation and compromised-agent drill; logs contain no secrets | S2, S8 |
| SEC-04 | Tenant-isolate metadata, jobs, evidence, caches and telemetry | Cross-tenant object/job/subscription tests | S1, S2, S8 |
| AI-01 | AI only proposes; deterministic approved plans execute | Prompt injection cannot cause deployment, tool use or policy changes | S3, S4 |
| API-01 | Narrow versioned REST/OpenAPI contracts with schemas, scopes, quotas and revocation | Allowlisted operation validates requests/responses; no generic execution endpoint | S5 |
| CONN-02 | Timeouts, bounded retries, idempotency and reconciliation for uncertain writes | Lost acknowledgement never triggers blind repeat of a side effect | S4, S7 |
| OBS-01 | Explain hierarchical capability/dependency/resource health | Stale workbook dependency gives cause, evidence and impact; unknown is not healthy | S6 |
| DRIFT-01 | Detect schema/dependency changes and identify affected plans/interfaces/consumers | Field rename blocks incompatible plan until new approval; audit retained | S6 |
| AUD-01 | Security-controlled append-only audit of access, approvals, execution and changes | Independent access controls and integrity/retention evidence; audit failure blocks new execution | S2, S8 |
| UX-01 | Estate map and guided register/review/connect/approve/deploy journey | Accessible end-to-end pilot; evidence and denial reasons inspectable | S7 |
| EXT-01 | Add an adapter without redesigning domain or bypassing policy | Later PDF/folder adapter passes the same conformance tests | S9 |
| QUAL-01 | Clear boundaries, mockable infrastructure and automated failure/security tests | Domain, integration, contract, operational and compatibility gates | S1–S9 |

## Quality gates

For each stage: functional and failure-path tests; authentication/authorisation and least
privilege; input/output validation; no secrets or arbitrary execution; domain separation;
diagnosable telemetry; documentation/diagram/ADR alignment; peer and security review.

Latency, resource quotas, freshness thresholds, recovery objectives, retention periods,
maximum revocation delay and availability objectives are intentionally uncommitted until
pilot measurements and security approval. Approving a release requires setting and
testing these values, not leaving them implicit.

Traceability runs requirement → stage issue → design/ADR → implementation PR → test
evidence → approval. Existing Core V1-MD requirements and CI remain separate.
