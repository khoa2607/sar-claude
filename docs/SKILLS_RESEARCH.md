# Agent Skills and Memory Tools Research

Verified: 2026-11-12. "Primary" means the repository's own files were read; "secondary" means a search summary only. Security detail is in [SKILL_SECURITY_AUDIT](SKILL_SECURITY_AUDIT.md); decisions are in [RECOMMENDED_STACK](RECOMMENDED_STACK.md).

## Verified candidates

| Tool | Canonical repo | License | Version / last push | Evidence | What it is |
|---|---|---|---|---|---|
| Superpowers | [obra/superpowers](https://github.com/obra/superpowers) | MIT | 7.0.2 / 2026-11-03 | Primary | 14 workflow skills (brainstorming, TDD, debugging, plans, subagent-driven development, code review, verification). Manifests exist for Claude Code, Codex, Cursor and others. |
| Graphify | [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) | Apache-2.0 (+MIT file) | 0.9.108 / 2026-11-12 | Primary (partial) | Builds a code/doc knowledge graph (tree-sitter AST, no LLM needed for code). CLI queries replace grep. Optional MCP server. |
| Caveman | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) | Apache-2.0 since 3.0.0 | 4.1.0 / 2026-11-13 | Primary (partial) | Terse-output skill, now bundled with an engine, proxy, browser tool and a hosted-service tie-in. **First-pass report said MIT; that is wrong for current versions.** |
| K-Dense scientific-agent-skills | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills) | MIT | 2026-11-09 | Primary (2 skills) | 177 SKILL.md files, mostly life-science. Relevant: statistical-analysis, literature-review, peer-review, citation-management, scientific-writing, optimize-for-gpu. |
| NVIDIA skills | [NVIDIA/skills](https://github.com/NVIDIA/skills) | Apache-2.0 | 2026-11-12 | Primary (1 skill) | 452 skills. Relevant: `compute-sanitizer-diagnose-cuda-bugs`, `warp-*`. No Nsight Systems/Compute profiling skill found in the file list (only `deepstream-profile-pipeline`, unrelated). |
| low-level-dev-skills | [mohitmishra786/low-level-dev-skills](https://github.com/mohitmishra786/low-level-dev-skills) | MIT | 2026-06-27 | Primary (1 skill) | Single-author set: `cuda-profiling`, `cuda-debugging`, `simd-intrinsics`, `profilers/*` (flamegraphs, hardware counters, heaptrack, VTune, perf). |

## Not verified at primary level
- **Graphiti / Zep** ([getzep/graphiti](https://github.com/getzep/graphiti)): Apache-2.0 per search summary. Requires a graph database. Zep's community edition is reported discontinued. Paper: [arXiv 2501.13956](https://arxiv.org/abs/2501.13956v1).
- **OpenClaw / ClawHub**: only secondary reports of malicious skills ([The Hacker News](https://thehackernews.com/2026/02/researchers-find-341-malicious-clawhub.html), [arXiv 2602.06547](https://arxiv.org/pdf/2602.06547v2)).

## Numerical, profiling and GPU libraries (repository metadata checked 2026-11-12; not audited)
Prefer these deterministic tools over skills.

| Tool | License (GitHub) | Last push | Use |
|---|---|---|---|
| numba | BSD-2-Clause | 2026-11-12 | JIT for CPU kernels |
| CuPy | MIT | 2026-11-05 | GPU NumPy/SciPy-compatible arrays, cuFFT |
| NVIDIA cuda-python | Apache-2.0 | 2026-11-13 | Low-level CUDA access |
| py-spy | MIT | 2026-11-10 | Sampling profiler for Python |
| pyinstrument | BSD-3-Clause | 2026-11-01 | Statistical call-tree profiler |
| line_profiler | GitHub reports NOASSERTION (check file) | 2026-10-18 | Line-level timing |
| pyFFTW | GitHub reports NOASSERTION (check file) | 2025-12-03 | FFTW bindings; less recently updated |

FFTs: `scipy.fft`/`numpy.fft` first; CuPy for GPU. No DSP-specific agent skill was found by name; none appears necessary.
Local hardware: NVIDIA GeForce RTX 3060, 12 GB (via `nvidia-smi`), Python 3.10.11.

## Gaps (searches not yet run)
- C++ optimization skills beyond `simd-intrinsics`.
- Independent review and multi-agent orchestration skills beyond Superpowers.
- Agent memory alternatives beyond Graphify/Graphiti (e.g. mem0, supermemory appear in Graphify's own benchmark but were not assessed).

## Built-in capability that overlaps with skills
Per [Claude Code docs](https://code.claude.com/docs/en/skills.md), custom commands and skills share one mechanism (`.claude/skills/<name>/SKILL.md`). Memory (`CLAUDE.md`, auto memory), subagents, hooks and compaction are built in. See [TOKEN_OPTIMIZATION](TOKEN_OPTIMIZATION.md).

## Overlap map
- Test-driven development, debugging, verification, code review: Superpowers only; a short project-written checklist can cover the same ground.
- Code navigation: Graphify vs Claude's built-in Explore subagent vs the code-intelligence plugins mentioned in the costs docs.
- Output style: Caveman vs a one-line "answer concisely" instruction in CLAUDE.md. Caveman's own page measures against that control (see [TOKEN_OPTIMIZATION](TOKEN_OPTIMIZATION.md)).
