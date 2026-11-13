"""Parameter provenance: every reported value says where it came from."""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any

import numpy as np


class Provenance(str, enum.Enum):
    MEASURED = "measured"          # read directly from the file (XML, PVP, header)
    DERIVED = "derived"            # computed from measured values by a documented formula
    ASSUMED = "assumed"            # a convention or default not stated in the file
    UNAVAILABLE = "unavailable"    # not present or not supported; no value is invented


def _plain(v: Any) -> Any:
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, np.ndarray):
        return v.tolist()
    return v


@dataclass(frozen=True)
class Param:
    value: Any
    unit: str | None
    provenance: Provenance
    source: str
    note: str = ""

    def to_dict(self) -> dict:
        return {"value": _plain(self.value), "unit": self.unit,
                "provenance": self.provenance.value, "source": self.source, "note": self.note}


def measured(value: Any, unit: str | None, source: str, note: str = "") -> Param:
    return Param(value, unit, Provenance.MEASURED, source, note)


def derived(value: Any, unit: str | None, source: str, note: str = "") -> Param:
    return Param(value, unit, Provenance.DERIVED, source, note)


def assumed(value: Any, unit: str | None, source: str, note: str = "") -> Param:
    return Param(value, unit, Provenance.ASSUMED, source, note)


def unavailable(source: str, note: str = "") -> Param:
    return Param(None, None, Provenance.UNAVAILABLE, source, note)
