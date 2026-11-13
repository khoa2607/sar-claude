# Progress

Last verification: 2026-11-12 (documents re-read and cross-checked; no code exists to test).

**Current phase:** Phase 0B-setup complete (environment and approved tooling). No SAR code exists. Awaiting approval of the next milestone.

## Completed
- Phase 0A research and governance ([PHASE_0A_SUMMARY](PHASE_0A_SUMMARY.md)).
- Environment setup (2026-11-12), see [DECISIONS](DECISIONS.md) D-007 to D-012:
  - `.venv` created with uv 0.13.7 on existing CPython 3.13.14 (no system-level install was needed).
  - SARkit 1.12.0 installed; pins in `requirements.lock.txt`. SarPy not installed.
  - Git initialized on `main`; `.gitignore` excludes `.venv/` and dataset files. No commits.
  - Superpowers 7.0.2 installed (project scope) from `obra/superpowers`.
  - Caveman: one vendored skill file, manual `/caveman` only, no hooks.

## Verification results (2026-11-12)
- `import sarkit, sarkit.cphd, sarkit.verification` succeeds in `.venv` (isolated mode); `Reader`, `Writer`, `Metadata`, `compute_t_ref`, `CphdConsistency` present; `cphdcheck.exe` installed (not run: no CPHD file).
- `claude plugin list`: superpowers@superpowers-dev 7.0.2, project scope, enabled.
- Headless Claude Code session lists all 15 `superpowers:*` skills.
- `/caveman status` in a headless session returned `Caveman mode: caveman (not tracked by this host)`; the model does not see the skill unless the user invokes it (expected with `disable-model-invocation`).
- Not verified: SARkit against a real CPHD file; Superpowers hook behavior on Windows beyond session start working; no pytest suite exists.

## In progress
- None.

## Not started (do not treat as implemented)
All source code, tests, scripts, benchmark harness, artifact storage.

## Known blockers
- `cphd/` is empty: no dataset for M1. Public candidates (Umbra, Capella open buckets) need per-collect license confirmation.
- Unresolved research items: [PHASE_0A_SUMMARY](PHASE_0A_SUMMARY.md#blockers-and-unknowns).
- Superpowers' `using-superpowers` rule and brainstorming-first flow may add tokens to every task; no baseline measured yet.

## Next approved task
**None.** Proposed: M1 (read-only CPHD inspector) in [DEVELOPMENT_ROADMAP](DEVELOPMENT_ROADMAP.md), once a CPHD file is available and the user approves.

## Tests run
None (no test suite). Environment checks listed above.

## Session log
- 2026-11-12: Phase 0A research, gap closure, governance files.
- 2026-11-12: Environment setup and verification. No commits.

## How to use this file
Start of session: read this file, then only the docs the task needs. End of significant session: update every section above, add a session log line, list tests run and results, and name the next action.
