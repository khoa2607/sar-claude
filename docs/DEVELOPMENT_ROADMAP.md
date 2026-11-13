# Development Roadmap

Last updated: 2026-11-12. **Everything below is proposed; nothing is implemented.** A milestone starts only after user approval, recorded in [PROGRESS](PROGRESS.md). Decisions: [DECISIONS](DECISIONS.md).

## Architecture sketch (proposed)
- **Source adapters:** one adapter per CPHD source (vendor), converting to a common internal metadata model. Core code is vendor-agnostic. Parsing uses SARkit (CPHD 1.0.1 and 1.1.0).
- **Metadata model:** each parameter tagged measured, derived, assumed or unavailable, with units and frame.
- **Processing core:** signal-model utilities, image formation (backprojection first), CPU and GPU backends behind one interface.
- **Experiment layer:** configuration hashing, run records (versions, hardware, parameters, data identifiers).
- **Artifact store:** scientific products kept apart from visualization images.

### Intermediate artifact storage requirements
1. Complex data stored as complex, with dtype and shape recorded; no lossy conversion.
2. Each artifact has a sidecar record: source dataset ID and hash, processing steps with parameters, software versions, units, coordinate frame, parameter provenance tags.
3. Chunked, resumable writes for large arrays; never overwrite a source CPHD.
4. Content-addressed or hash-verified so experiments are reproducible and comparable.
5. Visualization images (PNG and similar) are derived outputs, regenerated from artifacts, never read back by science code.
6. Format choice (HDF5, Zarr or memmap plus sidecar) is open (O-003).

## Milestones

| ID | Milestone | Depends on | Acceptance criteria | Validation checkpoint |
|---|---|---|---|---|
| M0 | Environment and repo: Python 3.12 venv, pinned SARkit, pytest, git init (P-001, P-002) | Approval | `import sarkit` works; versions pinned in a lockfile; empty test suite runs | Record versions in PROGRESS |
| M1 | **Finalized 2026-11-12 with documented limits ([M1_INSPECTOR](M1_INSPECTOR.md)); multi-provider compatibility not validated.** Read-only CPHD inspector: list channels, shapes, dtypes, PVP names, key metadata, with provenance tags; run SARkit consistency check | M0, one CPHD file | Never opens file for write; output matches SARkit reader values on the sample; handles missing fields as "unavailable" | Unit tests with a small CPHD fixture; SARkit checker result recorded |
| M2 | SICD reference and image formation preparation (plan: [M2_PLAN](M2_PLAN.md); proposed, not started) | M1, DS-001 SICD | SICD downloaded and checked; SICD interpreted; CPHD-to-SICD comparison table; coordinate mapping; comparison methodology; no formation code | SICD-to-SICD noise floor; mapping unit test |
| M2b | Multi-source adapter interface plus a second provider's file | M1, a second provider file | Both sources produce the same internal model; no vendor branches in core | Cross-source metadata comparison test |
| M3 | Artifact store and run records | M1 | Write/read round trip bit-exact for complex data; sidecar present; source data hash unchanged | Round-trip and hash tests |
| M4 | Reference signal model checks (CPHD signal model, reference geometry) | M1 | Results agree with SARkit's own functions within stated tolerance | Reference-case tests |
| M5 | Image formation prototype (CPU backprojection on a chip) | M2, M4 | Point-target response matches analytic resolution and sidelobe values within tolerance; independent cross-check against a second implementation (FastSAR or torchbp, run in a separate environment) | Documented comparison, raw logs |
| M6 | Performance and GPU backend | M5 | Same output as CPU within tolerance; benchmark per AGENTS.md rules | Benchmark report with raw logs |
| M7 | Waveform modeling where metadata supports it | M4 | Only used when metadata justifies it; assumptions listed | Review by a second model or human |

## Dependencies on open items
- M0 needs P-001/P-002 approval.
- M1 uses dataset DS-001 ([DATASETS](DATASETS.md)); available since 2026-11-12.
- M5 depends on O-001 (build vs adopt) and O-002 (WSL2 vs native).

## Review points
Algorithmic milestones (M4, M5, M7) get an independent review before being marked done.
