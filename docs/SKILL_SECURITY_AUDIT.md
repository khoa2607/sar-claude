# Skill Security Audit (Phase 0A)

Verified: 2026-11-12. Read-only audit: files were downloaded with `curl` into an isolated scratch directory, read or grepped, and never executed or installed. Popularity was not used as evidence.

Related: [RECOMMENDED_STACK](RECOMMENDED_STACK.md) · [SKILLS_RESEARCH](SKILLS_RESEARCH.md) · [PHASE_0A_SUMMARY](PHASE_0A_SUMMARY.md)

## Status after user approval (2026-11-12)
- Superpowers 7.0.2 is installed as a project-scope plugin (user decision, overriding the vendoring advice). Mitigations applied: `SUPERPOWERS_DISABLE_TELEMETRY=1` in `.claude/settings.json`; visual brainstorming companion must stay off. The remaining unread skill bodies are still an open review item.
- The marketplace entry `superpowers-dev` was added at user level (it applies to all projects on this machine); the plugin itself is enabled for this project only.
- Caveman: only `skills/caveman/SKILL.md` (4.7 KB, read in full: plain instructions, no scripts, no network or file actions) was vendored. Upstream INSTALL.md says the CLI telemetry is on by default and sends content-free usage events with IP address, which is why the installer and CLI were not used.

## Classification

| Candidate | Class | Why |
|---|---|---|
| Superpowers **plugin hook** (SessionStart) | Acceptable with restrictions | Fully read; local only |
| Superpowers **individual skills**, vendored copy | Requires further review | Only frontmatter + `using-superpowers` read in full |
| Superpowers **visual brainstorm server** | Reject (do not enable) | Opens a local web server; loads a remote logo from primeradiant.com unless telemetry env var is set |
| Graphify | Requires further review | Too large to audit; hook payload and semantic-extraction path unread |
| Caveman | Requires further review (defer) | 4 hooks incl. one per prompt; 2,118-file repo with binaries and a hosted-service tie-in; mostly unread |
| K-Dense scientific-agent-skills (whole set) | Requires further review | 177 skills, 774 scripts, mostly life-science; 2 skills sampled |
| K-Dense `statistical-analysis` | Requires further review | SKILL.md grepped; `assumption_checks.py` unread |
| K-Dense `optimize-for-gpu` | Reject for now | RAPIDS needs Linux/WSL2; not Windows-native |
| NVIDIA `compute-sanitizer-diagnose-cuda-bugs` | Acceptable with restrictions (provisional) | No scripts in file list; signature file present (not verified); references/evals unread |
| mohitmishra786 `cuda-profiling` | Requires further review | Single-author repo, 441 files; SKILL.md fetched, grepped only |
| SarPy / SARkit / sarkit-processing (libraries) | Acceptable with restrictions | Manifests only; source not audited |
| OpenClaw / ClawHub skills | Reject | Documented malicious-skill campaigns (secondary sources); no primary inspection |
| Graphiti / Zep | Requires further review (defer) | Not inspected at primary level; needs a graph DB service |

## What was actually inspected

**Superpowers** (obra/superpowers, v7.0.2, MIT, last push 2026-11-03)
- Read in full: `hooks/hooks.json`, `hooks/session-start`, `hooks/run-hook.cmd`, `skills/using-superpowers/SKILL.md`, `package.json`, `.claude-plugin/plugin.json`.
- Grepped (network, env, curl/wget, eval, base64, secrets) across `hooks/`, `skills/`, `scripts/`, `.opencode/`, `.pi/`, `.hermes-plugin/`.
- Findings:
  - The hook runs on `startup|clear|compact`. It reads its own `using-superpowers/SKILL.md` and injects it as context. No network, no env secrets.
  - `run-hook.cmd` searches fixed Git-for-Windows locations for bash and exits silently if none is found. It is written with Windows in mind (docs/windows/polyglot-hooks.md exists).
  - `skills/brainstorming/scripts/server.cjs` is a local web server (default 127.0.0.1, per-session key). It references a remote logo URL and honors `SUPERPOWERS_DISABLE_TELEMETRY`, `DISABLE_TELEMETRY` and `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`. It only opens a browser when `BRAINSTORM_OPEN` is set. I did not trace any other outbound call.
  - `diagnosing-superpowers/references/github-issues.md` instructs a `curl` to the GitHub issues API. It is a documented flow, but it is an instruction to the agent to hit the network.
  - Prompt-style concern: `using-superpowers` says a 1% chance a skill applies means you MUST invoke it, and says to invoke it before clarifying questions. That is legitimate by design but pushes more skill loading and more tokens.
- **Not inspected:** bodies of 13 other skills, `.opencode/plugins/superpowers.js`, release/sync scripts, tests.

**Graphify** (Graphify-Labs/graphify, v0.9.108 per `pyproject.toml`, Apache-2.0 with LICENSE-MIT, last push 2026-11-12; `safishamsi/graphify` now redirects here)
- Read: `graphify/always_on/claude-md.md`, `SECURITY.md` (head), `BENCHMARKS.md` (head), `pyproject.toml`, grep of `__main__.py` for hook installation.
- Findings:
  - `graphify claude install` writes a CLAUDE.md section and a **PreToolUse hook**. The always-on rule tells the agent to query the graph before any grep or file read and to put that rule in every subagent prompt.
  - SECURITY.md states that semantic extraction "may send content to a configured model/backend", `ingest` fetches URLs, and HTTP MCP is an opt-in listener. SSRF protections are described but I did not test them.
  - Roughly 30 tree-sitter grammars are hard dependencies, plus many optional extras (mcp, neo4j, video via yt-dlp, and others). Heavy install.
- **Not inspected:** the PreToolUse payload text, `extract.py` (641 KB), `engine.py` (651 KB), `cli.py` (308 KB), CI/publish workflows.

**Caveman** (JuliusBrussee/caveman, plugin 4.1.0, Apache-2.0 since 3.0.0, last push 2026-11-13)
- Read: `.claude-plugin/plugin.json`, `docs/HONEST-NUMBERS.md` (head), `LICENSING.md` (head); grepped `caveman-activate.js` and `caveman-stats.js`.
- Findings:
  - Hooks on SessionStart, SubagentStart, **UserPromptSubmit** and SessionEnd, each running `node` (silently skipped if node is absent).
  - The two scripts read and write config under the Claude config dir and an APPDATA caveman config. No HTTP, `child_process` or `spawn` calls matched in them.
  - The repo has grown into an engine, proxy, browser tool (Go), MCP delegate and a "Caveman Cloud" hosted product (LICENSING.md says Cloud is separate commercial software). That is far beyond a style skill.
- **Not inspected:** the other 2,000+ files, release binaries, proxy and MCP delegate code.

**K-Dense scientific-agent-skills** (MIT, last push 2026-11-09)
- Read: frontmatter and greps of `optimize-for-gpu` and `statistical-analysis`; file listings.
- Findings: both skills tell the agent to cite arXiv 2609.00065 and to fetch the arXiv page to take the current version; they also instruct package installs (`uv pip install` with pinned versions). `optimize-for-gpu` states it needs Linux or WSL2 and an NVIDIA GPU. README claims a CI security scan; I did not verify it.

**NVIDIA/skills** (Apache-2.0, last push 2026-11-12, 452 SKILL.md files)
- Read: the first 1.5 KB of the compute-sanitizer SKILL.md and its file list. The skill directory has a `BENCHMARK.md`, `evals/`, `references/`, `skill-card.md` and `skill.oms.sig`, and no scripts. Author is listed as an NVIDIA employee. I did not verify the signature.

**SarPy 2.1.1 / SARkit 1.12.0 / sarkit-processing / sarkit-assurance**
- Read: `setup.py`, `pyproject.toml` files, README heads, commit and tag lists, directory listings. No source code was read. All MIT.

## Ecosystem-level evidence (secondary, not re-verified)
The Hacker News (publication), Snyk, Koi and an academic study (arXiv 2602.06547) report malicious skills in public registries, including prompt injection and memory poisoning. Treat any skill from a registry as hostile until read. Sources are listed in [SKILLS_RESEARCH](SKILLS_RESEARCH.md).

## Required install controls (if any skill is later adopted)
1. Copy a pinned commit's SKILL.md plus references into `.claude/skills/<name>/` after reading every file. No marketplace auto-update.
2. No hooks from third parties. Write our own if needed.
3. Set `DISABLE_TELEMETRY=1` in the environment.
4. Python packages go into a project venv with pinned versions and hashes.
5. Re-audit on every upgrade by diffing against the pinned commit.

## Open items
- Read the TDD, systematic-debugging and verification-before-completion bodies in full before vendoring.
- Read the Graphify PreToolUse payload and `security.py`.
- Check the NVIDIA signature with its published tooling.
- Read `assumption_checks.py` in K-Dense `statistical-analysis`.
