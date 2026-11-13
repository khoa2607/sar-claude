"""Synthetic CPHD 1.1.0 fixtures with known geometry.

The XML structure is borrowed from the local Umbra file (so the tests need it), but every number that
matters (signal samples, timing, platform trajectory, frequencies, channel sizes) is synthetic and known.
Each platform moves on a circular arc around a fixed SRP, so the line-of-sight angular span equals the
arc angle exactly.
"""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import sarkit.cphd as sc

REAL = Path(__file__).resolve().parents[1] / "cphd" / "2023-11-19-16-12-16_UMBRA-05_CPHD.cphd"
SRP = np.array([6.378137e6, 0.0, 0.0])
RADIUS_M = 5.0e5
DT_S = 1.0e-4
FX1_HZ, FX2_HZ = 9.4e9, 9.7e9
RCV_DELAY_S = 3.0e-3


def _q(p):
    return "/".join("{*}" + s for s in p.split("/"))


def build_cphd(path: Path, channels: list[dict], *, nan_at=None, signal_value_2=None,
               jitter_frac: float = 0.0) -> Path:
    """channels: [{id, nv, ns, arc_deg, flagged=[vector indices with SIGNAL=0 and zero samples]}]."""
    with open(REAL, "rb") as f:
        meta = sc.Reader(f).metadata
        xml = copy.deepcopy(meta.xmltree)
    root = xml.getroot()
    data = root.find(_q("Data"))
    tmpl_ch = copy.deepcopy(data.find(_q("Channel")))
    for e in data.findall(_q("Channel")) + data.findall(_q("SupportArray")):
        data.remove(e)
    data.find(_q("NumCPHDChannels")).text = str(len(channels))
    data.find(_q("NumSupportArrays")).text = "0"
    sup = root.find(_q("SupportArray"))
    if sup is not None:
        root.remove(sup)
    cparams = root.find(_q("Channel"))
    tmpl_par = copy.deepcopy(cparams.find(_q("Parameters")))
    for e in cparams.findall(_q("Parameters")):
        cparams.remove(e)
    cparams.find(_q("RefChId")).text = channels[0]["id"]
    sig_off = pvp_off = 0
    for c in channels:
        n = copy.deepcopy(tmpl_ch)
        n.find(_q("Identifier")).text = c["id"]
        n.find(_q("NumVectors")).text = str(c["nv"])
        n.find(_q("NumSamples")).text = str(c["ns"])
        n.find(_q("SignalArrayByteOffset")).text = str(sig_off)
        n.find(_q("PVPArrayByteOffset")).text = str(pvp_off)
        data.insert(list(data).index(data.find(_q("NumCPHDChannels"))) + 1 + channels.index(c), n)
        sig_off += c["nv"] * c["ns"] * 8
        pvp_off += c["nv"] * 240
        p = copy.deepcopy(tmpl_par)
        p.find(_q("Identifier")).text = c["id"]
        p.find(_q("RefVectorIndex")).text = str(c["nv"] // 2)
        p.find(_q("SignalNormal")).text = "false" if (c.get("flagged") or signal_value_2) else "true"
        cparams.append(p)
    pvp_dtype = sc.get_pvp_dtype(xml)
    out = Path(path)
    with out.open("wb") as fh, sc.Writer(fh, sc.Metadata(xmltree=xml)) as w:
        for k, c in enumerate(channels):
            nv, ns = c["nv"], c["ns"]
            pvp = np.zeros(nv, dtype=pvp_dtype)
            dt = np.full(nv, DT_S)
            if jitter_frac:
                dt = dt * (1 + jitter_frac * np.where(np.arange(nv) % 2 == 0, 1.0, -1.0))
            t = np.concatenate(([0.0], np.cumsum(dt[:-1]))) if nv > 1 else np.zeros(1)
            half = np.deg2rad(c["arc_deg"]) / 2
            th = np.linspace(-half, half, nv)
            omega = (2 * half) / (t[-1] - t[0]) if nv > 1 else 0.0
            pos = SRP + RADIUS_M * np.stack([np.cos(th), np.sin(th), np.zeros(nv)], axis=1)
            vel = RADIUS_M * omega * np.stack([-np.sin(th), np.cos(th), np.zeros(nv)], axis=1)
            pvp["TxTime"], pvp["RcvTime"] = t, t + RCV_DELAY_S
            pvp["TxPos"], pvp["RcvPos"], pvp["TxVel"], pvp["RcvVel"] = pos, pos, vel, vel
            pvp["SRPPos"] = SRP
            pvp["FX1"], pvp["FX2"] = FX1_HZ, FX2_HZ
            pvp["SC0"], pvp["SCSS"] = FX1_HZ, (FX2_HZ - FX1_HZ) / max(ns - 1, 1)
            pvp["TOA1"], pvp["TOA2"] = -1e-6, 1e-6
            pvp["SIGNAL"] = 1
            rng = np.random.default_rng(100 + k)
            sig = (rng.standard_normal((nv, ns)) + 1j * rng.standard_normal((nv, ns))).astype(np.complex64)
            for i in c.get("flagged", []):
                pvp["SIGNAL"][i] = 0
                sig[i] = 0
            if signal_value_2 is not None and k == 0:
                pvp["SIGNAL"][signal_value_2] = 2
            if nan_at is not None and nan_at[0] == c["id"]:
                sig[nan_at[1], nan_at[2]] = np.nan
            w.write_signal(c["id"], sig)
            w.write_pvp(c["id"], pvp)
    return out
