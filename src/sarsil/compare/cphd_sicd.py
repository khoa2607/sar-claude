"""Metadata and geometry comparison between a CPHD and the SICD formed from it.

Every row states a tolerance and the principle it comes from. Rows are never adjusted to pass: a row that
exceeds its tolerance is reported as such. Rows with no meaningful tolerance are `informational`.

Tolerance principles
--------------------
* geometry_m   : the finest SICD impulse-response width (min Grid/Row|Col/ImpRespWid): positions and ranges must
                 agree to better than one resolution cell.
* angle_deg    : the angle that subtends `geometry_m` at the SICD slant range.
* pri_s        : the median CPHD pulse interval: times must agree to better than one pulse.
* freq_hz      : 1 Hz, far below the frequency sample spacing (tens of kHz).
* copied values: relative 1e-9 (values that should be transcribed unchanged).
* angular span : relative 1% (cross-range resolution scales inversely with the span).
The principles were fixed when this module was written, after a first look at the metadata; they were not
adjusted afterwards to change any status.
"""
from __future__ import annotations

import numpy as np

import sarkit.cphd as sc
import sarkit.sicd as ss
import sarkit.wgs84 as wgs84

from sarsil.cphd.inspector import InspectOptions, inspect_cphd
from sarsil.xmlparam import q

C_MPS = 299_792_458.0
SCHEMA = "sarsil.cphd_sicd_comparison/1"


def _f(node, path):
    return float(node.findtext(q(path)))


def _xyz(node, path):
    e = node.find(q(path))
    return np.array([float(e.findtext(q(k))) for k in "XYZ"])


def _poly(node, path):
    e = node.find(q(path))
    pairs = sorted((int(c.get("exponent1")), float(c.text)) for c in e.findall(q("Coef")))
    coefs = np.zeros(pairs[-1][0] + 1)
    for k, v in pairs:
        coefs[k] = v
    return coefs


def compare_cphd_sicd(cphd_path, sicd_path) -> dict:
    """Compare a CPHD and a SICD (read-only). Returns a deterministic, JSON-ready dict."""
    cphd_path, sicd_path = str(cphd_path), str(sicd_path)
    rep = inspect_cphd(cphd_path, InspectOptions(run_consistency=False))
    ap = rep["channels"][0]["aperture"]
    with open(cphd_path, "rb") as f:
        r = sc.Reader(f)
        cx = r.metadata.xmltree
        cid = rep["channels"][0]["identifier"]["value"]
        ref_idx = int(cx.getroot().findtext(q("Channel/Parameters/RefVectorIndex")))
        srp_ref = np.asarray(r.read_pvps(cid)["SRPPos"][ref_idx], dtype=float)
    with open(sicd_path, "rb") as f:
        sx = ss.NitfReader(f).metadata.xmltree
    C, S = cx.getroot(), sx.getroot()

    geom_tol = min(_f(S, "Grid/Row/ImpRespWid"), _f(S, "Grid/Col/ImpRespWid"))
    slant = _f(S, "SCPCOA/SlantRange")
    pri = ap["timing"]["dt_median_s"]
    tol = {"geometry_m": geom_tol, "angle_deg": float(np.degrees(geom_tol / slant)), "pri_s": pri,
           "freq_hz": 1.0, "copied_rel": 1e-9, "angular_span_rel": 1e-2}
    rows: list[dict] = []

    def add(rid, quantity, cphd, sicd, unit, tolerance, basis, note="", kind="abs"):
        c, s = np.asarray(cphd, dtype=float), np.asarray(sicd, dtype=float)
        d = np.linalg.norm(c - s) if c.ndim else float(c - s)
        if kind == "rel":
            d = float(d / abs(s))
        d = float(d)
        rows.append({"id": rid, "quantity": quantity, "cphd": cphd, "sicd": sicd, "unit": unit, "difference": d,
                     "tolerance": tolerance, "tolerance_basis": basis, "note": note,
                     "status": "within_tolerance" if abs(d) <= tolerance else "exceeds_tolerance"})

    def info(rid, quantity, cphd, sicd, unit, basis, note=""):
        rows.append({"id": rid, "quantity": quantity, "cphd": cphd, "sicd": sicd, "unit": unit, "difference": None,
                     "tolerance": None, "tolerance_basis": basis, "note": note, "status": "informational"})

    g_basis = "finest SICD impulse-response width (one resolution cell)"
    a_basis = "angle subtending one resolution cell at the SICD slant range"
    t_basis = "one CPHD pulse interval (median TxTime spacing)"
    rel_basis = "copied value, relative 1e-9"

    # ---- identity and positions
    cs, ss_ = C.findtext(q("Global/Timeline/CollectionStart")), S.findtext(q("Timeline/CollectStart"))
    rows.append({"id": "collect_start", "quantity": "collection start time", "cphd": cs, "sicd": ss_, "unit": None,
                 "difference": 0.0 if cs == ss_ else None, "tolerance": 0.0, "tolerance_basis": "exact string match",
                 "note": "", "status": "within_tolerance" if cs == ss_ else "exceeds_tolerance"})
    scp = _xyz(S, "GeoData/SCP/ECF")
    add("scp_vs_iarp_ecf_m", "SICD SCP vs CPHD IARP (ECF)", _xyz(C, "SceneCoordinates/IARP/ECF").tolist(), scp.tolist(),
        "m", geom_tol, g_basis)
    add("scp_vs_srp_pvp_ecf_m", "SICD SCP vs CPHD SRPPos at the reference vector (ECF)", srp_ref.tolist(), scp.tolist(),
        "m", geom_tol, g_basis, f"reference vector index {ref_idx}")
    def corners(node, path):
        return np.array([[float(c.findtext(q("Lat"))), float(c.findtext(q("Lon")))] for c in node.findall(q(path))])
    ca, sa = corners(C, "SceneCoordinates/ImageAreaCornerPoints/IACP"), corners(S, "RadarCollection/Area/Corner/ACP")
    ecf = lambda ll: wgs84.geodetic_to_cartesian(np.column_stack([ll, np.zeros(len(ll))]))  # noqa: E731
    dist = np.linalg.norm(ecf(ca) - ecf(sa), axis=1)
    rows.append({"id": "area_corners_max_m", "quantity": "CPHD image-area corners vs SICD area corners (max over 4, HAE 0)",
                 "cphd": ca.tolist(), "sicd": sa.tolist(), "unit": "m", "difference": float(dist.max()), "tolerance": geom_tol,
                 "tolerance_basis": g_basis, "note": "", "status": "within_tolerance" if dist.max() <= geom_tol else "exceeds_tolerance"})

    # ---- frequency
    fr = rep["channels"][0]["frequency"]
    add("tx_freq_min_hz", "minimum transmit frequency (CPHD min FX1 vs SICD TxFrequency/Min)", fr["fx1_min_hz"]["value"],
        _f(S, "RadarCollection/TxFrequency/Min"), "Hz", tol["freq_hz"], "1 Hz, far below the frequency sample spacing")
    add("tx_freq_max_hz", "maximum transmit frequency (CPHD max FX2 vs SICD TxFrequency/Max)", fr["fx2_max_hz"]["value"],
        _f(S, "RadarCollection/TxFrequency/Max"), "Hz", tol["freq_hz"], "1 Hz, far below the frequency sample spacing")

    # ---- waveform parameters
    tw, rc = rep["tx_waveform"], rep["tx_waveform"]["receiver"]
    wf = "RadarCollection/Waveform/WFParameters/"
    for rid, name, cv, path, unit in [
            ("tx_pulse_length_s", "TX pulse length", tw["pulse_length"]["value"], "TxPulseLength", "s"),
            ("tx_rf_bandwidth_hz", "TX RF bandwidth (metadata)", tw["rf_bandwidth_metadata"]["value"], "TxRFBandwidth", "Hz"),
            ("tx_fm_rate_hz_per_s", "TX LFM rate", tw["lfm_rate"]["value"], "TxFMRate", "Hz/s"),
            ("adc_sample_rate_hz", "receiver sample rate", rc["sample_rate"]["value"], "ADCSampleRate", "Hz"),
            ("rcv_window_length_s", "receive window length", rc["window_length"]["value"], "RcvWindowLength", "s")]:
        add(rid, name, cv, _f(S, wf + path), unit, tol["copied_rel"], rel_basis, kind="rel")

    # ---- aperture and time axes
    n_c = rep["channels"][0]["num_vectors"]["value"]
    n_s = int(S.findtext(q("Timeline/IPP/Set/IPPEnd"))) - int(S.findtext(q("Timeline/IPP/Set/IPPStart"))) + 1
    add("num_vectors", "pulse count (CPHD NumVectors vs SICD IPPEnd-IPPStart+1)", n_c, n_s, "vectors", 0.0, "exact")
    t0, t1 = ap["timing"]["t_first_s"], ap["timing"]["t_last_s"]
    p0, p1 = _f(S, "ImageFormation/TStartProc"), _f(S, "ImageFormation/TEndProc")
    add("aperture_duration_s", "aperture duration (CPHD TxTime span vs SICD TEndProc-TStartProc)", t1 - t0, p1 - p0, "s", pri, t_basis)
    delay = slant / C_MPS
    add("sicd_start_minus_cphd_start_s_vs_slant_range_over_c", "SICD TStartProc - CPHD first TxTime vs SlantRange/c",
        delay, p0 - t0, "s", pri, t_basis,
        "Hypothesis, not documented in either file: SICD time = CPHD transmit time + one-way delay to the SCP.")
    add("sicd_center_time_vs_cphd_srp_cod_time_s", "SICD (TStartProc+TEndProc)/2 vs CPHD ReferenceGeometry/SRPCODTime",
        _f(C, "ReferenceGeometry/SRPCODTime"), (p0 + p1) / 2, "s", pri, t_basis)
    add("scp_time_vs_cphd_reference_time_s", "SICD SCPCOA/SCPTime vs CPHD ReferenceGeometry/ReferenceTime",
        _f(C, "ReferenceGeometry/ReferenceTime"), _f(S, "SCPCOA/SCPTime"), "s", pri, t_basis,
        "Definitions differ (COA time of the SCP versus the reference vector time); an offset is not an error by itself.")

    # ---- reference geometry at the SCP / reference vector
    m = "ReferenceGeometry/Monostatic/"
    for rid, name, cp, sp, unit, tl, basis in [
            ("slant_range_m", "slant range", m + "SlantRange", "SCPCOA/SlantRange", "m", geom_tol, g_basis),
            ("ground_range_m", "ground range", m + "GroundRange", "SCPCOA/GroundRange", "m", geom_tol, g_basis),
            ("graze_angle_deg", "graze angle", m + "GrazeAngle", "SCPCOA/GrazeAng", "deg", tol["angle_deg"], a_basis),
            ("incidence_angle_deg", "incidence angle", m + "IncidenceAngle", "SCPCOA/IncidenceAng", "deg", tol["angle_deg"], a_basis),
            ("azimuth_angle_deg", "azimuth angle", m + "AzimuthAngle", "SCPCOA/AzimAng", "deg", tol["angle_deg"], a_basis),
            ("doppler_cone_angle_deg", "Doppler cone angle", m + "DopplerConeAngle", "SCPCOA/DopplerConeAng", "deg", tol["angle_deg"], a_basis)]:
        add(rid, name, _f(C, cp), _f(S, sp), unit, tl, basis,
            "CPHD value is file-declared at the reference vector time; SICD value is at SCPTime.")
    add("arp_position_ecf_m", "platform position (CPHD ReferenceGeometry ARPPos vs SICD SCPCOA ARPPos)",
        _xyz(C, "ReferenceGeometry/Monostatic/ARPPos").tolist(), _xyz(S, "SCPCOA/ARPPos").tolist(), "m", geom_tol, g_basis,
        "Different reference times, so an offset of speed x time difference is expected.")

    dt_ref = _f(C, "ReferenceGeometry/ReferenceTime") - _f(S, "SCPCOA/SCPTime")
    speed = float(np.linalg.norm(_xyz(C, "ReferenceGeometry/Monostatic/ARPVel")))
    info("arp_offset_vs_speed_times_time_offset_m", "platform position offset vs (CPHD ARP speed x reference-time offset)",
         speed * abs(dt_ref), float(np.linalg.norm(_xyz(C, "ReferenceGeometry/Monostatic/ARPPos") - _xyz(S, "SCPCOA/ARPPos"))), "m",
         "explanatory only, no tolerance",
         "post-hoc: added after the ARP position and time rows exceeded tolerance; it shows the position offset is the platform "
         "motion over the reference-time offset, not a geometry disagreement")

    # ---- angular span: SICD polar angle polynomial vs CPHD line-of-sight span
    pa = _poly(S, "PFA/PolarAngPoly")
    span_sicd = float(np.degrees(abs(np.polynomial.polynomial.polyval(p1, pa) - np.polynomial.polynomial.polyval(p0, pa))))
    span_cphd = ap["angular_span"]["first_last_deg"]
    rows.append({"id": "angular_span_deg", "quantity": "angular span (CPHD LOS first-last vs SICD |PolarAngPoly(TEndProc)-PolarAngPoly(TStartProc)|)",
                 "cphd": span_cphd, "sicd": span_sicd, "unit": "deg", "difference": float(span_cphd - span_sicd),
                 "tolerance": tol["angular_span_rel"] * span_sicd, "tolerance_basis": "relative 1% (cross-range resolution scales inversely with span)",
                 "note": "PolarAngPoly takes time since collection start (SARkit's checker evaluates it at PolarAngRefTime and requires 0).",
                 "status": "within_tolerance" if abs(span_cphd - span_sicd) <= tol["angular_span_rel"] * span_sicd else "exceeds_tolerance"})

    # ---- informational
    rb = 2 * rep["channels"][0]["frequency"]["pvp_union_bandwidth"]["value"] / C_MPS
    info("row_bandwidth_vs_pvp_bandwidth", "SICD Row ImpRespBW vs 2*PVP union bandwidth/c", rb, _f(S, "Grid/Row/ImpRespBW"), "cycles/m",
         "no tolerance: the processed support is a rectangle inscribed in the polar annulus segment, so it is smaller by design",
         f"ratio SICD/CPHD = {_f(S, 'Grid/Row/ImpRespBW') / rb:.4f}")
    ia = ap["image_area_metadata"]["value"]
    info("image_extent_m", "image extent (CPHD declared ImageArea vs SICD rows x SS, cols x SS)",
         [ia["x2y2_m"][0] - ia["x1y1_m"][0], ia["x2y2_m"][1] - ia["x1y1_m"][1]],
         [_f(S, "ImageData/NumRows") * _f(S, "Grid/Row/SS"), _f(S, "ImageData/NumCols") * _f(S, "Grid/Col/SS")], "m",
         "different concepts (producer-declared area vs processed grid); no tolerance")
    info("polarization_strings", "polarization as stated in each file (Tx, Rcv)",
         [rep["channels"][0]["parameters"]["tx_pol"]["value"], rep["channels"][0]["parameters"]["rcv_pol"]["value"]],
         [S.findtext(q("RadarCollection/TxPolarization")), S.findtext(q("RadarCollection/RcvChannels/ChanParameters/TxRcvPolarization"))],
         None, "values reported as stated; no reconciliation with each other or with external catalogs")
    info("sicd_processing_steps", "processing steps recorded in the SICD (the CPHD records none)", [],
         [(p.findtext(q("Type")) or "").strip() for p in S.findall(q("ImageFormation/Processing"))], None,
         "SICD may include steps (for example RFI removal) not applied to the CPHD samples")
    info("sicd_weighting", "SICD row/col weighting",
         None, [S.findtext(q("Grid/Row/WgtType/WindowName")), S.findtext(q("Grid/Col/WgtType/WindowName"))], None,
         "weighting is not documented in the SICD (elements absent)")

    n = {k: sum(1 for x in rows if x["status"] == k) for k in ("within_tolerance", "exceeds_tolerance", "informational")}
    return {"schema": SCHEMA, "tolerances": tol, "rows": rows,
            "summary": {"total": len(rows), **n},
            "sources": {"cphd": cphd_path, "sicd": sicd_path}}
