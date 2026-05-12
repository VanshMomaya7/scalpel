from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EditResult:
    success: bool
    syntax_valid: bool
    diff: str                    # unified diff, empty string if no change
    error: str | None            # None on success
    blast_radius: float | None   # fraction of file's symbols whose sig changed
    patch_locality: float | None  # 1 - (changed_line_range / total_lines)
    token_cost: int | None       # tiktoken count: input_tokens + output_tokens
