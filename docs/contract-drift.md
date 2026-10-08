# Contract drift — proposed

Detect resource changes, assess contractual impact, suspend unsafe execution and
propose a reviewed repair. A file timestamp is a signal to inspect, not proof of a
breaking schema change. Fingerprint metadata/schema/dependencies separately from data.

## Flow

1. Approved watch/poll discovers a new fingerprint; debounce and check source stability.
2. Bounded re-discovery compares schemas, procedure signatures, ACLs, dependencies and
   configuration with the approved revision.
3. Traverse typed dependencies to affected capabilities, connectors, interfaces and
   known consumers. Mark unknown downstream consumers explicitly.
4. Classify compatible, breaking, security-relevant or uncertain changes. Required
   unknown/breaking changes suspend affected execution; no silent default-value repair.
5. Propose a mapping/repair with evidence, confidence and test impact. Human approval
   produces a new plan/schema/twin revision.
6. Validate against representative fixtures and source permissions, deploy with agent
   acknowledgement, audit the change and monitor outcomes.

Example: `PolicyNumber` renamed to `Policy_No` creates a mapping proposal.
Name similarity alone does not prove meaning, type or units; dependent plans stay
suspended until approved compatibility is demonstrated.

## Safety and recovery

Bind execution to validated contract versions and verify source identity/fingerprint
at access time. File replacement between check and open, partial writes and concurrent
edits must produce a consistent snapshot or a clear retryable read failure; side effects
cannot be retried blindly. ACL/identity changes invalidate execution even without a
schema change. Cosmetic modifications do not require indiscriminate approval resets.

Keep diff, evidence, impact graph, policy/approval decisions, deployment revision and
post-change telemetry. Historical versions are immutable; rollback cannot restore
revoked permissions or target an incompatible source. Poll intervals, stale contract
limits and suspension rules require pilot approval.

MVP: workbook schema/dependency fingerprint, field rename impact, suspension and
reviewed recovery. Automated semantic repair and comprehensive dynamic dependencies
are deferred.
