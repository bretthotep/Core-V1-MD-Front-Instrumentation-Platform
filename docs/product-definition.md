# Product definition — proposed

## Purpose and users

A governed fabric around existing enterprise applications, documents, files, and data
sources: discover their structure and dependencies, propose business capabilities,
connect approved capabilities, expose standard interfaces, and explain operational health.

Primary users are application owners, integration operators, security administrators,
and authorised business/API/AI consumers. Owners review semantics; operators deploy
connections; security administrators govern access; consumers use approved contracts
without needing to understand the source's implementation.

## Product boundaries

| Concern | Fabric responsibility | Remains authoritative elsewhere |
|---|---|---|
| Resource discovery | Bounded, permission-aware inspection | Source contents and ACLs |
| Application context | Versioned twins with evidence and uncertainty | Actual application behaviour |
| Integration | Approved schemas, mappings, deterministic connector plans | Business source records |
| Interfaces | Authenticated, authorised, versioned REST/MCP/event surfaces | Enterprise identity provider |
| Observability | Capability/dependency health and drift impact | Source and infrastructure ownership |
| AI | Optional analysis and proposals | Human/policy approvals and production runtime |

Control-plane metadata and short-lived execution caches do not make the platform a
business data warehouse. Retention and egress are explicit, purpose-limited decisions.

## Resource coverage

The extensible model must accommodate Excel/VBA, PDF and Word collections, folders and
network shares, Access and SQL databases, desktop applications, files, REST/SOAP and
legacy APIs, queues, mainframes, SaaS, and unknown proprietary systems.
Lack of an API is a supported starting point; support for every type is not an MVP promise.

The Excel/VBA slice is first. The claims-folder scenario is a later acceptance scenario:
combine approved Excel rows and PDF evidence into a canonical Claim representation,
not a new claims database. [Discovery](discovery.md) distinguishes observations from
relationship hypotheses.

## Non-goals

No CRM/ERP, system replacement, project/workflow-management suite, generic warehouse,
conventional iPaaS clone, unrestricted RPA/AI agent, proprietary transport or cryptography,
replacement identity system, or unrestricted remote shell. MCP is an interface, not the
product's domain or a privileged access path.

## Measures and unresolved decisions

Measure time from registration to an approved usable capability, evidence coverage,
capability success/latency, drift detection/impact accuracy, and denied unauthorised
operations. Numerical targets require pilot evidence and human approval.

Product sponsor must approve using this repository for the new direction, the pilot
workbook/target, allowed data egress, operating environment, and operational ownership.
See [decision register](roadmap.md#human-approval-register).
