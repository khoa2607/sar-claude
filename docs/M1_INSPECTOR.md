# M1: Read-only CPHD Inspector

Status: **finalized 2026-11-12, committed `8653056` and pushed**, with the limitations below. Roadmap: [DEVELOPMENT_ROADMAP](DEVELOPMENT_ROADMAP.md). Progress: [PROGRESS](PROGRESS.md). Dataset: [DATASETS](DATASETS.md). Next: [M2_PLAN](M2_PLAN.md).

## Use
```powershell
.venv\Scripts\python.exe scripts\inspect_cphd.py cphd\<file>.cphd [--scan-signal] [--thorough] [--hash] [--no-consistency] [--perf]
    [--chunk-budget-mib N] [--subaperture START STOP] [--nonuniform-rtol X] [--json PATH]
.venv\Scripts\python.exe -m pytest -q
```
Prints about 15 lines; writes the full report (sorted keys) to `outputs/inspection/<name>.json`, which git ignores. Exit codes: 0 ok, 2 controlled error (message on stderr), 3 ok but consistency failures.

## Code map
| Path | Role |
|---|---|
| `src/sarsil/provenance.py` | `Param`: measured / derived / assumed / unavailable, with unit and source |
| `src/sarsil/cphd/inspector.py` | `inspect_cphd(path, InspectOptions)` returns a JSON-ready dict |
| `src/sarsil/cphd/aperture.py` | timing, trajectory and angular-span math (pure functions) |
| `src/sarsil/cphd/chunking.py` | chunk planning and vector selection |
| `src/sarsil/cphd/errors.py`, `cli.py` | controlled errors, command line |
| `tests/cphd_fixtures.py` | synthetic CPHD builder with known geometry |

## Report contents
`source`, `format` (version, supported versions, header fields), `global` (collection, domain, SGN, timeline), `tx_waveform` (metadata parameters; samples marked unavailable), `unavailable_by_design`, `channels[]`, `support_arrays[]`, `layout`, `consistency`, `capabilities[]`, optional `signal_scan` and `performance`, `warnings`.

Each channel has: identifier, vector and sample counts, stored dtype, byte offsets, compressed size, PVP field list, `pvp_availability`, channel parameters, `frequency` (PVP union bandwidth kept separate from the `RFBandwidth` and `FxBW` metadata), and `aperture` (valid-vector counts, `signal_status`, selection, timing, receive timing, Tx and Rcv trajectories, angular span, SRP motion, producer-declared image area, SARkit-recomputed and file-declared reference geometry with their differences).

**Capability assessment:** each entry is supported, unsupported, uncertain or not_evaluated, with a reason (version, FX/TOA domain, multi-channel, signal scan, monostatic geometry, waveform reconstruction, full aperture, consistency checks, SIGNAL semantics, multi-provider compatibility, image-formation readiness).

## Behavior
- SARkit 1.12.0 reads CPHD 1.0.1 and 1.1.0. Other versions raise `UnsupportedFormatError`. Missing, empty, non-CPHD, truncated, corrupted-XML, duplicate-channel and out-of-block files raise `MalformedFileError`. An unknown `SignalArrayFormat` raises `UnsupportedFormatError`.
- The file is only opened read-only. Tests confirm size, mtime and SHA-256 are unchanged.
- **Bounded reads:** an inspection reads the XML and PVPs only (about 2 MB for the Umbra file). The optional scan uses a read-only memory map and chunks sized by `--chunk-budget-mib` (working-set factor 5). It scans the first channel only.
- **Full aperture by default.** `--subaperture` is the only way to narrow it and is labelled in the report.
- **Deterministic output:** the same file and options give identical JSON bytes (tested). Only the `--perf` section varies.

## Scientific conventions
- Positions are PVP values in CPHD ECF (WGS 84, m). LOS = unit(platform − SRPPos); bistatic bisector = unit(LOS_tx + LOS_rcv). Angular span: first-to-last, maximum from first, and cumulative (sum over consecutive vectors). It is a geometric description of the collection, **not** resolution, pixel spacing or scene extent. Limits: it assumes per-vector SRPPos is the scene reference; it ignores squint and Doppler geometry; for a non-planar path first-to-last and cumulative differ.
- Samples are big-endian: SARkit's dtype helper returns native order while the standard stores big-endian, as `Reader.read_signal` does.
- **SIGNAL PVP.** Evidence: SARkit's checker requires every sample of a vector with `SIGNAL == 0` to be zero, and `SignalNormal` to be true exactly when all vectors have `SIGNAL == 1` (SarPy documents `SignalNormal` as "all signal array vectors are normal", present iff the SIGNAL PVP is). So `0` means a zero-filled vector with no valid signal, `1` is normal, and the report keeps counts by value and the `SignalNormal` consistency. Vectors with `0` are excluded from the default aperture. Values other than 0 and 1 are kept, counted and flagged `uncertain`. **The NGA standard text itself was not accessed**, so the meaning of values above 1 is unconfirmed.
- **Nonuniform timing:** flagged when (dt_max − dt_min)/dt_median exceeds `--nonuniform-rtol` (default 0.001, a choice and not a standard). The report always gives the min, median and max dt, so the flag can be re-judged.
- **Polarization:** reported only from the CPHD XML (`Tx`/`Rcv` = `X`/`X` for DS-001). External catalog values (the STAC item says VV) are not read by the tool and are not reconciled; see [DATASETS](DATASETS.md).

## Results on DS-001 (Umbra-05), all 8,780 vectors
- 8,780 vectors by 8,747 samples, `>c8`, one channel; every `SIGNAL` is 1 and agrees with `SignalNormal`; two support arrays (Antenna 201×201, Antenna_element 2×2); no core PVP missing.
- TxTime span 1.385739 s; median dt 157.85 µs; dt spread 0.128% (flagged nonuniform at the default threshold), no gaps, strictly monotonic.
- Tx path 10.63 km, mean speed 7.67 km/s, 2.05 m maximum deviation from the chord; SRP fixed.
- Angular span 0.9356°. Plausibility check: path / slant range = 0.938°.
- PVP union bandwidth 268.540 MHz, center 9.5999972 GHz; equal to `RFBandwidth` for this file, though they are separate quantities.
- File-declared reference geometry matches SARkit's recomputation to 0.0002 m (slant range) and 5e-9° (angles).
- Declared ImageArea is ±2000 m (producer-declared; not derived).
- Consistency, default (non-thorough): 97 checks, 78 passed, 0 failed, 19 inapplicable. With `--thorough`: 80 passed, 0 failed, 17 inapplicable. Inapplicable checks pass vacuously because the file lacks the feature (antenna beam, dwell time, polarization reference, polygons); zero failures does not prove scientific correctness.
- Capabilities: 6 supported, 1 unsupported (waveform reconstruction), 1 uncertain (multi-channel on real data), 3 not evaluated.
- Performance (this machine): inspection 0.49 s, Python heap peak 10.5 MiB, process peak working set 65 MiB. Full scan at the 256 MiB default budget: 1.96 s, heap peak 317 MiB (about 1.2× the budget), peak working set 933 MiB (includes the memory-mapped file pages).

## Tests (70 passing)
23 unit tests (provenance, chunking, aperture math against analytic geometry); 7 malformed-input tests; 16 synthetic-fixture tests; 21 real-data tests (report content, determinism, no modification, memory bounds, independent signal cross-check); 3 CLI tests. A deliberate bug in the SIGNAL mask made 14 tests fail, then the code was restored.

## Limits
- **Multi-provider compatibility is not validated.** Only one real file from one provider has been tested. The synthetic multi-channel fixtures borrow their XML structure from the Umbra file (numbers are synthetic and known), so they test the code paths but not other providers' conventions.
- Multi-channel behavior is validated on synthetic files only; the scan covers the first channel only.
- TOA-domain files, compressed signal arrays, bistatic geometry and CPHD 1.0.1 were never tested on real data.
- The SIGNAL value meanings above 1 and the standard text are unconfirmed.
- SARkit's consistency checker emits a divide-by-zero warning on the synthetic fixtures (SCSS and TOA settings); it is harmless there.
- Superpowers skills were not loaded in the sessions that built M1, so verification was done by deterministic tests, a mutation check and manual review.
