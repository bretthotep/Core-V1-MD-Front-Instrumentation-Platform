# Testing strategy — proposed

## Existing product compatibility

This PR changes documentation only; Core V1-MD source, dependencies, configuration and
tests are unchanged. Its existing CI uses Python 3.12 on Windows/Linux and, from
`core-v1-md/`, runs `ruff check .`, `python -m pytest -q`, a headless simulator render,
and the proof-of-concept gallery. Do not replace this pipeline with fabric tooling.

There is no existing documentation-specific linter/test framework. Review relative
links, named sections, Mermaid source, requirement/stage references, proposal status,
and consistency by inspection and lightweight validation; adding a new test dependency
is not necessary for this design PR. No runtime test pass is claimed by this document.

## Future fabric test layers

| Layer | Scope |
|---|---|
| Domain/use case | Tenant invariants, twin revisions, confidence/unknown handling, lifecycle and policy decisions with fake ports |
| Adapter conformance | Bounded discovery, evidence shape, permissions, unsupported inputs, cancellation and resource limits |
| Fixture discovery | Synthetic `.xlsx`/`.xlsm`, hidden sheets, links, formulas, accessible/protected VBA and corrupt/oversized files |
| Contract | Schemas, OpenAPI and later MCP parity, versioning and backwards compatibility |
| Identity/security | Token verification, source-denial intersection, tenant escape, egress, injection, replay/revocation and audit failure |
| Integration | Real chosen OS/identity/source mode, signed enrollment, secret rotation, SQL/API target and consistent workbook reads |
| End-to-end | Approved workbook → twin → capability → secure API → selected target → health → drift suspension/reapproval |
| Failure/resilience | Offline agent, stale policy, queue pressure, audit spool full, source edit, timeout and uncertain writes |
| Operational | Restore, certificate/credential rotation, revocation, signed update and rollback/reconciliation drills |

Separate safe static fixtures from explicitly approved execution fixtures. No real
customer data or credentials in the repository. Dynamic VBA integration tests require
the approved Windows/Excel environment and cannot be faked as successful on Linux.

## Release gate

Each requirement links to deterministic test evidence and reviewer approval. Deny-paths
matter as much as successful calls. Test source ACL changes, cross-tenant access,
prompt injection and drift between validation and execution. Assert no generic execution,
secret leakage, unexpected source writes or unapproved egress.

Security audit and business provenance are independently verified; telemetry alone does
not prove audit durability. Recovery/idempotency tests must demonstrate “outcome unknown”
handling instead of asserting exactly-once delivery.

Numerical performance/resource/revocation targets are set after a measured pilot; release
requires approved limits and repeatable test conditions. Re-run the threat review when
adding any new adapter or execution primitive.
