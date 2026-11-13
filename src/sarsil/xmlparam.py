"""Helpers that turn XML elements into provenance-tagged parameters (shared by CPHD and SICD inspectors)."""
from __future__ import annotations

from typing import Any

from .provenance import Param, measured, unavailable


def q(path: str) -> str:
    """'A/B' -> '{*}A/{*}B' so lookups ignore the XML namespace."""
    return "/".join("{*}" + s for s in path.split("/"))


def text(node, path: str) -> str | None:
    e = node.find(q(path))
    return None if e is None or e.text is None else e.text.strip()


def param(node, path: str, conv=str, unit: str | None = None, src: str | None = None) -> Param:
    s = src or f"XML:{path}"
    if node is None:
        return unavailable(s, "parent element absent")
    t = text(node, path)
    if t is None or t == "":
        return unavailable(s, "element absent or empty")
    try:
        return measured(conv(t), unit, s)
    except ValueError:
        return unavailable(s, f"could not parse {t!r}")


def to_bool(t: str) -> bool:
    return t.strip().lower() in ("true", "1")


def params_to_dict(params: dict[str, Param]) -> dict:
    return {k: v.to_dict() for k, v in params.items()}


def tag(d: dict, source: str, provenance: str = "derived") -> dict:
    """Mark a plain dict of statistics as one provenance-tagged leaf."""
    return {**d, "provenance": provenance, "source": source}
