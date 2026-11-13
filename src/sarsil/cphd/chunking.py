"""Vector selection and memory-bounded chunk planning.

Policy (DECISIONS / roadmap): the default selection is every valid vector of the
channel. A chunk is a memory-management unit, never a separate aperture.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Memory budget for one in-memory chunk. A conservative placeholder, not a
# performance-derived value; it must stay configurable.
DEFAULT_CHUNK_BUDGET_BYTES = 256 * 2**20


def plan_chunks(n_vectors: int, bytes_per_vector: int,
                memory_budget_bytes: int = DEFAULT_CHUNK_BUDGET_BYTES) -> list[tuple[int, int]]:
    """Split range(n_vectors) into contiguous [start, stop) chunks within the budget.

    A budget smaller than one vector still yields single-vector chunks.
    """
    if n_vectors < 0:
        raise ValueError("n_vectors must be >= 0")
    if bytes_per_vector <= 0:
        raise ValueError("bytes_per_vector must be > 0")
    if memory_budget_bytes <= 0:
        raise ValueError("memory_budget_bytes must be > 0")
    per = max(1, memory_budget_bytes // bytes_per_vector)
    return [(a, min(a + per, n_vectors)) for a in range(0, n_vectors, per)]


def contiguous_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """[start, stop) runs where mask is True."""
    m = np.asarray(mask, dtype=bool)
    if m.size == 0:
        return []
    edges = np.flatnonzero(np.diff(np.concatenate(([False], m, [False])).astype(np.int8)))
    return [(int(a), int(b)) for a, b in zip(edges[::2], edges[1::2])]


@dataclass(frozen=True)
class VectorSelection:
    runs: list[tuple[int, int]]
    count: int
    policy: str  # "full" (default) or "subaperture" (explicit user choice)

    def to_dict(self) -> dict:
        return {"runs": [list(r) for r in self.runs], "count": self.count, "policy": self.policy}


def select_vectors(valid_mask: np.ndarray, subaperture: tuple[int, int] | None = None) -> VectorSelection:
    """Default: all valid vectors. An explicit [start, stop) subaperture is labelled as such."""
    valid = np.asarray(valid_mask, dtype=bool)
    if subaperture is None:
        return VectorSelection(contiguous_runs(valid), int(valid.sum()), "full")
    a, b = subaperture
    if not (0 <= a < b <= valid.size):
        raise ValueError(f"subaperture {subaperture} outside [0, {valid.size}] or empty")
    sub = np.zeros_like(valid)
    sub[a:b] = valid[a:b]
    return VectorSelection(contiguous_runs(sub), int(sub.sum()), "subaperture")
