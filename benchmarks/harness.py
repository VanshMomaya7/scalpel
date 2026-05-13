"""Benchmark harness: str_replace vs scalpel vs measure_edit on 10 fixture files."""
from __future__ import annotations

import csv
import pathlib
import sys
import tempfile
from dataclasses import asdict, dataclass

import libcst as cst
import tiktoken
from libcst.metadata import MetadataWrapper, PositionProvider

from scalpel.core import edit_class_method, edit_function_body, measure_edit

TASKS_DIR = pathlib.Path(__file__).parent / "tasks"
RESULTS_DIR = pathlib.Path(__file__).parent / "results"
RESULTS_CSV = RESULTS_DIR / "benchmark.csv"

_enc = tiktoken.get_encoding("cl100k_base")


# ── data types ────────────────────────────────────────────────────────────────


@dataclass
class Symbol:
    fn_name: str
    class_name: str | None  # None = top-level function
    start_line: int
    body_start_line: int  # first line inside the IndentedBlock (after the signature)
    end_line: int


@dataclass
class Row:
    file: str
    function: str
    approach: str
    success: bool
    input_tokens: int
    output_tokens: int
    total_tokens: int
    blast_radius: float | None
    patch_locality: float | None
    error: str | None


# ── helpers ───────────────────────────────────────────────────────────────────


def _t(text: str) -> int:
    return len(_enc.encode(text))


def _label(sym: Symbol) -> str:
    return f"{sym.class_name}.{sym.fn_name}" if sym.class_name else sym.fn_name


def collect_symbols(path: pathlib.Path) -> list[Symbol]:
    source = path.read_text(encoding="utf-8")
    tree = cst.parse_module(source)
    wrapper = MetadataWrapper(tree)
    positions = wrapper.resolve(PositionProvider)
    syms: list[Symbol] = []
    for stmt in wrapper.module.body:
        if isinstance(stmt, cst.FunctionDef):
            rng = positions[stmt]
            body_rng = positions[stmt.body]
            syms.append(
                Symbol(stmt.name.value, None, rng.start.line, body_rng.start.line, rng.end.line)
            )
        elif isinstance(stmt, cst.ClassDef):
            for item in stmt.body.body:
                if isinstance(item, cst.FunctionDef):
                    rng = positions[item]
                    body_rng = positions[item.body]
                    syms.append(
                        Symbol(
                            item.name.value,
                            stmt.name.value,
                            rng.start.line,
                            body_rng.start.line,
                            rng.end.line,
                        )
                    )
    return syms


def extract_texts(source: str, sym: Symbol) -> tuple[str, str]:
    """Return (full_fn_text, body_only) using exact line numbers from libcst."""
    lines = source.splitlines(keepends=True)
    full_fn_text = "".join(lines[sym.start_line - 1 : sym.end_line])
    body_text = "".join(lines[sym.body_start_line - 1 : sym.end_line])
    return full_fn_text, body_text


def make_new_body(body_text: str) -> str:
    """Prepend a no-op statement so the body is visibly different."""
    indent = "    "
    for line in body_text.splitlines():
        if line.strip():
            indent = " " * (len(line) - len(line.lstrip()))
            break
    return f"{indent}_ = None\n" + body_text


# ── per-approach runners ──────────────────────────────────────────────────────


def run_str_replace(
    source: str, sym: Symbol, full_fn_text: str, body_text: str, new_body: str
) -> Row:
    # Replace only the body portion within the full function text
    new_full = full_fn_text.replace(body_text, new_body, 1)
    new_source = source.replace(full_fn_text, new_full, 1)
    success = (full_fn_text in source) and (new_source != source)

    input_t = _t(source + body_text + new_body)
    output_t = _t(new_source)
    return Row(
        file="",
        function=_label(sym),
        approach="str_replace",
        success=success,
        input_tokens=input_t,
        output_tokens=output_t,
        total_tokens=input_t + output_t,
        blast_radius=None,
        patch_locality=None,
        error=None if success else "replacement string not found",
    )


def run_scalpel(source: str, sym: Symbol, new_body: str) -> Row:
    with tempfile.NamedTemporaryFile(
        suffix=".py", mode="w", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(source)
        tmp_path = tmp.name

    try:
        if sym.class_name:
            result = edit_class_method(tmp_path, sym.class_name, sym.fn_name, new_body)
        else:
            result = edit_function_body(tmp_path, sym.fn_name, new_body)
    finally:
        pathlib.Path(tmp_path).unlink(missing_ok=True)

    if not result.success:
        return Row(
            file="",
            function=_label(sym),
            approach="scalpel",
            success=False,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            blast_radius=None,
            patch_locality=None,
            error=result.error,
        )

    diff_t = _t(result.diff)
    # token_cost = _t(source + fn_name + new_body) + _t(diff)
    total_t = result.token_cost or 0
    input_t = total_t - diff_t
    return Row(
        file="",
        function=_label(sym),
        approach="scalpel",
        success=True,
        input_tokens=max(0, input_t),
        output_tokens=diff_t,
        total_tokens=total_t,
        blast_radius=result.blast_radius,
        patch_locality=result.patch_locality,
        error=None,
    )


def run_measure(path: pathlib.Path, source: str, sym: Symbol, new_body: str) -> Row:
    # measure_edit only supports top-level functions
    if sym.class_name is not None:
        return Row(
            file="",
            function=_label(sym),
            approach="measure_edit",
            success=False,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            blast_radius=None,
            patch_locality=None,
            error="measure_edit: class methods not supported",
        )

    result = measure_edit(str(path), sym.fn_name, new_body)
    if not result.success:
        return Row(
            file="",
            function=_label(sym),
            approach="measure_edit",
            success=False,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            blast_radius=None,
            patch_locality=None,
            error=result.error,
        )

    diff_t = _t(result.diff)
    total_t = result.token_cost or 0
    input_t = total_t - diff_t
    return Row(
        file="",
        function=_label(sym),
        approach="measure_edit",
        success=True,
        input_tokens=max(0, input_t),
        output_tokens=diff_t,
        total_tokens=total_t,
        blast_radius=result.blast_radius,
        patch_locality=result.patch_locality,
        error=None,
    )


# ── summary printer ───────────────────────────────────────────────────────────


def print_summary(rows: list[Row]) -> None:
    approaches = ["str_replace", "scalpel", "measure_edit"]
    col_w = 18

    header = (
        f"{'Approach':<{col_w}}| {'Avg Input Tokens':>17} | "
        f"{'Avg Total Tokens':>17} | {'Success Rate':>12}"
    )
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)

    avgs: dict[str, tuple[float, float]] = {}
    for approach in approaches:
        subset = [r for r in rows if r.approach == approach]
        if not subset:
            continue
        success_count = sum(1 for r in subset if r.success)
        successful = [r for r in subset if r.success]
        avg_in = sum(r.input_tokens for r in successful) / len(successful) if successful else 0.0
        avg_total = sum(r.total_tokens for r in successful) / len(successful) if successful else 0.0
        rate = f"{100 * success_count // len(subset)}%"
        print(
            f"{approach:<{col_w}}| {avg_in:>17.0f} | {avg_total:>17.0f} | {rate:>12}"
        )
        avgs[approach] = (avg_in, avg_total)

    print(sep)

    if "str_replace" in avgs and "scalpel" in avgs:
        sr_total = avgs["str_replace"][1]
        sc_total = avgs["scalpel"][1]
        if sr_total > 0:
            reduction = 100.0 * (sr_total - sc_total) / sr_total
            print(f"Token reduction (scalpel vs str_replace):  {reduction:.1f}%")

    print(sep)


# ── main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    task_files = sorted(TASKS_DIR.glob("*.py"))
    if not task_files:
        print("No task files found in", TASKS_DIR, file=sys.stderr)
        sys.exit(1)

    all_rows: list[Row] = []

    for task_path in task_files:
        source = task_path.read_text(encoding="utf-8")
        symbols = collect_symbols(task_path)
        file_label = task_path.name

        for sym in symbols:
            full_fn_text, body_text = extract_texts(source, sym)
            new_body = make_new_body(body_text)

            for row in (
                run_str_replace(source, sym, full_fn_text, body_text, new_body),
                run_scalpel(source, sym, new_body),
                run_measure(task_path, source, sym, new_body),
            ):
                row.file = file_label
                all_rows.append(row)

    # Write CSV
    fieldnames = [f.name for f in Row.__dataclass_fields__.values()]  # type: ignore[attr-defined]
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(asdict(row))

    print(f"\nResults written to: {RESULTS_CSV}")
    total_fns = len(all_rows) // 3
    print(f"Benchmarked {len(task_files)} files, {total_fns} functions/methods\n")
    print_summary(all_rows)


if __name__ == "__main__":
    main()
