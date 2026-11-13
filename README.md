# SAR-SIL

Synthetic Aperture Radar Software-in-the-Loop research platform.

## Overview
A backend-only platform for multi-source CPHD processing and SAR image formation, with validated radar signal modeling where metadata supports it. The research goal is reproducible, modular signal-quality experiments on large SAR datasets.

## Status
**Early stage. A read-only CPHD inspector (M1) exists; no SAR image formation yet.** Phase 0A research is complete; the environment is set up. See [docs/PROGRESS.md](docs/PROGRESS.md) for the current state and [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md) for proposed milestones (all proposed, none implemented).

## Planned: multi-source CPHD support
Each CPHD source gets an adapter that maps to a common metadata model, with every parameter tagged measured, derived, assumed or unavailable. Source files are read-only. Scientific artifacts are stored separately from visualization images. Details: [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md).

## Technology stack
- Python 3.13 with [uv](https://docs.astral.sh/uv/)
- [SARkit](https://github.com/ValkyrieSystems/sarkit) 1.12.0 for CPHD 1.0.1 and 1.1.0 (primary library)
- Claude Code with the Superpowers plugin; a vendored, manual-only Caveman skill (experiment)
- Rationale and alternatives: [docs/RECOMMENDED_STACK.md](docs/RECOMMENDED_STACK.md), [docs/OPEN_SOURCE_REUSE.md](docs/OPEN_SOURCE_REUSE.md)

## Setup on Windows
Prerequisites: Python 3.13, uv, Git for Windows, Claude Code.

```powershell
git clone https://github.com/khoa2607/sar-claude.git
cd sar-claude
uv venv --python 3.13 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.lock.txt
.venv\Scripts\python.exe -c "import sarkit; print(sarkit.__name__)"
```

Place CPHD files in `cphd/` (ignored by git; never modify them).

## Inspect a CPHD file
```powershell
.venv\Scripts\python.exe scripts\inspect_cphd.py cphd\<file>.cphd --scan-signal
.venv\Scripts\python.exe -m pytest -q
```
Options include `--perf`, `--thorough` and `--nonuniform-rtol`. Details: [docs/M1_INSPECTOR.md](docs/M1_INSPECTOR.md). Dev tools: `uv pip install --python .venv\Scripts\python.exe -r requirements-dev.lock.txt`.

## Launch Claude Code
```powershell
cd sar-claude
claude
```
The first session in a new clone asks you to approve the project plugin (Superpowers). Entry point: [CLAUDE.md](CLAUDE.md), which imports [AGENTS.md](AGENTS.md).

## Update on another computer
```powershell
git pull origin main
uv pip install --python .venv\Scripts\python.exe -r requirements.lock.txt
```

## Daily Git commands
```powershell
git status
git pull --ff-only
git add <files>
git commit -m "type: summary"
git push
```

## Documentation
- [CLAUDE.md](CLAUDE.md), [AGENTS.md](AGENTS.md)
- [docs/PROGRESS.md](docs/PROGRESS.md), [docs/DECISIONS.md](docs/DECISIONS.md), [docs/DEVELOPMENT_ROADMAP.md](docs/DEVELOPMENT_ROADMAP.md)
- Research index: [docs/PHASE_0A_SUMMARY.md](docs/PHASE_0A_SUMMARY.md)
