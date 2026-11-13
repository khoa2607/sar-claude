# Phase 0A Summary

Verified: 2026-11-12. Status: **complete for architecture decisions; minor research gaps remain (see Blockers)**. Gap-closing pass done 2026-11-12: SARkit supports CPHD 1.0.1 and 1.1.0; SarPy's CPHD is deprecated in favor of SARkit; FastSAR (alpha, MIT) already forms images from CPHD; Claude Code needs `@AGENTS.md` in CLAUDE.md; Codex has three Windows sandboxes. The approved stack was set up the same day ([PROGRESS](PROGRESS.md)). Governance files and the roadmap are in [PROGRESS](PROGRESS.md), [DECISIONS](DECISIONS.md) and [DEVELOPMENT_ROADMAP](DEVELOPMENT_ROADMAP.md). Details live in the linked documents.

| Document | Content |
|---|---|
| [SKILLS_RESEARCH](SKILLS_RESEARCH.md) | Candidate skills and memory tools, canonical repos, gaps |
| [OPEN_SOURCE_REUSE](OPEN_SOURCE_REUSE.md) | SAR libraries: reuse / adapt / build |
| [TOKEN_OPTIMIZATION](TOKEN_OPTIMIZATION.md) | 14 techniques, claim classification, benchmark protocol |
| [MULTI_AGENT_ARCHITECTURE](MULTI_AGENT_ARCHITECTURE.md) | Role decisions and minimal architecture |
| [SKILL_SECURITY_AUDIT](SKILL_SECURITY_AUDIT.md) | What was inspected, classification |
| [RECOMMENDED_STACK](RECOMMENDED_STACK.md) | Four tiers |

## Answers to the nine questions

1. **Install first?** No third-party skills. Start with built-ins (lean CLAUDE.md, shared AGENTS.md, `/clear`, `/compact`, subagent `model:`), deterministic scripts, and SARkit + SarPy as pinned libraries. *Evidence: official docs verified; libraries by manifest only.*
2. **On-demand?** Project TDD/verification skills derived from Superpowers, NVIDIA compute-sanitizer, K-Dense statistics and literature skills (cherry-picked, copied after review), sarkit-processing/assurance. *Evidence: partial; bodies still to be read.*
3. **Is Graphify worth using?** Not yet. It is a heavy install (about 30 grammar dependencies), its always-on rule and hook change search behavior, and its benchmark (82.0% vs 70.8% coverage, n=6) measures answers, not tokens. Revisit with the A/B test, AST-only and hookless. *Evidence: author-reported; partial audit.*
4. **Is Caveman or another token-efficiency tool worthwhile?** Not now. The author's own page reports a 3% median output reduction against a plain "answer concisely" control and no input reduction. Output is a small share of spend, and the tool adds hooks. A one-line brevity rule gets most of that for free. *Evidence: author-reported (self-disclaiming) plus independent figures from search summaries.*
5. **OpenClaw, Graphiti, or native?** Native Claude Code capabilities. OpenClaw's registry has documented malicious skills; Graphiti needs a database service. *Evidence: native verified in docs; the others secondary or uninspected.*
6. **Claude Code vs Codex roles?** Claude Code is coordinator and implementer; Codex is an on-demand, read-only independent reviewer of diffs. Share AGENTS.md and SKILL.md; keep separate agent configs. *Evidence: formats verified in docs; review value unmeasured.*
7. **Most cost-efficient workflow?** Plan in the main session, push verification into deterministic scripts, `/clear` between tasks with state in files, Sonnet by default, strongest model only for algorithm review, no agent teams. *Evidence: docs support each piece; combined savings unmeasured.*
8. **Which SAR libraries?** SARkit for CPHD I/O and checks, SarPy as cross-check and for CPHD 0.3, sarkit-processing for SICD tools. Image formation must be built (backprojection references: torchbp, osubp, unverified). *Evidence: manifests and file lists verified; code unaudited.*
9. **Simplest maintainable setup?** Tier 1 in [RECOMMENDED_STACK](RECOMMENDED_STACK.md): two instruction files, a few scripts, two libraries, no plugins.

## Top five recommendations
1. Adopt no third-party plugin yet; use built-ins and deterministic scripts.
2. Use SARkit as the primary CPHD layer with SarPy as a cross-check.
3. Vendor, never install, any skill, after reading every file and pinning the commit.
4. Build image formation ourselves; no reusable CPHD-to-image code was found.
5. Run the A/B benchmark ([TOKEN_OPTIMIZATION](TOKEN_OPTIMIZATION.md#benchmark-protocol)) before adopting Graphify or Caveman.

## Security concerns
- Public skill registries have documented malicious skills (secondary sources).
- Superpowers' visual-brainstorm server loads a remote logo unless telemetry is disabled; its session hook is benign.
- Graphify can send content to a model backend during semantic extraction and installs a PreToolUse hook.
- Caveman runs four hooks including one on every prompt, from a repo with binaries and a hosted-service component.
- Skills may instruct the agent to fetch URLs (K-Dense cites arXiv; Superpowers' diagnostic skill calls the GitHub API).

## Blockers and unknowns
- DSP/numerical, Python-profiling and C++ skills: no primary-source search done; may not exist or be needed.
- ISCE3 license text, pyroSAR and MintPy unchecked; FastSAR claims unverified.
- SARkit's CPHD support is confirmed from source, but no data file was read (`cphd/` is empty) and nothing was executed.
- Python 3.12+ is needed for SARkit; local default is 3.10.11.
- Remaining skill bodies unread (Superpowers TDD/debugging/verification, Graphify hook payload, K-Dense scripts).
- Codex Windows sandbox documented but untested here; review-run flags unverified.
- No token measurements exist; benchmark is designed, not run.

## Next action
Resolve the gaps above with targeted reads (about a dozen files), then start Phase 0B only on your approval.
