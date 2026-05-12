"""
Verify libcst round-trips on three stdlib files.
parse → serialize must be byte-identical to the original source.
"""
from __future__ import annotations

import importlib.util
import sys

import libcst as cst

TARGETS = ["pathlib", "json", "typing"]


def stdlib_path(module_name: str) -> str:
    spec = importlib.util.find_spec(module_name)
    if spec is None or spec.origin is None:
        raise RuntimeError(f"Cannot locate stdlib module: {module_name}")
    return spec.origin


def check(path: str) -> bool:
    source = open(path, encoding="utf-8").read()
    tree = cst.parse_module(source)
    return tree.code == source


def main() -> None:
    all_passed = True
    for name in TARGETS:
        path = stdlib_path(name)
        passed = check(path)
        symbol = "PASS" if passed else "FAIL"
        print(f"[{symbol}] {path}")
        if not passed:
            all_passed = False
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
