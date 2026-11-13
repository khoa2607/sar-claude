import json
import pytest
from sarsil.provenance import Provenance, Param, measured, derived, assumed, unavailable


def test_categories_are_exactly_the_four_approved():
    assert {p.value for p in Provenance} == {"measured", "derived", "assumed", "unavailable"}


def test_constructors_set_category_and_source():
    m = measured(3.0, "m", "XML:Global/X")
    d = derived(6.0, "m", "2*X", note="doubling")
    a = assumed("FX", None, "domain default", note="not in file")
    u = unavailable("XML:Foo", note="absent")
    assert [x.provenance for x in (m, d, a, u)] == [
        Provenance.MEASURED, Provenance.DERIVED, Provenance.ASSUMED, Provenance.UNAVAILABLE]
    assert u.value is None and u.unit is None


def test_to_dict_is_json_serializable_and_keeps_unit_and_source():
    d = measured(1.5, "Hz", "PVP:FX1").to_dict()
    assert json.loads(json.dumps(d)) == {
        "value": 1.5, "unit": "Hz", "provenance": "measured", "source": "PVP:FX1", "note": ""}


def test_numpy_values_are_converted():
    import numpy as np
    d = measured(np.float64(2.0), "s", "x").to_dict()
    assert isinstance(d["value"], float)
    d = measured(np.array([1, 2]), None, "x").to_dict()
    assert d["value"] == [1, 2]

