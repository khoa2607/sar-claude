# Open-Source SAR Reuse Assessment

Verified: 2026-11-12 from primary repository metadata and manifests (GitHub API, raw files). Source code was not audited; see [SKILL_SECURITY_AUDIT](SKILL_SECURITY_AUDIT.md). Summary: [PHASE_0A_SUMMARY](PHASE_0A_SUMMARY.md).

## Corrections to the first-pass report
- SarPy is at **2.1.1** (tag `v2.1.1`, last push 2026-10-23), not 1.3.64. It now depends on `sarkit`.
- SARkit's canonical repo is **ValkyrieSystems/sarkit** (not ngageoint), MIT, v1.12.0 (2026-09-17), last commit 2026-10-05. Its README calls it the modern successor to SarPy.

## Candidates

| Package | License | Status | Formats / scope | Key limits |
|---|---|---|---|---|
| **SARkit** [github.com/ValkyrieSystems/sarkit](https://github.com/ValkyrieSystems/sarkit) | MIT | Active (v1.12.0) | Read/write CRSD, CPHD, SICD, SIDD; XML metadata objects; consistency checks (`verification/` module) | Python ≥3.12, numpy ≥2.0, lxml, shapely, jbpy. Deps are small. |
| *SARkit detail (verified in source, 2026-11-12)* | | | Supported CPHD versions **1.0.1 and 1.1.0** (both XSD schemas bundled; **0.3 is not supported**). `Reader.read_channel(id)`, `read_signal(id)`, `read_pvps(id)` select channels by `Data/Channel/Identifier`; compressed signal arrays are handled. Helpers: PVP dtypes, `compute_t_ref` (signal model), reference geometry, image-area and scene-coordinate transforms. `sarkit/verification/_cphd_consistency.py` holds `CphdConsistency` with about 98 `check_*` methods, usable from a `cphdcheck` CLI (`--thorough` reads through the signal). | Check coverage not tested. No image formation. |
| **sarkit-processing** [repo](https://github.com/ValkyrieSystems/sarkit-processing) | MIT | Active (push 2026-11-04) | SICD-level tools: remocomp, deskew, area plane, scene-to-image, chipping, atmosphere | Operates on SICD, not CPHD. Needs numba, scipy, networkx. **No image formation.** |
| **sarkit-assurance** [repo](https://github.com/ValkyrieSystems/sarkit-assurance) | MIT | Active (push 2026-11-06) | "SAR-related assurance tools" | README gives little detail; scope unverified. |
| **sarkit-convert** [repo](https://github.com/ValkyrieSystems/sarkit-convert) | MIT | Push 2026-08-26 | Conversion of vendor data to standard formats | Scope unverified. |
| **SarPy** [github.com/ngageoint/sarpy](https://github.com/ngageoint/sarpy) | MIT | Active (v2.1.1) | `phase_history/cphd.py` reads CPHD 0.3 and 1, writes version 1. SICD/SIDD I/O, ortho-rectify, registration, SICD normalization | Deps: h5py, numpy, scipy, pillow, matplotlib, shapely, lxml, sarkit. Heavier than SARkit. No image-formation code found under `sarpy/processing` (only `ortho_rectify`, `registration`, `sicd`, `sidd`). |
| *SarPy detail (verified in source)* | | | SarPy 2.0 "is a merge between the sarkit library and legacy SarPy functions" and adds SARkit-based fast readers (`sarpy.io.sarkitFastReader`: SICD, SIDD, CPHD, CRSD). Its legacy CPHD classes are marked `@deprecated("sarpy's CPHD implementation is deprecated. Please use sarkit.")`. | **Overlap with SARkit is near-total for CPHD.** Keep SarPy only for non-CPHD extras if needed (ortho-rectify, registration). |
| **FastSAR** [github.com/saulpingerman/FastSAR](https://github.com/saulpingerman/FastSAR) | MIT | Active but young: created 2026-10-05, 360 commits, pushed 2026-11-13; classifier "Development Status :: 3 - Alpha" | Reads CPHD 1.0, 1.1 and 0.3 (frequency-domain) plus NISAR, Sentinel-1, ALOS PALSAR raw; factorized backprojection for spotlight, stripmap, sliding spotlight; autofocus, interferometry, geolocation, SICD output; CPU (prebuilt wheels), CUDA via CuPy, TPU via JAX | Wheels for Linux and macOS only; no Windows classifier, so use WSL2. GPU path needs Linux x86-64 CuPy. **TOA-domain CPHD not supported.** Speed and accuracy figures in its README are author-reported and unverified here. Deps: numpy ≥2.2.6, scipy, jax. |
| **torchbp** [github.com/Ttl/torchbp](https://github.com/Ttl/torchbp) | MIT | Created 2025-01-20, pushed 2026-10-06, 2 open issues | Differentiable backprojection (polar/Cartesian), FFBP, autofocus, NUFFT projection as a C++/PyTorch extension. Examples load safetensors, not CPHD | Tested with CUDA 12.9; build from source against installed torch (`--no-build-isolation`); Windows not documented; CPU-only machines skip CUDA tests. Algorithm reference, not a CPHD tool. |
| **sar-focus** [github.com/asp53826/sar-focus](https://github.com/asp53826/sar-focus) | MIT | Pushed 2026-08-13 | Teaching-scale LFM pulse compression, time-domain backprojection, PGA; 27 tests checked against analytic resolution and sidelobe values | Raw phase history, not CPHD. Useful as a model of "validate against analytic values". |
| **grdl-sartoolbox** [github.com/GEOINT/grdl-sartoolbox](https://github.com/GEOINT/grdl-sartoolbox) | MIT | Pushed 2026-11-02 | Pure-NumPy port of the NGA MATLAB SAR Toolbox; PulseExplorer viewer | Scope beyond README head unread. |
| **ISCE3** [github.com/isce-framework/isce3](https://github.com/isce-framework/isce3) | GitHub reports NOASSERTION (unresolved) | Pushed 2026-11-10 | C++/Python InSAR/SAR framework. FastSAR's README estimates ISCE3 backprojection on CPU at about 4.8 h for one image (author's estimate) | Not read further; license text not checked. |
| **osubp** [github.com/bambang/osubp](https://github.com/bambang/osubp) | Not checked | Not checked | PyCUDA backprojection | README lists open items; reference only. |
| pyroSAR, MintPy | Not investigated | | | Likely satellite-product/InSAR oriented; not needed for CPHD formation. |

## Reuse / adapt / build

| Need | Decision | Basis |
|---|---|---|
| CPHD parsing, metadata, XML objects | **Reuse** SARkit (primary) | Verified: reader/writer + schema objects. |
| CPHD consistency checking | **Reuse** SARkit `CphdConsistency` (about 98 checks) | Verified in source; correctness of individual checks not tested. SarPy's checker is legacy. |
| CPHD 0.3 legacy files | Out of scope unless needed; SarPy (deprecated reader) or FastSAR can read 0.3 | SARkit does not support 0.3. |
| SICD post-processing | **Reuse** sarkit-processing | Verified list of modules. |
| Backprojection from CPHD | **Open (O-001):** FastSAR exists and reads CPHD, but is alpha, young and Linux/macOS-only. Recommended: build our own validated implementation and use FastSAR (in WSL2/separate env) plus torchbp as independent cross-checks. | No CPHD-to-image code in SarPy or sarkit-processing (verified by file listing). FastSAR claims are author-reported. |
| Range-Doppler / PFA | Build if needed | FastSAR covers factorized backprojection only per its README summary. |
| Motion compensation / autofocus | Reference FastSAR and torchbp autofocus; build as needed | Unverified. |
| FFT operations | **Reuse** numpy/scipy (CPU); CuPy or PyTorch for GPU | Standard libraries; not researched here. |
| Large-array storage | **Adapt** (e.g. Zarr/HDF5/memmap) | Not researched; decide in Phase 0B. |
| Experiment harness, run provenance, artifact metrics | **Build** | Nothing found. |
| Test data | **Reuse** public buckets: Umbra (`umbra-open-data-catalog`), Capella (`capella-open-data`) | Search summaries only. Confirm CPHD availability and license per collect before use. |

## Unresolved
- Resolved 2026-11-12: SARkit supports CPHD 1.0.1 and 1.1.0; SarPy's CPHD is deprecated; torchbp is MIT; FastSAR exists.
- SARkit requires Python ≥3.12 and numpy ≥2; the local default Python is 3.10.11 (see [DECISIONS](DECISIONS.md) P-001).
- Windows install behavior of numba, shapely, jbpy wheels: not tested (no installs allowed).
- ISCE3 license text, pyroSAR, MintPy: not checked.
- FastSAR accuracy and speed claims, and its handling of non-Umbra sources: unverified.
- NGA CPHD standard document itself: not read; SARkit's TOA-domain support status not checked.
- No CPHD file is available locally (`cphd/` is empty).
