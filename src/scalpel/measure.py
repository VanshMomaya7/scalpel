"""Metrics: blast_radius, patch_locality, token_cost."""
from __future__ import annotations

__all__ = ["blast_radius", "patch_locality", "token_cost"]


def blast_radius(before: str, after: str) -> float:
    raise NotImplementedError("blast_radius not yet implemented")


def patch_locality(diff: str, total_lines: int) -> float:
    raise NotImplementedError("patch_locality not yet implemented")


def token_cost(input_text: str, diff_output: str) -> int:
    raise NotImplementedError("token_cost not yet implemented")
