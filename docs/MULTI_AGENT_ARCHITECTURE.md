# Multi-Agent Architecture

**Update 2026-11-12:** the user decided not to use Codex (decision D-007). Codex-specific rows below are historical; independent review is by the user or a fresh-context pass. Verified: 2026-11-12 against the official [Claude Code sub-agents](https://code.claude.com/docs/en/sub-agents.md) and [Codex subagents](https://developers.openai.com/codex/subagents) docs. Cost facts are in [TOKEN_OPTIMIZATION](TOKEN_OPTIMIZATION.md).

## Platform facts (verified in docs)
- Claude Code subagents: markdown files with frontmatter (tools, `model`, permissions). The model is inherited unless set per agent or with `CLAUDE_CODE_SUBAGENT_MODEL`. Explore and Plan skip CLAUDE.md. Subagent descriptions count against context.
- Codex custom agents: TOML files in `.codex/agents/` (project) or `~/.codex/agents/` (personal), with their own model and instructions. Codex skills live in `.agents/skills`. `AGENTS.md` is capped at 32 KiB by default.
- Both tools use the same SKILL.md format. Subagent and config formats differ, so they need separate files.
- Claude Code agent teams cost roughly 7x a standard session in plan mode (official figure) and are disabled by default.

## Shared instructions and Windows (verified in docs, 2026-11-12)
- **Claude Code and AGENTS.md:** with both files present, Claude reads **only CLAUDE.md** by default; AGENTS.md is read directly only when no CLAUDE.md exists (requires v2.1.277 or later). To share rules, `CLAUDE.md` must contain `@AGENTS.md`. This repository does that (decision D-002). Source: [memory docs](https://code.claude.com/docs/en/memory.md).
- **Codex and AGENTS.md:** reads `AGENTS.override.md` or `AGENTS.md` from the Codex home, then walks from the project root down to the working directory; stops at 32 KiB (`project_doc_max_bytes`). Source: [AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md).
- **Claude Code on Windows:** native Windows is supported (Windows 10 1809+). Git for Windows is recommended so the Bash tool works; otherwise PowerShell is the shell tool. Source: [setup docs](https://code.claude.com/docs/en/setup.md).
- **Codex on Windows:** three sandbox implementations: `mxc` (recommended on compatible devices, no admin setup), `elevated` (legacy fallback, needs admin-approved setup) and `unelevated` (weaker network isolation). `prefer_mxc = true` in `config.toml` opts in for CLI use. Source: [Codex Windows docs](https://developers.openai.com/codex/windows). Not tested on this machine.

## Role decisions

| Role | Form | Reason |
|---|---|---|
| Main coordinator | Main session (Claude Code) | Holds the plan and decisions. |
| CPHD and metadata specialist | **Deterministic tool** (script using SARkit checks) plus a short reference doc | Parsing and validation are rule-based; a model adds cost without adding certainty. |
| Numerical validation | **Deterministic tool** (pytest with tolerances, reference-image metrics) | Pass/fail output replaces model review. |
| Python/C++ performance | **Skill/checklist plus profiler scripts** (cProfile, py-spy, Nsight when GPU work starts) | Needed occasionally, no standing context. |
| Scientific research | **On-demand subagent** (Sonnet), literature passes only | Reading papers is verbose; isolation protects the main context. |
| SAR algorithm reviewer | **On-demand subagent or Codex review** on the strongest model, at milestones only | High-stakes reasoning, low frequency. |
| Independent code reviewer | **Codex (different model family) invoked on demand** over a diff | A second family finds different bugs. Value is plausible but unmeasured. |

## Minimal initial architecture
1. One Claude Code main session with a lean CLAUDE.md that imports a shared `AGENTS.md`.
2. Deterministic scripts: `check_cphd`, `run_tests`, `compare_images`.
3. Zero custom subagents on day one. Use built-in Explore for broad searches.
4. Add a research subagent and a reviewer only after the first milestone shows a need.
5. Codex used as a read-only reviewer: it receives a diff plus acceptance criteria and returns the contract below.

## Subagent contract (all subagents)
- Narrow task, explicit acceptance criteria, minimal tools (read-only unless writing is the task).
- Output as a short structured block: `verdict`, `findings[]` (file:line, severity, one-line evidence), `commands_run[]`, `unknowns[]`. No prose beyond 200 words.
- No network unless the task is a literature search.

## Cheaper vs stronger models
Doc guidance: Sonnet for most coding, Opus for complex reasoning, Haiku for simple subagents. Practitioner reports say Haiku misses subtle bugs in review (unverified). Rule for now: Sonnet default, strongest model for the SAR algorithm review, Haiku only for mechanical lookups. Confirm with the benchmark.

## Unresolved
- Whether the Codex Windows sandbox works on this machine, and the exact CLI flags for a read-only review run (decision O-004).
- How Claude Code and Codex share state beyond files (assume files only).
