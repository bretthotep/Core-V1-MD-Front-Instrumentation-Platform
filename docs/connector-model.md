# Connector model — proposed

A Connector joins approved resources/capabilities through a versioned deterministic
plan. It is neither a replacement business workflow nor unrestricted code generation.

## Plan contents

Tenant/connector/version IDs; source and target bindings; exact capability/twin/schema
revisions; allowlisted typed steps; mapping and validation rules; permitted transformations;
source and target identity modes; policy and secret references; dependency fingerprints;
effects; egress/classification; timeout/retry/rate limits; idempotency/reconciliation;
field provenance requirements; reviewer approvals and deployment state.

Mappings carry source/target paths, evidence, transformation, confidence/method and
review decision. Use bounded declarative transformations (rename, explicit type/unit/date
conversion, approved lookup); no shell, general script, reflection or expression `eval`.
Candidate similarity scores are not proof of semantic compatibility.

## Lifecycle

Draft → proposed → validated → approved → deploying → active.
Failures during deployment remain failed/non-active; never publish before the agent
acknowledges the accepted plan digest. Active → suspended/retired. A new revision
requires validation and approval; rollback uses an explicitly still-authorised version.

Dragging Application A to B starts feasibility analysis, not deployment. Inspect schemas,
source/target permissions, auth, transport, validation, dependencies and effects. Reviewers
approve mappings and security together; uncertain mappings stay unresolved.

## Runtime and resilience

The agent validates signed/integrity-protected configuration and short-lived job
authorisation, then rechecks policy, source ACLs, resource fingerprint and target bounds.
Pin plan/schema versions through the operation to avoid validation/execution races.
Detect source changes during reads; retry only a safe bounded read or return inconsistency.

Carry correlation/job IDs and an idempotency key scoped to tenant, capability version,
requester and validated input. Durable deduplication handles redelivery; reads may retry
with bounded backoff/jitter. Writes require target-supported idempotency or a durable
reconciliation procedure; no exactly-once claim across workbook and remote SQL/API.
Timeout/lost acknowledgement can mean “outcome unknown,” not “safe to retry.”

Use concurrency limits and isolation for stateful Excel workbooks. Source and target
timeouts, cancellation, circuit breakers and queue bounds are configured per operation.
Do not treat a compensating action as a guaranteed transactional rollback.

SQL targets use a scoped account and preapproved parameterised statements/procedures.
API targets use an allowlisted origin/route and scoped credential; constrain redirects.
Audit outcomes without raw payloads; retain authorised field lineage and health measures.

See [lifecycle diagram](diagrams/connector-lifecycle.mmd) and
[deployment gates](deployment.md).
