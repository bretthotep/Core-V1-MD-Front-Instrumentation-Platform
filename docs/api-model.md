# API model — proposed

REST/OpenAPI is the MVP consumer projection of approved capabilities; it is not the
core data model. Registry/approval administrative APIs and generated business APIs have
separate permissions and exposure. No unauthenticated “temporary demo” deployment.

## Publication contract

Each interface binds a tenant, capability/version, approved plan, input/output schemas,
route/method, allowed identity modes, resource policy, scopes, rate/quota limits,
timeouts, lifecycle and provenance/audit requirements. Publish OpenAPI only for
authorised metadata; docs and schema names themselves can reveal sensitive information.

Illustrative later routes: `GET /claims/{claimNumber}` for read-only retrieval,
`POST /claims/{claimNumber}/validate` for an approved validation action.
The Excel pilot's CalculatePremium contract uses a POST operation if calculation can
write or execute a macro; a GET must not trigger hidden side effects.
Route shape/version strategy is an approval decision, not a deployed URL in this PR.

## Shared request pipeline

Authenticate → derive tenant/requester → resolve active version → authorise resource/
capability/effects → validate bounded input → enforce quotas → dispatch approved work →
local source authorisation → execute deterministic plan → validate/minimise output →
record authorised provenance, telemetry and audit → respond.

Gateway checks alone are insufficient; application use cases and local agent enforce
policy again. Schema validation must not turn user identifiers into arbitrary paths.
Errors expose a safe category/correlation ID, not file paths, SQL, stack traces or tokens.

## Lifecycle and operations

Explicit contract versions; compatibility tests; deprecation notices to authorised
consumers; suspend/revoke immediately at the control plane and within the approved
local lease window. Track known consumer registrations and access evidence; unknown
external consumers must be marked unknown rather than claimed as a complete dependency graph.

Apply per-tenant/consumer/capability rate limits and bounded queue/concurrency/response
sizes. Long-running operations may return an authorised job reference; polling,
cancellation and results require the same tenant/requester checks as invocation.
POST idempotency and uncertain outcomes follow [connector semantics](connector-model.md).

GET/POST examples are capability projections, not unrestricted execution endpoints.
No arbitrary SQL, shell, macro name, source locator or runtime script accepted from consumers.
