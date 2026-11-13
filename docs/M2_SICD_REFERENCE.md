# M2: SICD Reference for DS-001

Status: **accepted by the user on 2026-11-13 with the documented limitations below; committed** (`feat: add SICD reference and geometry validation`). Plan: [M2_PLAN](M2_PLAN.md) and `docs/superpowers/plans/2026-11-13-m2-sicd-reference.md`. Data: [DATASETS](DATASETS.md). CPHD side: [M1_INSPECTOR](M1_INSPECTOR.md). No image formation exists.

## Tools
```powershell
.venv\Scripts\python.exe scripts\compare_cphd_sicd.py cphd\<cphd> cphd\<sicd>     # table + outputs/comparison/*.json
.venv\Scripts\python.exe -m pytest -q
```
| Module | Role |
|---|---|
| `sarsil/sicd/inspector.py` | `inspect_sicd(path)`: read-only SICD report with provenance and SARkit consistency check |
| `sarsil/geometry/sicd_coords.py` | `SicdGeometry`: pixel, image-plane, ECF, ground-plane and CPHD image-area coordinate mapping (SARkit projections) |
| `sarsil/compare/cphd_sicd.py` | `compare_cphd_sicd(cphd, sicd)`: 30 comparison rows with stated tolerances |
| `sarsil/xmlparam.py` | XML-to-`Param` helpers shared with the CPHD inspector |

## SICD facts (file `..._SICD.nitf`, 215,757,674 bytes, SHA-256 `030e12f7...de108f`)
- SICD 1.2.1, pixel type `RE32F_IM32F` (complex float32), 5045 rows × 5345 columns, SCP pixel (2513, 2667); one image segment readable; a 256×256 chip near the SCP read in 0.02 s.
- Grid: type `RGAZIM`, plane `SLANT`; row spacing 0.5266 m, column spacing 0.8890 m; impulse-response width 0.590 m (row), 0.994 m (column); `Sgn` −1 on both axes.
- **Formation: PFA**, no azimuth or range autofocus, no beam compensation. Pulses 0 to 8779 (all 8,780). Processing steps recorded: "inscription" (fixed k-range and k-azimuth), a Valkyrie Sage/Umbra CPHD processor, **CPHD pulse RFI removal** (data fraction removed 3.9e-4, power fraction 7.5e-6), and `polar_deterministic_phase` (two-dimensional constant, linear and quadratic terms).
- **Weighting is not documented** (no `WgtType`/`WgtFunct` elements). Radiometric and calibration scaling are not characterised here.
- Frequency 9.4657271 to 9.7342673 GHz (268.54 MHz); SCP ECF identical to the CPHD IARP.
- Polarization strings in the SICD are `OTHER`/`OTHER`; the CPHD XML says `X`/`X`; the STAC catalog says VV. All three are reported as stated and **not reconciled**.
- Pixel data: the image has zero-valued margins (corner chips have median amplitude 0), so a valid-data mask is needed in any comparison. Amplitudes are small (256×256 chip near the SCP: max 0.6, median 0.01), i.e. the SICD is not in count units.
- SARkit SICD consistency: 103 checks, 0 failed, 29 inapplicable (35 partially).

## CPHD versus SICD (30 rows: 20 within, 4 exceed, 6 informational, one of them added post hoc)
Tolerance principles are in the module docstring: one SICD resolution cell (0.590 m) for positions and ranges, the angle subtending it at the slant range (5.2e-5°) for angles, one pulse interval (157.8 µs) for times, 1 Hz for frequencies, 1e-9 relative for copied values, 1% for angular span. I fixed the principles after a first look at the metadata and before assigning statuses; they were not changed afterwards to alter a status.

**Agree (within tolerance):** collection start; SCP = IARP = SRPPos at the reference vector (difference 0); image-area corners (9e-10 m); transmit frequency min/max (0 and −2e-6 Hz); all five waveform parameters (identical); pulse count 8,780; aperture duration (−2.7 µs); slant range (+0.167 m), ground range (+0.276 m), graze and incidence angles (±2.3e-5°); angular span (SICD polar-angle polynomial 0.935563° vs CPHD line-of-sight span 0.935561°, difference 1.9e-6°).

**Time axes:** the SICD time axis equals the CPHD transmit time plus the one-way delay to the SCP: (SICD start − CPHD start) differs from SlantRange/c by 1.3 µs, and the SICD center time equals CPHD `SRPCODTime` to 5.4e-9 s. This relation is not documented in either file; it is a numerical finding.

**Exceed tolerance (reported, not adjusted):**
| Row | Difference | Tolerance | Post-hoc explanation |
|---|---|---|---|
| SCPTime vs CPHD ReferenceTime | +288 µs | 158 µs | different definitions (COA time of the SCP vs reference-vector time) |
| ARP position | 2.21 m | 0.59 m | platform speed 7.67 km/s × 288 µs = 2.21 m, so the offset is motion over the time offset, not a geometry disagreement |
| Azimuth angle | +3.3e-4° | 5.2e-5° | same cause: the two angles refer to times 288 µs apart |
| Doppler cone angle | +1.8e-4° | 5.2e-5° | same cause |
The explanations are post-hoc; only the ARP one was checked numerically (informational row, 2.2106 vs 2.2104 m).

**Informational:** SICD row bandwidth is 84% of 2·B/c (the processed support is an inscribed rectangle of the polar annulus segment); SICD extent 2,657 × 4,751 m versus the producer-declared CPHD image area 4,000 × 4,000 m (different concepts); polarization strings (above); SICD processing steps (above); weighting unavailable.

## Coordinate conventions (implemented and unit-tested, 11 tests)
- Pixel (row, col): global zero-based indices; integer values are pixel centers. SCP-centered image-plane meters (xrow, ycol) = SS × offset from the SCP pixel.
- Slant image plane: ECF point = SCP + xrow·`Grid/Row/UVectECF` + ycol·`Grid/Col/UVectECF` (row axis is range, column axis is azimuth for this RGAZIM product).
- Ground plane: plane through the SCP with the geodetic up as normal, reached by SICD Volume 3 R/Rdot projection (SARkit), not by orthogonal projection. Constant-height surface and scene-to-image projections also wrap SARkit.
- **CPHD image-area plane = SICD ground plane**: the CPHD `uIAZ` equals the geodetic up at the SCP exactly (angle 0.0°), the IARP equals the SCP, and ground-projected SICD pixels have CPHD image-area Z below 0.01 m.
- Checks that pin conventions: SCP pixel → SCP; one pixel along row/col moves exactly SS along the matching unit vector with no transposition; round trip pixel → ground → pixel within 0.01 pixel; range foreshortening matches 1/cos(graze angle) within 1% (measured ratio 1.7045 vs 1.6967); corner pixels pair with the right declared corners and not with transposed ones.
- **Finding:** SICD `ImageCorners` differ from corners computed with the SICD projection by about 13–15 m (about 15–30 pixels, 0.3% of the extent), depending on the assumed height (the disagreement is smallest near HAE 270 m, with ±5 pixel column offsets). The method the producer used is undocumented. SARkit's own checker accepts them (it allows 5% of the largest chord, about 350 m). The unit test therefore pins orientation and a 20 m regression bound, **not** an accuracy claim. Because I first used a 1 m tolerance and replaced it after seeing 15 m, that history is recorded here.
- Two other tolerances were also loosened after first runs, with reasons: the in-plane round trip to 1e-4 m (the file's unit vectors are unit and orthogonal only to about 3e-10, giving about 1e-6 m), and the pixel round trip to 0.01 pixel (SARkit stops when ground displacement is below 1 mm, about 0.002 pixel).

## Image comparison methodology (defined; nothing implemented)
1. **What the SICD is.** A PFA product from a vendor chain with RFI removal, undocumented weighting, phase processing (`polar_deterministic_phase`) and unspecified calibration. It is a reference to compare against, not truth. Differences are reported, not "errors".
2. **Pairing and grid.** Always compare on the SICD pixel grid: map a formed image onto SICD pixels with `SicdGeometry` (ECF), never resample the SICD. Restrict to the SICD valid-data region (it has zero margins). Compare chips (for example 256×256) selected by a deterministic rule: local maxima ranking, minimum separation, fixed seed for any random choice.
3. **Registration.** First apply the coordinate mapping only. Then estimate residual shift by sub-pixel cross-correlation of amplitude (upsampled 16×) on each chip. Report the shift (pixels and meters) and its spread. Compare unshifted and shifted results; never hide a shift.
4. **Amplitude.** Estimate one global scale (least squares of amplitude over the common valid region), record it, then compare in dB over pixels above a noise threshold defined from the SICD's own low-amplitude percentile: mean and standard deviation of the dB difference, amplitude normalized cross-correlation, and difference histograms.
5. **Phase.** Absolute phase is not comparable without the SICD's phase terms. Use complex coherence magnitude |γ| over chips (insensitive to a constant phase), then the phase of γ after fitting a constant plus 2-D linear ramp; report the residual phase standard deviation only on high-coherence pixels. No absolute phase claim.
6. **Focus metrics.** Per isolated bright point (top-K local maxima): −3 dB widths in range and azimuth (interpolated), peak sidelobe ratio, integrated sidelobe ratio. Per chip: image entropy and normalized intensity sharpness. Compare to the SICD's declared impulse-response widths knowing the weighting is undocumented.
7. **Measurement floor first.** Before judging any formed image, compute the same metrics for the SICD against itself shifted by a known sub-pixel amount (Fourier shift) and for adjacent chips. The floor sets the achievable tolerance; acceptance tolerances are written to DECISIONS before the first formation result is evaluated.
8. **Aperture policy.** Formation uses all 8,780 valid vectors. "Chips" are spatial chips of the image, never aperture subsets.
9. **Reproducibility.** Log input SHA-256s, versions, chip coordinates, seeds, and raw per-chip numbers. **Automatic:** all metrics above. **Manual:** visual inspection of difference images and the choice of what a failed metric implies.
10. **Limitations.** One scene, one provider, one SICD processor; urban/field content only as in this scene; no ground truth for absolute location or radiometry; SICD float32 precision; the SICD RFI removal and phase terms may have no CPHD-side counterpart; a match shows agreement with the vendor chain, not correctness.

## Acceptance, unresolved issues and numerical tolerances
**Accepted** means the tools, tests and findings are accepted as a reference baseline. It does **not** mean the CPHD and SICD geometry are fully reconciled. These items stay open and must not be reported as validated:
1. **ImageCorners (13–15 m):** SICD-declared corners differ from corners projected with the SICD's own grid. The producer's method is unknown; SARkit's checker (5% of the largest chord, about 350 m) cannot confirm or refute it. Tests pin orientation and a 20 m regression bound only.
2. **Four rows exceed tolerance** (SCPTime vs ReferenceTime +288 µs; ARP position 2.21 m; azimuth +3.3e-4°; Doppler cone +1.8e-4°). The explanation (motion over a 288 µs reference-time offset) was found after seeing the numbers. It is numerically supported only for the position row (2.2106 vs 2.2104 m); the two angle rows are consistent with it but were not checked numerically.
3. **SICD time axis = CPHD transmit time + SlantRange/c** is an observed relation (1.3 µs residual), not a documented one.
4. **Polarization** differs by source (CPHD X/X, SICD OTHER, STAC VV): unreconciled by design.
5. **Weighting, calibration and phase conventions** of the SICD are undocumented; its RFI removal and `polar_deterministic_phase` steps may have no CPHD-side counterpart.
6. **Standards:** the NGA SICD/CPHD text was not read; SARkit's implementation was the reference for the polar-angle and projection conventions.
7. **Scope:** one scene, one provider, one vendor processing chain; three small SICD pixel chips examined; no image comparison has been run.

Tolerances in force (module `sarsil/compare/cphd_sicd.py`): geometry 0.590 m; angle 5.21e-5° (that distance at 649 km); time 157.8 µs (one pulse interval); frequency 1 Hz; copied values 1e-9 relative; angular span 1%. Test tolerances: in-plane round trip 1e-4 m; pixel round trip 0.01 pixel; foreshortening 1%; corner regression 20 m; IAC height 0.01 m. Loosened-after-first-run items are listed under Coordinate conventions and in DECISIONS (D-021).

## Tests and verification
- Full suite: **99 passed** (70 from M1 plus 29 for M2: 8 SICD inspector, 11 coordinates, 10 comparison). CPU only; real-data tests need the local files.
- Unchanged: CPHD SHA-256 `31bcefb4...b55790`; SICD hashed after download and used read-only.
- Mutation checks: swapping the row/column axes made 2 coordinate tests fail; using 2R/c for the time delay made 1 comparison test fail; both restored and 99 pass.
- Not verified: other providers' SICDs; SICD pixel statistics beyond three small chips; image formation readiness; the NGA SICD/CPHD standard text (SARkit's implementation was used as the reference for the polar-angle and projection conventions).
