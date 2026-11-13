# Decisions

Last updated: 2026-11-12. Entries are append-only; supersede with a new entry. Status: **Accepted** (settled), **Proposed** (needs user approval), **Open** (alternatives unresolved). Evidence is in the linked Phase 0A documents.

## Accepted

| ID | Decision | Basis |
|---|---|---|
| D-001 | Phase 0A is research-only. No third-party skills or MCP servers installed; no SAR code written. | User instruction |
| D-002 | `CLAUDE.md` imports `AGENTS.md` (`@AGENTS.md`). Shared rules live in AGENTS.md; CLAUDE.md holds Claude-specific rules and navigation. | Claude Code docs: with both files present, only CLAUDE.md loads unless it imports AGENTS.md. [memory docs](https://code.claude.com/docs/en/memory.md) |
| D-003 | SARkit is the primary CPHD library. SarPy's own CPHD implementation is deprecated in favor of SARkit. | SarPy source marks CPHD classes `@deprecated("... Please use sarkit.")`; SarPy 2.0 is a merge with sarkit. See [OPEN_SOURCE_REUSE](OPEN_SOURCE_REUSE.md). |
| D-004 | Built-in Claude Code features and deterministic scripts come before any third-party skill. Skills are vendored after full review, never installed from a registry. | [RECOMMENDED_STACK](RECOMMENDED_STACK.md), [SKILL_SECURITY_AUDIT](SKILL_SECURITY_AUDIT.md) |
| D-005 | Source CPHD data is read-only; multi-source adapter design from the start; scientific artifacts are stored separately from visualization images. | User principles |
| D-006 | No custom subagents, no agent teams at the start. | [MULTI_AGENT_ARCHITECTURE](MULTI_AGENT_ARCHITECTURE.md) |
| D-007 | **Codex is not used** (user decision 2026-11-12). Supersedes the Codex-reviewer role in earlier documents. AGENTS.md stays as the shared-rules file imported by CLAUDE.md. | User |
| D-008 | Python 3.13.14 via existing install, `uv` 0.13.7 already present; project venv `.venv`. Implements P-001. | Environment inspection |
| D-009 | Git initialized on branch `main`. Implements P-002. M1 committed as `8653056` and pushed to origin/main. | User |
| D-010 | SARkit 1.12.0 (with jbpy 0.6.1, lxml 6.1.3, numpy 2.5.4, shapely 2.2.0) pinned in `requirements.lock.txt`. SarPy not installed: no compatibility need identified (SARkit has no CPHD 0.3 support; revisit only if a 0.3 file appears). | User approval |
| D-011 | Superpowers 7.0.2 (upstream commit 22f0b46, MIT) installed from its official repository as a **project-scope plugin** via marketplace `superpowers-dev` (marketplace entry is in user settings). `SUPERPOWERS_DISABLE_TELEMETRY=1` set in project `.claude/settings.json`. Approved for planning, TDD, debugging and verification; the visual brainstorming companion is not to be enabled. | User approval; deviates from the earlier "vendor, do not install" advice in [RECOMMENDED_STACK](RECOMMENDED_STACK.md) |
| D-012 | Caveman is limited to a vendored copy of one file (`skills/caveman/SKILL.md`, upstream commit ad47375, Apache-2.0) in `.claude/skills/caveman/`, set to manual invocation. No plugin hooks, installer, CLI, proxy or hosted service. Reason: upstream installer documents CLI telemetry on by default and four hooks (one per prompt). Experiment criteria in [TOKEN_OPTIMIZATION](TOKEN_OPTIMIZATION.md). | User approval of a limited experiment |
| D-013 | First dataset is DS-001, Umbra-05 `2023-11-19-16-12-16` (CPHD 1.1.0, 588 MiB, CC-BY-4.0 per STAC). The matching SICD was downloaded on 2026-11-13 (D-019). See [DATASETS](DATASETS.md). | User selection; verified |
| D-014 | M1 conventions: full valid aperture by default (chunking never changes the selection); samples read as big-endian; nonuniform timing flag is configurable (`--nonuniform-rtol`, default 0.1%, a choice not a standard); default chunk budget 256 MiB is a placeholder; PVP/XML values and external catalog metadata are never merged. See [M1_INSPECTOR](M1_INSPECTOR.md). | M1 implementation |
| D-016 | SIGNAL PVP: 0 = zero-filled vector with no valid signal (excluded from the default aperture), 1 = normal, other values kept and flagged uncertain. Basis: SARkit's checker requires zeros where SIGNAL is 0 and ties SignalNormal to all-ones; the NGA standard text was **not** read, so meanings above 1 are unconfirmed. | M1 finalization |
| D-017 | Source polarization stays as stated in the CPHD XML (X/X for DS-001). It is not reconciled with the catalog's VV. | User instruction |
| D-015 | pytest 9.2.0 added as dev dependency; no package install of `sarsil` (code is run through `scripts/` or pytest's `pythonpath`) to avoid adding build tooling. | Implementation |
| D-018 | Milestone naming: M2 is now "SICD reference and image formation preparation" (user, 2026-11-12). The multi-source adapter and second-provider work moved to M2b. Nothing in M2 or M2b is started. | User |
| D-019 | M2 reference: the Umbra SICD (PFA, RGAZIM, 5045 × 5345) is a *vendor reference*, not ground truth. CPHD-versus-SICD comparison tolerances come from stated principles (one SICD resolution cell for positions, its angle at the slant range, one pulse interval for times, 1 Hz, 1e-9 relative, 1% span). Results: 20 within, 4 exceed (explained post hoc by a 288 µs reference-time offset), 6 informational. See [M2_SICD_REFERENCE](M2_SICD_REFERENCE.md). | M2 |
| D-020 | Coordinate mapping reuses SARkit's SICD projections (`sarsil/geometry/sicd_coords.py`); only thin wrappers were written. The CPHD image-area plane equals the SICD ground plane (uIAZ = geodetic up at the SCP). SICD `ImageCorners` differ from SARkit-projected corners by 13–15 m; the producer's method is undocumented, so tests pin orientation and a 20 m regression bound, not accuracy. | M2 |
| D-021 | Three test tolerances were loosened after a first run, with measured reasons (unit vectors only unit to 3e-10; SARkit scene-to-image 1 mm stopping rule; ImageCorners method). Recorded so the history is visible. | M2 |
| D-022 | Image comparison methodology fixed in [M2_SICD_REFERENCE](M2_SICD_REFERENCE.md#image-comparison-methodology-defined-nothing-implemented): compare on the SICD grid, valid-data mask, sub-pixel registration reported, one global amplitude scale, complex coherence for phase, focus metrics on isolated scatterers, and a SICD self-comparison measurement floor before acceptance tolerances are set. | M2 |
| D-023 | **M2 accepted by the user (2026-11-13) with documented limitations**; unresolved geometry items are listed in [M2_SICD_REFERENCE](M2_SICD_REFERENCE.md#acceptance-unresolved-issues-and-numerical-tolerances) and are not validated. Committed as `feat: add SICD reference and geometry validation`. | User |
| D-024 | Cross-platform hygiene: `.gitattributes` normalizes text files to LF and marks datasets binary; datasets restore from public URLs with hash checks ([DATASETS](DATASETS.md#restore-on-a-new-computer-verified-2026-11-13)); `CLAUDE.md` has a fresh-machine checklist. | Handoff |

## Proposed (awaiting approval)

| ID | Proposal | Note |
|---|---|---|
| P-003 | Phase 0B first milestone: read-only CPHD inspection tool built on SARkit (see roadmap M1). | [DEVELOPMENT_ROADMAP](DEVELOPMENT_ROADMAP.md) |

## Open alternatives

| ID | Question | Options | Evidence status |
|---|---|---|---|
| O-001 | Image formation: build vs adopt | (a) build own backprojection; (b) depend on FastSAR; (c) use FastSAR and torchbp only as cross-check references | FastSAR is MIT, alpha, 5 weeks old, Linux/macOS wheels only. See [OPEN_SOURCE_REUSE](OPEN_SOURCE_REUSE.md). Leaning (c). |
| O-002 | Runtime platform for GPU | Native Windows (CPU) vs WSL2 (CuPy/FastSAR GPU path) | Machine has an RTX 3060 12 GB. WSL2 not checked. |
| O-003 | Intermediate artifact format (HDF5, Zarr, raw memmap + sidecar) | Not researched | Decide in M3. |
| O-004 | ~~Codex reviewer mechanics~~ | Closed by D-007 | n/a |
| O-005 | Further skills (compute-sanitizer, K-Dense statistics) | See [RECOMMENDED_STACK](RECOMMENDED_STACK.md) | Bodies not yet read. |
| O-006 | Graphify; whether Caveman stays after the experiment | Graphify deferred; Caveman judged on measured data | [TOKEN_OPTIMIZATION](TOKEN_OPTIMIZATION.md) |
