# Progress

Last verification: 2026-11-12 (70 tests passing).

**Current phase:** M1 finalized (accepted with documented limitations). M2 is planned only ([M2_PLAN](M2_PLAN.md)). No image formation exists.

## Completed
- Phase 0A research and governance ([PHASE_0A_SUMMARY](PHASE_0A_SUMMARY.md)).
- Environment, SARkit 1.12.0, Superpowers 7.0.2, manual Caveman skill (D-007 to D-012).
- Dataset DS-001 (Umbra-05 CPHD 1.1.0, 588 MiB) acquired and validated: [DATASETS](DATASETS.md). Matching SICD not downloaded.
- M1 CPHD inspector: [M1_INSPECTOR](M1_INSPECTOR.md). Finalization added capability assessment, support arrays, PVP availability, declared-vs-recomputed reference geometry, SIGNAL status handling, configurable nonuniform threshold, performance measurement and deterministic JSON.

## M1 verification (2026-11-12)
- `python -m pytest -q`: **70 passed** (about 10 s). Includes 16 synthetic multi-channel/negative tests with known geometry and 21 real-data tests.
- Mutation check: breaking the SIGNAL mask made 14 tests fail; code restored and 70 pass again.
- CPHD SHA-256 `31bcefb4...b55790` unchanged; size and mtime unchanged.
- Real-data run (all 8,780 vectors): consistency default 97 checks, 78 passed, 0 failed, 19 inapplicable; thorough 80/0/17. Inspection 0.49 s, heap peak 10.5 MiB; full scan 1.96 s, heap peak 317 MiB at the 256 MiB budget.
- Not verified: other providers, real multi-channel files, TOA-domain, compressed signals, the standard text for SIGNAL values above 1.
- The Superpowers skills were not loaded in the sessions that built M1 (`Unknown skill` when invoked), so deterministic verification was used instead.

## Environment verification (2026-11-12)
- `import sarkit, sarkit.cphd, sarkit.verification` succeeds in `.venv` (isolated mode); `Reader`, `Writer`, `Metadata`, `compute_t_ref`, `CphdConsistency` present; `cphdcheck.exe` installed (not run: no CPHD file).
- `claude plugin list`: superpowers@superpowers-dev 7.0.2, project scope, enabled.
- Headless Claude Code session lists all 15 `superpowers:*` skills.
- `/caveman status` in a headless session returned `Caveman mode: caveman (not tracked by this host)`; the model does not see the skill unless the user invokes it (expected with `disable-model-invocation`).
- Superpowers hook behavior on Windows beyond session start working is unverified.

## In progress
- None.

## Not started (do not treat as implemented)
Image formation, GPU code, artifact storage, benchmark harness, second-source adapter, M2 SICD comparison.

## Known blockers
- GPU: the earlier RTX 2080 statement was superseded; the M1 prompt and `nvidia-smi` both say RTX 3060, 12 GB.
- The NGA CPHD standard text was not read; SIGNAL values above 1 are unconfirmed.
- Unresolved research items: [PHASE_0A_SUMMARY](PHASE_0A_SUMMARY.md#blockers-and-unknowns).
- Superpowers' `using-superpowers` rule and brainstorming-first flow may add tokens to every task; no baseline measured yet.

## Next approved task
**None.** Proposed: M2 per [M2_PLAN](M2_PLAN.md) (SICD reference and formation preparation), after your approval. M3 (artifact store) and the second-source adapter remain alternatives.

## Tests run
46 passed (2026-11-12), see M1 verification.

## Session log
- 2026-11-12: Phase 0A research, gap closure, governance files.
- 2026-11-12: Environment setup and verification.
- 2026-11-12: M1 inspector implemented with tests.
- 2026-11-12: M1 finalized (70 tests, mutation check), M2 plan written, committed as `feat: implement validated CPHD inspector`.
- 2026-11-12: Acquired DS-001 (CPHD + metadata JSON) into `cphd/` (git-ignored); validated with SARkit. Uncommitted: docs only.

## How to use this file
Start of session: read this file, then only the docs the task needs. End of significant session: update every section above, add a session log line, list tests run and results, and name the next action.
