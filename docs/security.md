# Security architecture — proposed

## Trust zones

Untrusted consumers, optional AI/document analysis, the tenant control plane, and the
customer-local agent/source environment are separate trust zones. Transport encryption
does not establish authority to use a resource. Every crossing has authentication,
tenant binding, explicit authorisation, validation and security audit.

Agents initiate outbound authenticated TLS connections; mTLS is the proposed workload
identity mechanism. No arbitrary inbound firewall access or cloud shell is required.
Use industry-standard TLS, PKI, OIDC/OAuth and managed secret stores; invent no
cryptography or authentication protocol.

## Enforcement

- Default deny and least privilege at registration, discovery, metadata/evidence reads,
  approval, deployment, execution, health subscriptions and export.
- REST and MCP share the same application/policy path. Never grant an AI/tool identity
  broader access than the initiating user.
- Tenant binding comes from verified identity and assigned agent, not a request body.
  Storage keys, jobs, evidence, caches, queues, subscriptions and logs are tenant-scoped.
- Agents accept only bounded, typed, versioned operations from approved plans. Verify
  tenant, agent assignment, integrity, expiry, nonce/job identity, policy freshness,
  schemas and source permissions locally. Reject generic commands and scripts.
- Configuration and upgrade packages use standard signing mechanisms; verify publisher,
  version and integrity before activation. Protect enrollment/recovery from reassignment.
- Local roots, network destinations and capabilities are allowlisted. Resolve paths
  safely at access time; deny escapes via symlinks/junctions/reparse points. Restrict UNC
  hosts/shares. Do not automatically follow workbook links or SQL connection strings.
- Discovery is read-only: no macros, document scripts, external links, embedded executables
  or automatic network fetches. Enforce parser isolation and CPU/memory/file/time limits.
- Target SQL uses parameterised, preapproved operations, not AI-generated SQL. Target APIs
  enforce egress allowlists, TLS verification and bounded responses/redirects; deny SSRF.

## Source permission preservation

Effective permission is the intersection of platform policy, local policy and source
authorisation for the approved requester/service-identity mode. A powerful service account
must not launder access for a denied user. Delegation, constrained service execution or
explicit source-owner entitlement mapping must be demonstrated adapter by adapter;
unsupported per-user ACL checks mean deny, not “agent account can read it.”

See [identity](identity-and-access.md) for modes and [threat model](threat-model.md) for tests.

## Secrets, data and audit

Use enterprise/vault/OS-protected secret stores; plans hold secret references, not values.
Encrypt stores, backups and local spools at rest with managed keys; segregate duties and
tenant access. Rotate certificates/tokens with a tested overlap and revoke compromised
agents and credentials. Tokens are short-lived, audience/issuer-bound and never logged.

Default to metadata-only cloud egress. Evidence and payload export require classification,
purpose, authorised recipients, retention and source-owner approval. Minimise paths,
personal/business contents and raw document excerpts in telemetry; the estate graph
itself may be sensitive. Apply deletion/legal-hold policy to retained evidence and backups.

Security audit is separate from operational logs: append-only storage with independently
controlled writers/readers, retention enforcement, integrity verification and reviewed
immutable/WORM storage where required. Record actor, decision, policy/plan versions,
resource, source authorisation mode, time, correlation and outcome; not secrets or payloads.
If required audit cannot be durably accepted centrally or in an approved local spool,
deny new discovery/execution/deployment. Full spool, lost integrity or expired policy
fails closed; never silently drop required records.

## Revocation and incident handling

Suspend capability/connector, reject new work centrally, push invalidation over the
outbound channel, and enforce short-lived leases locally. An offline agent cannot promise
instant revocation: the approved maximum lag is a release gate. Running operations stop
at safe boundaries; already committed external effects need reconciliation, not retries.
Loss of valid identity/policy/source authorisation blocks new work.

Contain a compromised agent by revoking enrollment/certificates, isolating its assignments,
rotating affected secrets and preserving security evidence. Patch through signed,
staged updates with rollback safeguards against reinstating revoked policy.

## Approval gates

No deployment until tenant isolation, source ACL preservation, secure enrollment/rotation,
audit integrity, egress/retention, parser isolation and revocation tests pass.
Excel/VBA execution has an additional feasibility and risk gate: see
[deployment](deployment.md#excelvba-execution-gate). This document is a target design,
not a claim of implemented controls or compliance certification.
