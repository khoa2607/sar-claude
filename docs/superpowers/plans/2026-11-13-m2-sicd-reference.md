# M2 SICD Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a documented, checked reference (the Umbra SICD for DS-001) and the minimum coordinate mapping needed to compare future formed images with it.

**Architecture:** Read-only SICD inspector (same provenance model as M1), a file-level CPHD-versus-SICD metadata comparison with a priori tolerances, and thin tested wrappers over SARkit's SICD/CPHD coordinate functions. The comparison methodology is a document. No image formation.

**Tech Stack:** Python 3.13, SARkit 1.12.0 (`sarkit.sicd`, `sarkit.cphd`, `sarkit.wgs84`), numpy, pytest. No new dependencies.

**Spec:** the user's "Execute M2" request (session 2026-11-13) and [M2_PLAN](../../M2_PLAN.md).

## Global Constraints
- CPU only; CPHD and SICD files are opened read-only and never modified; `cphd/` stays git-ignored.
- No image formation, no jammer; no commit or push without approval.
- Do not assume undocumented metadata: absent fields are reported `unavailable`.
- Tolerances are defined from stated principles **before** looking at the differences; exceedances are reported, not tuned away.
- Reuse SARkit functions for projections; implement only what is missing.
- Coordinates: ECF WGS 84 meters; SICD row/col are global zero-based pixel indices.

## Review Focus
- SICD file that is not NITF/SICD, truncated or missing: controlled error, exit code 2.
- SICD lacking optional elements (no weighting, no Radiometric): reported as `unavailable`, no crash.
- Mapping round trip off-plane or outside the image: result returned, never silently clipped.
- Image corner pixels (0,0) and (N-1,M-1): map to the SICD's declared corner positions.
- Row/col transposition and sign errors: pinned by a point displaced by exactly one pixel along each axis.

---

### Task 1: SICD inspector
**Files:** Create `src/sarsil/xmlparam.py` (shared XML-to-`Param` helpers moved from `cphd/inspector.py`), `src/sarsil/sicd/__init__.py`, `src/sarsil/sicd/inspector.py`, `tests/test_sicd_inspector.py`; Modify `src/sarsil/cphd/inspector.py` (import helpers).
**Interfaces:** Produces `inspect_sicd(path, run_consistency=True) -> dict` (JSON-ready, provenance-tagged; keys `source`, `format`, `image`, `grid`, `formation`, `frequency`, `timeline`, `geodata`, `scpcoa`, `waveform`, `consistency`, `capabilities`).
- [ ] Failing tests: missing/empty/non-NITF file raise `MalformedFileError`; real-file report has `image.num_rows == 5045`, `grid.type == "RGAZIM"`, `formation.algorithm == "PFA"`, weighting reported `unavailable`, consistency `failed == 0`, every leaf has a valid provenance, JSON-serializable and deterministic.
- [ ] Implement with `sarkit.sicd.NitfReader` and `SicdConsistency`; verify tests pass.

### Task 2: Coordinate mapping
**Files:** Create `src/sarsil/geometry/__init__.py`, `src/sarsil/geometry/sicd_coords.py`, `tests/test_sicd_coords.py`.
**Interfaces:** Produces `SicdGeometry.from_sicd(path)` with `.scp_ecf`, `.row_uvect`, `.col_uvect`, `.row_ss`, `.col_ss`; `pixel_to_plane_m(rowcol) -> (xrow, ycol)`; `plane_m_to_pixel`; `pixel_to_ecf_slant(rowcol) -> ecf`; `ecf_to_pixel_slant(ecf)`; `pixel_to_ecf_ground(rowcol, height_m=None) -> ecf` (SARkit `image_to_ground_plane` / constant-HAE); `ecf_to_pixel(ecf)` (SARkit `scene_to_image`); `ecf_to_cphd_iac(cphd_xmltree, ecf)` thin wrapper.
- [ ] Failing tests: SCP pixel maps to SCP ECF; one pixel along row/col moves exactly `SS` meters along the matching unit vector (independent analytic check); unit vectors orthonormal; round trip pixel -> ground ECF -> pixel within 1e-3 pixel; SCP ECF maps to CPHD IAC (0,0,0); SICD corner pixels land inside 1 pixel of the declared ACP corner lat/lon.
- [ ] Implement as thin wrappers; verify tests pass.

### Task 3: CPHD versus SICD comparison
**Files:** Create `src/sarsil/compare/__init__.py`, `src/sarsil/compare/cphd_sicd.py`, `scripts/compare_cphd_sicd.py`, `tests/test_compare_cphd_sicd.py`.
**Interfaces:** Produces `compare_cphd_sicd(cphd_path, sicd_path) -> dict` with `rows: [{quantity, cphd, sicd, difference, unit, tolerance, tolerance_basis, status, note}]`, where `status` is `within_tolerance`, `exceeds_tolerance` or `informational`, plus `summary` counts.
- [ ] Failing tests: row set contains SRP vs SCP ECF, IARP corners vs ACP corners, frequency min/max, waveform parameters, vector count vs IPP range, polar angle span from `PolarAngPoly` vs CPHD angular span; every row has a tolerance basis string; summary counts add up; report deterministic.
- [ ] Implement; verify tests pass. Observed exceedances are documented in `docs/M2_SICD_REFERENCE.md`, never adjusted away.

### Task 4: Documentation and verification
**Files:** Create `docs/M2_SICD_REFERENCE.md` (findings, comparison table, methodology, limitations); Modify `docs/DATASETS.md`, `docs/PROGRESS.md`, `docs/DECISIONS.md`, `docs/DEVELOPMENT_ROADMAP.md`, `docs/M2_PLAN.md`, `CLAUDE.md` (stale "no commits yet" line).
- [ ] Run the full suite and record counts; confirm CPHD and SICD SHA-256 unchanged; `git status` shows nothing staged.
