# SAR-SIL — Synthetic Aperture Radar Software-in-the-Loop Research Platform

@AGENTS.md

(The import above is required: Claude Code ignores AGENTS.md when a CLAUDE.md exists. Shared engineering rules live there; this file holds only Claude-specific instructions.)

## Objective
Build a high-performance, backend-only, multi-source CPHD processing and SAR image formation platform, with validated radar signal modeling where metadata supports it. Support reproducible signal-quality experiments and large-scale SAR data processing.

## Non-negotiable principles
- Scientific correctness before optimization.
- No invented radar metadata; label parameters measured, derived, assumed or unavailable.
- Preserve phase, sampling information, geometry and units.
- Never assume CPHD contains the original transmitted waveform samples.
- Never modify source CPHD data (`cphd/` is read-only).
- Design for multiple CPHD sources from day one.
- Validate against reference cases; no accuracy claims without reproducible tests.
- Keep scientific data separate from visualization images; backend independent of any frontend.

## Workflow
Research → Plan → Implement → Test → Review → Document.
- Work on one approved milestone at a time (see `docs/PROGRESS.md`). Record scope changes in `docs/DECISIONS.md` before acting on them.
- Prefer deterministic tests over discussion. Keep changes focused.
- Codex is not used (decision D-007). Independent review of algorithm changes is done by the user or a fresh-context review pass.
- Approved tooling only: Superpowers plugin (planning, TDD, debugging, verification) and the manual `/caveman` skill. Do not use Codex. Never install other skills, plugins or MCP servers without review and approval.
- Do not commit unless asked. Git is initialized (branch `main`), no commits yet.
- Environment: use `.venv` (Python 3.13, `uv`); dependencies pinned in `requirements.lock.txt`. Ask before adding packages.

## Session start
1. This file and `AGENTS.md` load automatically.
2. Read `docs/PROGRESS.md`.
3. Read only the docs relevant to the task (index below).
4. Run `git status` before making changes.
5. State the active approved milestone before changing anything.

## Session end (after significant work)
Update `docs/PROGRESS.md` (done, in progress, tests run and results, blockers, next action) and `docs/DECISIONS.md` if architecture changed.

## Token efficiency
- Search with Grep/Glob before reading large files; read only what the task needs.
- Keep replies short; do not re-summarize the project.
- Keep research in `docs/`, not here. Use subagents only when isolation clearly pays; no agent teams.
- Caveman is an experiment: manual `/caveman` only, never in files, commits or docs. Measure before keeping (see `docs/TOKEN_OPTIMIZATION.md`).
- Use `/clear` between unrelated tasks; state lives in PROGRESS.md.

## Documentation map
- Status: `docs/PROGRESS.md` · Decisions: `docs/DECISIONS.md` · Roadmap: `docs/DEVELOPMENT_ROADMAP.md`
- Phase 0A research: `docs/PHASE_0A_SUMMARY.md` (index), `docs/OPEN_SOURCE_REUSE.md`, `docs/RECOMMENDED_STACK.md`, `docs/SKILLS_RESEARCH.md`, `docs/SKILL_SECURITY_AUDIT.md`, `docs/TOKEN_OPTIMIZATION.md`, `docs/MULTI_AGENT_ARCHITECTURE.md`
- Planned, not yet written: `docs/ARCHITECTURE.md`, `docs/VALIDATION.md`, `docs/TECHNOLOGY.md`
