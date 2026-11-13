import numpy as np
import pytest
from sarsil.cphd.chunking import plan_chunks, contiguous_runs, select_vectors


def test_chunks_cover_every_vector_exactly_once():
    chunks = plan_chunks(8780, bytes_per_vector=8747 * 8, memory_budget_bytes=64 * 2**20)
    assert chunks[0][0] == 0 and chunks[-1][1] == 8780
    assert all(a[1] == b[0] for a, b in zip(chunks, chunks[1:]))
    assert sum(b - a for a, b in chunks) == 8780


def test_chunk_size_follows_budget_not_a_fixed_constant():
    small = plan_chunks(1000, 1000, memory_budget_bytes=10_000)
    large = plan_chunks(1000, 1000, memory_budget_bytes=100_000)
    assert max(b - a for a, b in small) == 10
    assert max(b - a for a, b in large) == 100


def test_budget_smaller_than_one_vector_still_progresses_one_at_a_time():
    chunks = plan_chunks(5, 1000, memory_budget_bytes=1)
    assert chunks == [(i, i + 1) for i in range(5)]


def test_empty_and_invalid_inputs():
    assert plan_chunks(0, 8, 1024) == []
    with pytest.raises(ValueError):
        plan_chunks(10, 0, 1024)
    with pytest.raises(ValueError):
        plan_chunks(10, 8, 0)
    with pytest.raises(ValueError):
        plan_chunks(-1, 8, 1024)


def test_contiguous_runs():
    mask = np.array([1, 1, 0, 0, 1, 0, 1, 1, 1], dtype=bool)
    assert contiguous_runs(mask) == [(0, 2), (4, 5), (6, 9)]
    assert contiguous_runs(np.zeros(4, dtype=bool)) == []


def test_default_selection_is_full_aperture_of_valid_vectors():
    sel = select_vectors(np.ones(8780, dtype=bool))
    assert sel.policy == "full" and sel.count == 8780 and sel.runs == [(0, 8780)]


def test_full_selection_excludes_only_invalid_vectors():
    valid = np.ones(10, dtype=bool); valid[3] = False
    sel = select_vectors(valid)
    assert sel.policy == "full" and sel.count == 9 and sel.runs == [(0, 3), (4, 10)]


def test_explicit_subaperture_is_labelled_and_intersected_with_valid():
    valid = np.ones(100, dtype=bool); valid[10] = False
    sel = select_vectors(valid, subaperture=(5, 20))
    assert sel.policy == "subaperture" and sel.count == 14 and sel.runs == [(5, 10), (11, 20)]


def test_subaperture_out_of_range_rejected():
    with pytest.raises(ValueError):
        select_vectors(np.ones(10, dtype=bool), subaperture=(5, 11))
    with pytest.raises(ValueError):
        select_vectors(np.ones(10, dtype=bool), subaperture=(6, 6))
