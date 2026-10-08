# Core-V1-MD-Front-Instrumentation-Platform

**Core V1-MD** – a Sony MiniDisc-inspired front-panel instrumentation system for a
Thermaltake Core V1 gaming/development PC.

The project lives in [`core-v1-md/`](core-v1-md/). Start with its
[README](core-v1-md/README.md). The UI designs are in the
[proof-of-concept gallery](core-v1-md/docs/images/poc/README.md). To run the simulator:

```powershell
cd core-v1-md
pip install -r requirements.txt
python -m simulator
```

Or open it in **GitHub Codespaces** (Code → Codespaces → Create codespace). The dev container
installs everything and provides a browser desktop on port 6080 for the simulator window. See
[Codespaces](core-v1-md/README.md#github-codespaces).

## Proposed enterprise integration fabric — design only

A separate [architecture proposal](docs/architecture.md) explores a **Secure Application
Integration & Observability Fabric**: “Connect what you already have. Register it.
Understand it. Connect it. Monitor it. Query it.”

This is **not implemented** by the Core V1-MD simulator. The existing Python/Qt
application, hardware roadmap, tests, and workflows are unchanged. Adoption of the
new product, its repository location, and its technology choices require human approval;
this proposal does not silently repurpose the instrumentation platform.

Start with the [product definition](docs/product-definition.md),
[requirements](docs/requirements.md), [security boundary](docs/security.md),
[MVP and issue-ready stages](docs/roadmap.md), and [proposed ADRs](docs/adr/ADR-001-agent-trust-boundary.md).
The [architecture index](docs/architecture.md#design-documentation) links every design document
and Mermaid diagram. No enterprise integration or security capability described there
should be interpreted as an existing feature.
