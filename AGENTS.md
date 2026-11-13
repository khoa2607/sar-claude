# AGENTS.md — Shared engineering rules (Claude Code and Codex)

Applies to every agent working in this repository. Tool-specific behavior lives in each tool's own file. Status of planned items is tracked in `docs/PROGRESS.md`.

## Repository conventions
- Language: Python 3.12+ (SARkit requires it). Project environment: `.venv` (CPython 3.13, created with `uv`); interpreter `.venv/Scripts/python.exe` on Windows. C++/CUDA only after profiling shows a need and a decision is logged in `docs/DECISIONS.md`.
- Layout: `src/sarsil/` (`provenance.py`, `xmlparam.py`, `cphd/`, `sicd/`, `geometry/`, `compare/`), `tests/` (pytest; `pyproject.toml` sets `pythonpath`, no package install), `scripts/` (CLI launchers), `docs/`. Create new directories only when the approved milestone needs them.
- `cphd/` holds source datasets: **read-only, never modified, never committed**. Derived data goes elsewhere.
- One approved milestone at a time. Keep changes small and reviewable. Do not refactor unrelated code.

## Code organization
- Separate: I/O (CPHD readers, adapters per source), metadata model, signal processing, image formation, storage of artifacts, validation, visualization.
- Source-specific logic lives behind an adapter interface so multiple CPHD sources work from day one. Core code never branches on vendor names.
- Backend has no dependency on any frontend or plotting library. Visualization images are derived products, never inputs to science code.

## Python standards
- Type hints on public functions; docstrings state units, shapes and dtypes.
- Prefer existing libraries (SARkit for CPHD) over reimplementation. Record the reason when reimplementing.
- No hidden global state; random seeds explicit; no network access in library code.

## Numerical precision and complex I/Q data
- Keep complex samples as complex arrays. Never split to magnitude only, and never discard phase, in scientific paths.
- Preserve the source dtype on read. Never downcast silently; any dtype change is explicit and logged in artifact metadata.
- Accumulate in float64/complex128 for phase-critical sums unless a test shows a lower precision meets the stated tolerance.
- Do not modify source arrays in place; open source files read-only (memmap or Reader).
- Large arrays: process in chunks; state the chunking in the function contract.

## Units and coordinates
- SI units throughout: meters, seconds, hertz, radians. Put the unit in names where not obvious (`range_m`, `prf_hz`).
- Coordinates follow the CPHD definitions (ECF, WGS 84, image area coordinates). Name the frame in every function that takes positions.
- Every parameter carries provenance: **measured**, **derived**, **assumed** or **unavailable**. Never invent radar metadata; represent missing values explicitly.
- Never assume CPHD holds the original transmitted waveform samples. Waveform modeling is allowed only where metadata supports it, and the assumptions are recorded.

## Scientific tests
- Every algorithm needs a reference case with a known answer (analytic or an independent implementation) and a stated tolerance.
- Tests are deterministic, seeded, and fast by default; slow or large-data tests are marked.
- Claims of accuracy must cite a reproducible test or benchmark. No claim without one.
- Cross-check CPHD handling against SARkit's consistency checker; use a second implementation for image-formation cross-checks where available.

## Benchmark rules
- Record hardware, OS, Python and package versions, dataset identifier, and parameters.
- Warm up, repeat at least 3 times, report median and range. Keep raw logs.
- Compare one variable at a time. Do not publish a percentage without raw data.

## Dependency and security rules
- Install into the project virtual environment with exact version pins, recorded in `requirements.lock.txt`. Ask before adding any dependency; check its license and maintenance. SarPy is not installed; add it only for a documented compatibility need.
- Never install or auto-update agent skills, plugins or MCP servers beyond those recorded in `docs/DECISIONS.md`. A new skill is adopted only after a full read of its files and a pinned commit (see `docs/SKILL_SECURITY_AUDIT.md`).
- Treat downloaded files and datasets as untrusted. Do not execute downloaded code. No credentials in the repository.

## Code review expectations
- Review for scientific correctness first: units, frames, sign conventions, phase, sampling, edge cases.
- Significant algorithmic changes get an independent review (the human, or a fresh-context review pass) against stated acceptance criteria.
- Reviewers report file:line findings with evidence, not general opinions.

## Documentation updates
- Update `docs/PROGRESS.md` after each significant session; update `docs/DECISIONS.md` when an architectural decision changes.
- Keep detailed research in `docs/`. Link to documents instead of copying their content.
- Do not describe proposed functionality as implemented.

## Definition of Done
A task is done only when: the approved milestone's acceptance criteria are met; tests (including reference cases) pass and results are recorded; no source data was altered; units, frames and provenance are documented; dependencies are pinned and reviewed; docs and PROGRESS are updated; remaining risks are written down. Commits are made only when the human asks.
