# Evidence and provenance — proposed

Evidence supports discovery/assertions; provenance traces a returned data element or
transformation to its source. Both are first-class, access-controlled domain concepts,
not unstructured AI explanations or a promise of complete lineage.

## Record model

Record tenant/evidence ID, resource/source version or fingerprint, protected locator,
observation/extraction timestamp, method and adapter/tool/model version, confidence
where applicable, transformation/version, parent evidence IDs and approval reference.
For cells: sheet/table/row/column or range; for documents: page/region; for code:
module/procedure/location. Stable keys plus source fingerprint are needed because row
numbers and file names can change. Unknown location/method is explicitly unknown.

Illustrative Claim fields:

| Field | Source locator | Method | Confidence |
|---|---|---|---|
| claimAmount | Claim_12345.pdf, page 1, source fingerprint | OCR | Example 0.987; requires extraction evidence |
| claimStatus | ClaimsRegister.xlsx, Claims sheet, row 184, source fingerprint | Cell read | Not an invented AI probability |

Transformed output links to all contributing inputs, mapping/version and validation
outcome. Conflicting values retain both sources and the approved resolution rule;
missing evidence cannot become a verified fact.

## Retention and security

Prefer references/fingerprints and minimal approved snippets over copied documents.
An integrity hash alone is not semantic evidence or proof of authenticity. A protected
local evidence reference may require authorised retrieval through the assigned agent.
Do not export raw source content merely to help an AI explanation.

Read policies apply to evidence, locations, derived facts and output fields. A consumer
denied the source must not recover its contents through evidence APIs or health causes.
Classification, residency, retention, legal hold, deletion and backup handling require
source-owner/security approval. Retained audit may record an evidence ID without retaining
the business payload; deleted/redacted evidence is explicitly unavailable.

Changes append new records; no silent rewrite of historical assertions. Source version
checks prevent attributing a result to evidence gathered from a different workbook revision.
See [Application Twin](application-twin.md) and [security](security.md).
