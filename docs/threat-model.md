# Threat model — proposed baseline

## Assets, actors and boundaries

Assets: source business data and ACLs; credentials/agent certificates; twins/evidence;
capability/plan approvals; tenant isolation; integrity of execution, health and audit.

Actors: legitimate owners/operators/consumers; malicious tenants or compromised accounts;
hostile document authors; compromised AI, agent, control plane, target or update supply chain.
Threat boundaries follow the [security diagram](diagrams/security-boundary.mmd):
consumer → control plane, analysis → approval, control plane → local agent, agent → source/
target, services → protected evidence/audit. A trusted network is not an authorisation boundary.

## Threats and acceptance tests

| Threat | Required mitigation | Negative test / gate |
|---|---|---|
| Spoofed user/service or stolen token | Standard token validation, audience/issuer/tenant binding, short lifetime | Wrong audience/issuer, expired token and forged tenant denied |
| Compromised/misassigned agent | Secure enrollment, mTLS, tenant assignment, certificate revocation | Agent cannot receive another tenant's jobs; revoked cert rejected |
| Cross-tenant object/graph/job leakage | Tenant-scoped storage and policy on every read/write/subscription | Guessed IDs, graph traversal, caches and polling cannot leak |
| Privileged service-account confused deputy | Requester entitlement plus local/source enforcement | Platform allow + source deny still denies; no delegated fallback |
| Shell/SQL/macro injection | Typed fixed operations, parameterised SQL, bounded schemas | Paths, script text and arbitrary procedure names cannot execute |
| Path escape / SSRF | Canonical configured roots, handle-time checks, UNC/egress allowlists | Traversal, symlink/junction race, DNS/redirect destination escape blocked |
| Malicious workbook/PDF/parser bomb | Read-only isolation, no active content, bounded expansion/time/memory | Startup VBA, external refresh, archive bomb and corrupt input fail safely |
| Document/tool prompt injection | Isolated proposal-only AI, no runtime authority/secrets | Embedded “approve/deploy/ignore policy” cannot change execution or grants |
| Tampered/replayed/stale command/config | Standard integrity/signing, assignment, expiry, durable replay checks | Modified plan, duplicate job and stale approval rejected/reconciled |
| Source drift / check-use race | Version pinning, source identity checks and consistency handling | Rename/replace during read suspends or rejects stale contract |
| Data exfiltration through evidence/logs | Classification, field restrictions, egress approval, minimisation | Denied source contents never appear in tool metadata, evidence or logs |
| Audit deletion/repudiation | Separately controlled append-only integrity/retention | Writer cannot delete history; full/unavailable audit fails closed |
| Resource exhaustion | Bounded requests, quotas, concurrency, queues and cancellation | Oversized input/results and disconnected queues stay bounded |
| Duplicate or uncertain side effects | Durable idempotency and explicit reconciliation | Lost target acknowledgement never blindly reruns macro/write |
| Offline revocation / stale policy | Short authorisation leases and safe cancellation | Expired lease blocks new work; maximum lag tested |
| Malicious/downgraded update | Signed packages/configuration, trusted publisher, controlled rollback | Unsigned update rejected; rollback cannot revive revoked plan |

## Residual risks and approval

A fully compromised customer host can access what its OS/source identity allows;
the fabric cannot make an untrusted endpoint trustworthy through TLS. Workbook/VBA
behaviour can include undocumented side effects and unsupported Office automation;
unknown execution effects block deployment. Statistical inference cannot prove business
correctness. Offline revocation has a bounded but nonzero delay.

Security reviewers and source owners must approve these residual risks, isolation and
execution identity, egress/retention, revocation limits, audit storage and incident
procedures before the pilot. Revisit the model for every adapter, identity mode and
interface. This is a design threat model, not a completed penetration test or a claim
that the current simulator supplies these controls.
