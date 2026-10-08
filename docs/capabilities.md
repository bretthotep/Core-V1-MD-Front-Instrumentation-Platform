# Capabilities — proposed

A Capability is a narrow, business-meaningful operation discovered from a resource and
explicitly approved. It is not a raw macro runner, SQL console, shell command or AI tool
that can select arbitrary files.

## Contract

Include tenant/stable ID/version, name/description, input/output schema revisions,
source/twin dependencies, effects (read/write/execute), preconditions, supported execution
mode, policy/scopes, evidence, confidence, approval record, timeout/rate/quota constraints,
idempotency semantics, provenance requirements, health and lifecycle.

Example names include CalculatePremium, GetClaim, ValidateClaim and GetApplicationHealth.
Their REST routes and MCP tool names are separate projections, not the identity of the
domain capability. Input schemas constrain identifiers and reject path fragments or code.

## Lifecycle and approval

Proposed → validated → approved → deployed → suspended → retired.
Rejection returns a proposal to review, not deployment. Validation checks schema,
dependency coverage, known effects, source permissions, runtime feasibility and tests.
Approvers review business correctness, identity mode, side effects, egress and rollback/
reconciliation. Approval binds exact capability, source contract and connector-plan versions.

Deployment requires all approvals and local agent acceptance. Source drift, stale
authorisation, revoked approval or unknown effects suspends execution where contract
safety cannot be established. A revision creates a new proposal; approvals do not transfer.

## Runtime rules

Map operations to an allowlisted adapter action and fixed resource/macro/target binding.
Validate input before source access and output before publishing. A read operation must
not conceal file writes or outbound network side effects. Approval of a VBA procedure
requires its concrete execution safety gate, not merely a confidence threshold.

No `executeAnything`, arbitrary workbook/procedure name, dynamic SQL or user-supplied
script endpoint. Adding a typed operation is a reviewed feature with negative tests,
not a runtime plugin upload by an AI consumer.

Failures distinguish denial, validation error, dependency unavailable, timeout,
schema mismatch and unknown side-effect outcome without exposing sensitive source detail.
Attach correlation and permitted provenance, with audit and operational health.
