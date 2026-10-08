# MCP — proposed interface, deferred implementation

MCP exposes approved domain capabilities/resources to AI-friendly consumers.
It must not define the Twin or Connector model, be the production runtime, or act as
a privileged back door. REST/OpenAPI is first; MCP is deferred to S9.

Illustrative tools are `get_claim`, `search_claims`, `get_claim_document` and
`get_application_health`. Tools map to an approved capability/version and fixed plan;
they do not expose arbitrary SQL, filesystem access or execution.

## Security parity

Use the same identity, tenant binding, scopes, RBAC/ABAC, source ACL checks, quotas,
validation, audit, output restrictions and revocation as REST. Filter tool lists,
resource enumeration, descriptions, schemas and evidence to the requesting identity.
A tool must not become visible merely because the AI assistant can discover its name.

Workload authentication for the MCP service does not replace authorisation of the
initiating user. Where on-behalf-of delegation is needed, approve and validate the
identity chain; never fall back to a broad service account when delegation fails.
Select the supported MCP version, transport and standard authorisation approach during
the interface implementation stage, not via a custom auth protocol.

## Untrusted content

Documents, workbook strings and tool responses may contain prompt injection.
Treat their text as data, not instructions. AI analysis cannot alter scopes, approve
plans, deploy mappings, choose new network destinations or invoke production tools.
Label uncertainty/evidence and minimise returned content. Tool results cannot mint
permissions or become policy/configuration without a separate reviewed change.

Conformance tests must show REST/MCP policy parity for enumeration, execution,
cross-tenant access, revoked approval, source denial, evidence and health reads.
See [ADR-006](adr/ADR-006-mcp-as-interface.md).
