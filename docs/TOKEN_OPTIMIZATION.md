# Token Optimization

Verified: 2026-11-12. Claude Code claims come from the official docs ([costs](https://code.claude.com/docs/en/costs.md), [skills](https://code.claude.com/docs/en/skills.md), [sub-agents](https://code.claude.com/docs/en/sub-agents.md), [memory](https://code.claude.com/docs/en/memory.md)). Codex claims come from [skills](https://developers.openai.com/codex/skills), [subagents](https://developers.openai.com/codex/subagents) and [AGENTS.md](https://developers.openai.com/codex/guides/agents-md). No savings percentage below is measured on this project. Benchmark design: [Benchmark protocol](#benchmark-protocol).

Related: [MULTI_AGENT_ARCHITECTURE](MULTI_AGENT_ARCHITECTURE.md) · [RECOMMENDED_STACK](RECOMMENDED_STACK.md)

## The 14 techniques

| # | Technique | Built in? | Evidence | Effect and tradeoff |
|---|---|---|---|---|
| 1 | Minimal CLAUDE.md | Built in | Docs: loaded every session; keep under 200 lines; move workflow detail to skills | Lowers per-turn input. Cost is cached after the first turn, so the benefit is mostly context-window space and cache-write size. |
| 2 | On-demand skills | Built in | Docs: skills load when invoked; `disable-model-invocation: true` keeps one out of the model's reach | Each skill still adds its name and description to every session (description plus `when_to_use` capped at 1,536 characters). Codex caps its skill list at 2% of the context window. |
| 3 | Progressive disclosure | Built in (Claude Code and Codex) | Both docs describe name and description first, full SKILL.md on use | Put long references in separate files that SKILL.md links to. |
| 4 | Subagent context isolation | Built in | Docs: verbose output stays in the subagent, only a summary returns | Protects the main context. **Does not cut total tokens**: the docs say subagent requests still draw on your usage. Explore and Plan skip CLAUDE.md and git status to stay cheap. |
| 5 | Model selection and routing | Built in, manual | Docs: Sonnet for most coding, Opus for complex reasoning, `model: haiku` for simple subagents; subagents inherit the session model unless set; `CLAUDE_CODE_SUBAGENT_MODEL` forces one. Codex subagents also inherit unless configured. | No automatic routing. Cheaper models risk missed bugs; measure on our tasks. |
| 6 | Prompt caching | Built in, automatic | Docs: Claude Code uses prompt caching for repeated content | Cuts price, not context size. Changing CLAUDE.md or skills mid-session can break cache reuse (unverified on our setup). |
| 7 | Context compaction | Built in | Docs: auto-compaction, `/compact <focus>`, "Compact instructions" section in CLAUDE.md | Cheap. Loses detail; keep durable state in files. |
| 8 | Persistent documentation / memory | Built in | CLAUDE.md, auto memory, `@path` imports | Docs we write ourselves cost nothing to maintain beyond edits. |
| 9 | Efficient repo search | Built in + optional external | Docs: code-intelligence plugins give symbol navigation; Explore subagent for searches | Graphify is the external option; no independent evidence it helps (see below). |
| 10 | Avoid unnecessary file reads | Practice | Docs: "write specific prompts", name files | Free. |
| 11 | Avoid repeated tool calls | Practice + hooks | Docs show a PreToolUse hook that trims test output to the last 100 lines | Hook is our own code, so it is auditable. |
| 12 | Concise output contracts | Practice | Define a fixed result schema for each subagent | Free; only binds subagents we write. |
| 13 | Deterministic validation scripts | Practice | Not a vendor claim | Replaces a model review with a pass/fail command. Highest expected value, unmeasured. |
| 14 | Git checkpoints, resumable tasks | Practice | `/resume`, `/rename`, git | Keeps `/clear` cheap because state is on disk. |

Also in the docs: `/usage` and the status line to watch consumption; `/effort` to lower extended thinking, which is billed as output; disable unused MCP servers; prefer CLI tools over MCP servers.

## Do more agents or skills save tokens?
- Claude Code docs: agent teams "use approximately 7x more tokens than standard sessions" in plan mode, and recommend small teams on Sonnet. Agent teams are off by default.
- Subagent descriptions count against context; the docs warn when custom subagent descriptions exceed 15,000 tokens.
- Codex subagents are spawned when asked (or proactively only at the Ultra setting), per its docs.
- Conclusion: adding agents or skills increases cost unless each one replaces more tokens than it loads. That has to be measured.

## Candidate claims

| Claim | Class | Source |
|---|---|---|
| Caveman: 65% output reduction | Author-reported earlier; **now disclaimed by the author's own page** | [HONEST-NUMBERS.md](https://github.com/JuliusBrussee/caveman/blob/main/docs/HONEST-NUMBERS.md) |
| Caveman: median 3% (default), 35% (ultracave), 9% (megacave) output reduction vs an "Answer concisely" control | Author-reported, n=10, single run, output length only | same page |
| Caveman: 0% input reduction; input cost added "not measured yet" | Author-reported | same page |
| Caveman compress: 33.2% input reduction over 5 memory-file fixtures | Author-reported | same page |
| Caveman net-negative on terse coding Q&A | User issue cited by the author | same page (issue #145) |
| Caveman 8.5% / 12% measured (JetBrains / blogger) | Independent, from search summaries, not re-read | [JetBrains](https://blog.jetbrains.com/ai/2026/07/speak-to-ai-agents-like-cavemen-tosave-tokens/) |
| Graphify: 82.0% vs 70.8% key-fact coverage on ERPNext (n=6), memory benchmarks on LOCOMO/LongMemEval | Author-reported, own harness | [BENCHMARKS.md](https://github.com/Graphify-Labs/graphify/blob/v8/BENCHMARKS.md) |
| Graphify: token reduction on our code | Unverified; the benchmark measures answer coverage, not tokens | n/a |
| Superpowers: any token saving | Unverified. The repo ships `tests/claude-code/analyze-token-usage.py`, which we could reuse for measuring. | repo |

## Estimated overhead of candidates (estimates, bytes/4)
- Superpowers hook injects `using-superpowers/SKILL.md` (3,192 bytes, roughly 800 tokens) at every startup, clear and compact. Add 14 skill descriptions. Individual skills run 3 to 20 KB when invoked (subagent-driven-development 19.7 KB, executing-plans 18.4 KB).
- Graphify's always-on CLAUDE.md block is about 1.2 KB (roughly 300 tokens) plus a PreToolUse hook on every search.
- Caveman: four hooks, with a per-prompt `node` process; added input tokens unmeasured by the author.
Treat these as estimates until the benchmark below counts real tokens.

## Caveman experiment (approved 2026-11-12, limited)
- Form: vendored `SKILL.md` only, manual `/caveman`, no hooks; see [DECISIONS](DECISIONS.md) D-012.
- Method: run the benchmark tasks below with and without `/caveman`, same model and settings, at least 3 runs per cell.
- Measure: output tokens, total cost, and correctness (hidden tests, plus a check that no negation or number was lost in the replies).
- Keep it only if the measured total-cost saving is clear and quality is unchanged. Otherwise remove the folder.
- Observation only (not a result): one trivial headless prompt in this project cost about $0.07 to $0.08 with Superpowers enabled (cache creation 16,000 to 18,000 tokens plus cache reads). No baseline without Superpowers was measured, so this is not an overhead estimate.

## Benchmark protocol
Do not run yet. Goal: compare conditions on the same tasks.

**Conditions:** A baseline (lean CLAUDE.md only); B baseline + project TDD/verification checklist; C B + vendored Superpowers skills; D B + Graphify (AST-only, no hook); E B + Caveman. One variable at a time.

**Tasks (5 to 8, fixed in advance):** metadata extraction from a CPHD header; fix a seeded bug; write tests for a pure-numpy function; refactor an FFT helper; answer a cross-file question; a review of a seeded-defect diff. Each has hidden tests and a rubric.

**Controls:** fresh clone per run, pinned model and CLI version, same effort setting, at least 3 repetitions per cell, cold and warm cache recorded separately, order randomized.

**Collected automatically:**
- Input, output, cache-read and cache-write tokens per call, from `claude -p --output-format json` (usage fields) or the session transcript. Field names need confirming against the installed version.
- Tool-call counts and names from the transcript.
- Cost: from the reported cost field if present, otherwise tokens times the price list.
- Wall time (script timestamps).
- Hidden-test pass rate (pytest exit code and counts).

**Recorded manually:** rework turns (human corrections needed), reviewer severity rating on the review task, and whether the output followed the contract.

**Reporting:** medians and ranges, correctness first, cost second. No percentage is published without raw logs committed alongside.

**Codex runs:** dropped (D-007).

## Unknowns
- Resolved: Claude Code reads AGENTS.md only when no CLAUDE.md exists, so CLAUDE.md imports it with `@AGENTS.md` (the import expands into context, so AGENTS.md size counts toward every session). Keep AGENTS.md short.
- Cache behavior with hooks that inject context.
- Codex Windows sandbox maturity (docs list a Windows sandbox and WSL; not tested).
