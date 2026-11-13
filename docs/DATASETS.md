# Datasets

Verified: 2026-11-12. Datasets live in `cphd/` (git-ignored, read-only; see [AGENTS.md](../AGENTS.md)). Status: [PROGRESS](PROGRESS.md).

## DS-001: Umbra-05 spotlight, Beet Piler, ND (2023-11-19)

| Item | Value |
|---|---|
| Collect | `2023-11-19-16-12-16_UMBRA-05` |
| Source | Public S3 bucket `umbra-open-data-catalog` (us-west-2), also reachable over HTTPS |
| Prefix | `sar-data/tasks/Beet Piler - ND/13a1bac0-6d90-4a30-ada2-0fbfeb681aba/2023-11-19-16-12-16_UMBRA-05/` |
| STAC item | `stac/2023/2023-11/2023-11-19/70cae69f-6403-4c01-a390-4f84adecd2bd/70cae69f-6403-4c01-a390-4f84adecd2bd.json` |
| Access | Anonymous HTTPS listing and download worked (verified) |
| License | `CC-BY-4.0` per the STAC item (`properties.license`); the item has no license link. Attribution to Umbra required. The metadata JSON contains no license field. |
| Mode / band / pol | Spotlight, X band, VV, right-looking, descending (STAC and metadata JSON) |
| Incidence angle | 36.1° (STAC) |

### Objects (actual sizes from S3 listing, 2023-11-20 upload)

| Key (suffix after `..._UMBRA-05`) | Bytes | Local copy |
|---|---|---|
| `_CPHD.cphd` | 616,837,024 (588.3 MiB) | `cphd/2023-11-19-16-12-16_UMBRA-05_CPHD.cphd` |
| `_METADATA.json` | 7,352 | `cphd/2023-11-19-16-12-16_UMBRA-05_METADATA.json` |
| `_SICD.nitf` | 215,757,674 (205.8 MiB) | **Not downloaded.** Matching SICD for M2 validation. |
| `_SIDD.nitf` | 40,160,186 | Not downloaded |
| `_GEC.tif` | 50,860,332 | Not downloaded |

The metadata JSON is 7.3 KB, larger than the 4 KB in the task description. The S3 ETags are multipart (CPHD `935a6e7c…-74`) so they are not MD5s of the file.

Local SHA-256 (computed after download; byte count matches S3 exactly):
- CPHD: `31bcefb4272ff59f351dee7fe35dc44608b199ce08960a27a154110773b55790`
- METADATA.json: `b61778569f9be03d486e3fc7930f4c2e6b08fee2c88ad10a41d90485e269fb6d`

### CPHD facts (read with SARkit 1.12.0)

| Item | Value |
|---|---|
| Format version | `CPHD/1.1.0` (XML namespace `http://api.nsgreg.nga.mil/schema/cphd/1.1.0`): supported by SARkit |
| Header blocks (bytes) | XML 16,217 @1024; support 323,240 @17,280; PVP 2,107,200 @340,544; signal 614,389,280 |
| Domain | `FX`, `SGN` = -1, `FXFixedCPHD` true, `TOAFixedCPHD` false, `SRPFixedCPHD` true |
| Collect type / mode | MONOSTATIC / SPOTLIGHT; classification UNCLASSIFIED; collector Umbra-05 |
| Channels | 1 (`Primary`): 8,780 vectors × 8,747 samples, `CF8` (complex float32), big-endian `>c8` as read; 8,780 × 8,747 × 8 = 614,389,280 B, matches the signal block |
| PVPs | 20 fields, 240 bytes per vector: TxTime, TxPos, TxVel, RcvTime, RcvPos, RcvVel, SRPPos, aFDOP, aFRR1, aFRR2, FX1, FX2, TOA1, TOA2, TOAE1, TOAE2, TDTropoSRP, SC0, SCSS, SIGNAL |
| Support arrays | `Antenna` 201×201, `Antenna_element` 2×2 (8 B/element) |
| Timeline | TxTime1 0.0027477 s to TxTime2 1.3884862 s relative to collection start |
| Tx waveform (metadata) | LFM rate −5.674e12 Hz/s, pulse length 47.328 µs, RF bandwidth 268.54 MHz, center frequency 9.8685 GHz |
| Receive | Sample rate 750 MHz, window length 71.573 µs |
| SIGNAL PVP | all 1 (all vectors flagged valid) |

**Note:** the CPHD holds frequency-domain data with metadata describing the transmit waveform. It does **not** contain raw transmitted-waveform samples. Any waveform modeling must stay within what this metadata supports.

### Validation (executed 2026-11-12)
- `sarkit.cphd.read_file_header` and `Reader` open the file; the channel signal array and PVPs read without error; two sampled vectors were finite.
- `CphdConsistency` with `thorough=True`: **97 checks, 80 passed, 0 failed, 17 skipped** (1.2 s). The `cphdcheck` command printed nothing and exited 0, which matches zero failures.
- Not yet done: the 17 skipped checks were not examined; no comparison with the SICD.
- `Reader.read_signal` returned an in-memory NumPy array of 614 MB, not a memory map. Nothing was printed to the console beyond summary scalars. M1 should decide whether to read per-chunk.

### M1 inspector findings
Timing, geometry and frequency results from the inspector are in [M1_INSPECTOR](M1_INSPECTOR.md#results-on-ds-001-umbra-05). Notable: dt varies by 0.128% (no gaps); metadata polarization is X/X while the STAC item says VV.

### Open items
- The user's hardware note says RTX 2080, but `nvidia-smi` reports GeForce RTX 3060 with 12,288 MiB. Confirm which GPU is used.
- CC-BY-4.0 comes from the STAC item only; the bucket's own terms were not read.
- Scene location and footprint are in the metadata JSON (not summarized here).
