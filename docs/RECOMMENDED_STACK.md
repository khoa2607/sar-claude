# Recommended Skill and Tool Stack

Verified: 2026-11-12. **Update 2026-11-12:** the user approved a stack that differs from the original advice; see [DECISIONS](DECISIONS.md) D-007 to D-012. Installed: SARkit 1.12.0, Superpowers 7.0.2 (project-scope plugin, full plugin with its SessionStart hook), Caveman SKILL.md only (manual). Not used: Codex, SarPy, OpenClaw, Graphiti, Graphify. Evidence behind each row is in [SKILLS_RESEARCH](SKILLS_RESEARCH.md), [OPEN_SOURCE_REUSE](OPEN_SOURCE_REUSE.md), [TOKEN_OPTIMIZATION](TOKEN_OPTIMIZATION.md) and [SKILL_SECURITY_AUDIT](SKILL_SECURITY_AUDIT.md). Rows below describe the original recommendation; the installed set is listed above. Status values: **Verified** (primary source read), **Partial** (primary source sampled), **Unverified**.

Principle: built-in features and deterministic tools first; libraries second; third-party skills last, and vendored, not installed from a registry.

## Tier 1: Essential before development starts

| Item | Why | Why built-in or existing is insufficient | Extra tokens? | Install? | Claude + Codex? | Status |
|---|---|---|---|---|---|---|
| Lean `CLAUDE.md` (target under about 60 lines) that points to `AGENTS.md` and docs | Persistent rules with minimal context | n/a (it is the built-in) | Yes, small, every session | No | Yes: Claude reads AGENTS.md per docs; Codex reads it natively | Verified (docs) |
| Shared `AGENTS.md` (well under Codex's 32 KiB cap) | One instruction source for both tools | n/a | Small | No | Yes | Verified (docs) |
| Session hygiene: `/clear` between tasks, `/compact` focus line, `/usage`, per-subagent `model:` | Cheapest savings available | Built in | None | No | Claude only (Codex has its own) | Verified (docs) |
| Deterministic scripts: CPHD check, pytest runner, image comparison | Replace model review with pass/fail | No skill can replace a test | None unless output is long (trim it) | No third-party | Yes | Design only |
| `STATE.md` plus git checkpoints | Resume tasks after `/clear` | Built-in memory is not task state | Small | No | Yes | Design only |
| SARkit (CPHD 1.0.1/1.1.0 reader, XML objects, ~98 consistency checks) as a pinned dependency in a Python 3.12+ venv; SarPy only if a non-CPHD extra is needed (its CPHD code is deprecated) | Existing CPHD I/O and checks | Writing a CPHD parser is wasteful | None (library, not context) | pip/uv, Phase 0B | Yes | Verified in source (not executed) |
| FastSAR and torchbp as **independent cross-check references** (Codex-based review dropped per D-007), in a separate environment | Second implementation for image-formation validation | No local reference otherwise | None | Separate venv or WSL2, Phase 0B+ | Yes | Partial (README and manifests; FastSAR is alpha) |

## Tier 2: On-demand (adopt when the work begins)

| Item | Trigger | Why / why not built-in | Tokens | Install | Both tools | Status |
|---|---|---|---|---|---|---|
| Project-written TDD / verification-before-completion skills, **derived from** Superpowers' `test-driven-development`, `systematic-debugging`, `verification-before-completion` (MIT) | First algorithm code | Cheaper than the whole plugin; adapt to numeric tolerances | Description only until invoked | Copy reviewed files into `.claude/skills` and `.agents/skills` | Yes (same SKILL.md format) | Partial: bodies not yet read |
| `sarkit-processing`, `sarkit-assurance` | SICD post-processing, assurance checks | Reuse instead of writing | None | pip | Yes | Partial |
| NVIDIA `compute-sanitizer-diagnose-cuda-bugs` | First CUDA kernel | Router to the right sanitizer tool | About 3.5k tokens when invoked (14 KB, estimate) | Copy folder | Yes | Partial |
| K-Dense `statistical-analysis`, `literature-review`, `citation-management` (cherry-picked) | Validation write-up, literature phase | Domain method checklists | Description until invoked | Copy folders after reading scripts | Yes | Partial |
| Research subagent (Sonnet) and Codex reviewer | After first milestone | See [MULTI_AGENT_ARCHITECTURE](MULTI_AGENT_ARCHITECTURE.md) | Separate contexts | Config files only | Different formats | Verified (docs) |
| Profilers: cProfile / py-spy; Nsight tools | Performance phase | Deterministic tools | None | Standard tools | Yes | Not researched |

## Tier 3: Optional (needs evidence, setup or benchmarking)

| Item | Condition to try | Status |
|---|---|---|
| Graphify, AST-only, no PreToolUse hook, no semantic extraction | Codebase exceeds what Explore and grep handle cheaply; run the A/B first | Partial; benchmark is author-run and measures coverage, not tokens |
| mohitmishra786 `cuda-profiling` / profiler skills | GPU phase; read every file first | Partial |
| Claude Code code-intelligence plugin for Python | If grep-heavy exploration shows up in transcripts | Unverified for Python |
| Caveman compress for large memory files | Only if memory files grow large | Author-reported 33.2% on 5 fixtures |
| torchbp / osubp as backprojection references | Algorithm design | Unverified |

## Tier 4: Reject or defer

| Item | Reason |
|---|---|
| Caveman runtime (hooks, response style) | Author's own table: 3% median output reduction vs "answer concisely"; 0% input reduction; four hooks including one per prompt; repo scope far beyond a style skill. Add a one-line brevity instruction to CLAUDE.md instead. |
| Superpowers plugin as installed (hook + mandatory skill rule + brainstorming + visual companion) | Injects about 800 tokens each session start, pushes invocation at a 1% match threshold, requires brainstorming before creative work, adds 14 descriptions. Vendor individual skills instead. |
| OpenClaw, ClawHub skills | Documented malicious-skill campaigns (secondary sources). |
| Graphiti / Zep | Needs a graph database service; heavy for a repo this size; not inspected. |
| Whole K-Dense collection | 177 skills, mostly life science; unrelated descriptions would load into context. |
| K-Dense `optimize-for-gpu` | RAPIDS needs Linux/WSL2; revisit only if we move to WSL2. |
| Agent teams | Roughly 7x tokens per official docs; disabled by default. |
