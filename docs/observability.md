# Business/application observability — proposed

Observe whether a business capability functions, not only whether a host or agent is up.
An agent heartbeat is necessary context, not proof that CalculatePremium is correct.
Observations are timestamped, tenant-scoped, permission-filtered and evidence-linked.

## Signals and health

| Area | Signals |
|---|---|
| Resource | Availability, modification/freshness, schema integrity, access failures |
| Dependency | Required/optional availability, network latency, freshness, auth/permission health |
| Capability | Execution success, latency, validation failures, expected vs abnormal behaviour |
| Connector/interface | Agent heartbeat/uptime, queue lag, circuit state, deployment version, API errors |
| Security | Denials and credential/certificate expiry; separate authoritative audit trail |

Health states: healthy, degraded, unavailable, unknown and suspended. Include observed
time, valid-until/freshness, rule/baseline version, cause, evidence, affected entities,
business impact and suggested action. Unknown/stale data must not render green.

Hierarchical view: Enterprise → Application → Capability → Dependency → Resource.
The underlying dependency graph may have shared nodes/cycles; propagation must detect
cycles and avoid duplicate amplification. Required unavailable dependencies can make
a capability unavailable; optional failures may degrade it. Approved business impact
rules take precedence over a naive “worst colour wins” aggregate.

Example (illustrative): CalculatePremium is degraded because Rates.xlsx last changed
nine days ago against an approved seven-day update window. Evidence is the permitted
modification observation; impact is potentially stale rating factors. A network-share
latency increase or offline hosting workstation is a separate cause, not inferred solely
from the workbook timestamp.

## Collection and safeguards

Collect bounded metadata/fingerprints, approved passive probes and execution telemetry.
Do not run side-effecting macros as “health checks” without separate approved semantics.
AI may suggest a baseline/anomaly, but thresholds and remediation actions need review;
learned patterns do not prove business correctness.

Use structured events, correlation/trace IDs across API/control-plane/agent/target,
duration/error categories and source/plan revisions. Avoid business contents, tokens,
high-cardinality sensitive paths and unbounded metrics. Control backpressure, sampling
for operational telemetry, clock skew, stale/missing heartbeats and alert suppression.
Security audit is never sampled.

The estate UI displays cause → dependency chain → permitted evidence → impact.
Numerical SLOs, probe intervals and freshness thresholds need pilot approval.
See [observability diagram](diagrams/observability.mmd).
