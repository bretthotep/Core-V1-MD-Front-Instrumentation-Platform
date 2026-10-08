# Discovery — proposed adapter architecture

## Port and workflow

Adapters implement source-type support detection, bounded read-only discovery, evidence
collection, schema/dependency fingerprinting and discovery diagnostics. Execution is a
separate explicit port; discovering a macro never grants permission to run it.

The shared discovery request carries tenant/resource/agent identity, authorised locator,
source authorisation mode, policy revision, limits, classification and cancellation.
The result carries observations, proposed assertions, schema/dependencies, evidence,
coverage, warnings, source fingerprint and adapter version. No protocol-specific tool
definition is part of the domain contract.

Register → verify identity/root/ACL → select compatible adapter → inspect safely →
record versioned evidence → build partial twin → optionally infer → owner review.
Run identifiers and source fingerprints support idempotent ingestion, partial results,
and re-discovery without duplicating graph edges.

## Excel/VBA first

Inspect workbook metadata; visible/hidden sheets; named ranges; tables and column types;
formula text; external-workbook references; connection metadata; VBA modules, procedure
names/signatures and static read/write/dependency references where legally and technically
accessible. Mask secrets in connection strings. Bound file/ZIP expansion, cell counts,
module sizes, nesting, processing time and output volume.

Do not open a workbook in a mode that runs startup macros, recalculates unsafe external
functions, follows links, refreshes data connections or changes files. Parser selection
and the exact supported `.xlsx`/`.xlsm` subset require a feasibility spike. Password-protected
or inaccessible VBA is “unavailable”; do not bypass protection.

Static candidates for inputs, outputs and capabilities require review. Indirect calls,
dynamic paths, COM dependencies, network access and side effects may remain unresolved.
Behavioural execution/file modification observation is a later, separately approved
isolated mode, not part of safe default registration.

Dependencies discovered outside configured scope are unresolved references; request
owner approval to register them rather than crawling them automatically.

## Extension points

Future Excel, PDF, Folder, SQL, Word, Access, REST, SOAP, Mainframe and DesktopApplication
adapters share the same identity, bounded-discovery, evidence and error contracts.
Adapters declare versions, supported formats, required permissions and coverage;
conformance tests prevent extensions from bypassing common policy.

## Claims-folder scenario — later, not MVP

Given an approved root such as `\\ClaimsServer\Intake\`, a Folder adapter inventories
permitted children with depth/file/time quotas and no reparse-point escapes. PDF/Excel/Word
adapters inspect only authorised files. Naming conventions and matching identifiers
produce evidence-backed relationship hypotheses, not definitive joins.

An owner approves the Claim schema, key uniqueness, PDF-to-row matching, field precedence
and conflict handling. An approved `GET /claims/{claimNumber}` plan locates the Excel row
and permitted document, extracts/validates values, assembles a canonical response and
records field lineage. Missing, duplicate or conflicting identifiers return defined
errors or explicit partial results; never silently choose a document.

OCR is optional and confidence-bearing; document text is untrusted input to AI.
PDF/Word/OCR adapters and composite claims execution are deferred to S9.
See [claims diagram](diagrams/claims-example.mmd).
