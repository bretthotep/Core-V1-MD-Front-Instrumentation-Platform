# UX — proposed

The console is an application-estate map: application/resource nodes, approved connector
edges and immediately visible health. It is not a CRM, spreadsheet or old ESB designer.
The existing Core V1-MD narrow Qt display is a different UI; no reuse or replacement is assumed.

## Primary journey

1. Select an explicitly configured resource through the assigned agent and register it.
2. See bounded discovery progress, coverage, permission failures and unknowns.
3. Open the twin: structure, evidence, dependencies and proposed capabilities.
4. Review capabilities, business semantics and execution effects.
5. Drag to another permitted resource to request feasibility analysis.
6. Review schema mappings, transformations, validation, confidence and unresolved items.
7. Review effective identity, source permissions, scopes, egress, quotas and side effects.
8. Obtain required independent approvals; show exact approved versions.
9. Deploy; show “active” only after agent acceptance.
10. Observe capability/dependency health, query authorised interfaces and receive drift warnings.

## Views

| Selection | Detail |
|---|---|
| Application node | Twin revisions, discovery gaps, owner, capabilities and dependencies |
| Connector edge | Plan/mapping versions, auth mode, approvals, deployment and telemetry |
| Health issue | Cause chain, permitted evidence, impact, age and suggested action |
| Proposed mapping | Source/target semantics, confidence/method, evidence and review controls |
| Drift alert | Before/after contract, known/unknown consumers, suspension and repair proposal |

Graph/list/search results must be permission-filtered; even hidden node counts or
edge labels can reveal restricted applications. Show “unknown” and “proposal” distinctly
from healthy/approved. Denials should be actionable without leaking unauthorised paths.

Support keyboard navigation, an equivalent accessible list/tree, screen-reader labels,
non-colour health indicators and reduced motion. Large estates need clustering/search
and bounded graph queries. Dragging never approves or deploys by itself.

First UI acceptance covers register → review → approve → deploy → health → drift with
a real approved Excel pilot. Visual mocks cannot satisfy runtime/security gates.
