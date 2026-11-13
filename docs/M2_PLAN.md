# M2 Plan: SICD Reference and SAR Image Formation Preparation

Status: **executed 2026-11-13; results in [M2_SICD_REFERENCE](M2_SICD_REFERENCE.md).** This file is the original plan; where it differs (for example the corner-agreement idea), the results document governs. Context: [M1_INSPECTOR](M1_INSPECTOR.md), [DATASETS](DATASETS.md), [OPEN_SOURCE_REUSE](OPEN_SOURCE_REUSE.md), [DEVELOPMENT_ROADMAP](DEVELOPMENT_ROADMAP.md).

## Goal
Prepare a trustworthy reference for later image formation: obtain the Umbra SICD for DS-001, understand exactly how it was formed, check that it is geometrically consistent with the CPHD, and fix the comparison method before any formation code exists.

## Steps
1. **Acquire and verify the SICD.** Download `..._SICD.nitf` (215,757,674 bytes) from the DS-001 prefix (listed in [DATASETS](DATASETS.md)) into `cphd/` (git-ignored). Check size against the S3 listing, record SHA-256, and run SARkit's SICD consistency checker (`sarkit.verification.SicdConsistency`, `sicdcheck`). Same CC-BY-4.0 attribution.
2. **Interpret SICD metadata (read-only).** Report with the existing provenance model: image dimensions and pixel type, `ImageFormation` algorithm and parameters, grid type (RGAZIM, PLANE, XRGYCR, XCTYAT), row and column sample spacing and resolution/impulse-response widths, weighting (window) per axis, SCP location, timeline, and radar collection geometry. Do not assume the algorithm: read it.
3. **CPHD-to-SICD geometry checks (metadata only).** Compare collect time span, SRP vs SICD SCP in ECF, slant range, graze/incidence/azimuth angles (M1 already has file-declared and SARkit-recomputed CPHD values), center frequency, bandwidth, polarization (source XML values only, no catalog reconciliation) and aperture time. Each comparison states its tolerance and the reason for it.
4. **Define reference image coordinates.** Use SICD image rows/columns with the SCP as origin and the SICD grid vectors in ECF; document how an image pixel maps to ECF and how a CPHD image-area coordinate (IAC) maps to the same point (SARkit has the IAC transforms). Fix this mapping and its sign conventions in a document with a unit test using a point whose position is known.
5. **Fix the comparison methodology before writing formation code.**
   - Align on ECF position, not pixel index. Estimate any residual shift by sub-pixel cross-correlation of amplitude, and report it rather than hide it.
   - Compare complex values only after stating which phase terms are removed (SICD phase conventions, deskew). Otherwise compare amplitude (dB) and local structure.
   - Metrics: normalized cross-correlation of amplitude, residual dB statistics, and impulse-response measures (−3 dB width, peak sidelobe ratio) on isolated bright scatterers, compared with the SICD's declared resolution and weighting. Tolerances are chosen after seeing the SICD-to-SICD noise floor (for example, SICD against itself resampled), not before.
   - Save raw numbers and logs for every comparison.
6. **Candidate formation algorithms (for M5, not M2).**
   - Polar format algorithm (PFA): the natural match for a spotlight collection with FX-domain data; fast; its approximations (planar wavefront) limit scene size. This is the first candidate if step 2 shows the SICD used PFA.
   - Time-domain backprojection: exact for the stated geometry, no wavefront approximation, expensive; the accuracy reference and the algorithm FastSAR and torchbp implement.
   - Range-migration style algorithms: only if step 2 shows the SICD used one; not otherwise needed for spotlight data.
   - Decide build versus adopt (O-001) at the start of M5 using these results; FastSAR and torchbp stay as cross-checks in a separate environment.
7. **CPU-first validation.** Formation tests start on small chips (for example 256×256 pixels) on the CPU, at full aperture, so every pulse contributes. A GPU backend (RTX 3060, 12 GB) comes only after CPU outputs match the reference.

## Constraints and estimates
- Signal block: 8,780 × 8,747 × 8 B = 614 MB; the inspector reads it in chunks, and formation code must use the same chunking (chunking is a memory unit, not a separate aperture).
- Backprojection cost is pulses × pixels × (range interpolation): a 256×256 chip needs 65,536 × 8,780 ≈ 5.8×10⁸ pixel-pulse updates; a 4,096×4,096 image needs about 1.5×10¹¹. Times depend on the implementation and are **not measured**; they will be measured in M5, not assumed.
- Memory: the SICD (about 206 MiB) and the CPHD fit in RAM; image products are stored as complex arrays plus a sidecar record (M3).

## Full-aperture policy
All valid vectors (8,780 for DS-001) are used for every formation test. Subapertures are only explicit, labelled experiments. Nothing in M2 may choose an aperture size to save runtime.

## Acceptance criteria
- SICD downloaded, hashed, and checked with SARkit (result recorded, any failures explained).
- A written SICD interpretation including the algorithm and parameters, and a CPHD-to-SICD comparison table with tolerances and results.
- The coordinate mapping document and its unit test.
- The comparison methodology and metrics written down, with a SICD-to-SICD noise-floor measurement.
- No image formation code.

## Risks and unknowns
- The SICD's formation algorithm, weighting and phase conventions are unknown until step 2.
- Umbra's SICD may be formed with details (for example, a non-uniform window or autofocus) that the CPHD does not describe, limiting how close a match is possible.
- Only one provider is covered; M2 results say nothing about other providers' SICD and CPHD conventions.
