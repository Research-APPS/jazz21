#!/usr/bin/env python3
"""Fail if a public function or class in ``__all__`` lacks a docstring."""

from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

MODULES = (
    "jazz21",
    "jazz21.notation",
    "jazz21.notation.compose_engine",
    "jazz21.symbols",
    "jazz21.guitar",
    "jazz21.guitar.resolve",
)

SKIP_NAMES = frozenset({"__version__", "DEFAULT_MAX_CHORDS"})


def main() -> int:
    sys.path.insert(0, str(SRC))
    errors: list[str] = []
    for mod_name in MODULES:
        mod = importlib.import_module(mod_name)
        all_names = getattr(mod, "__all__", None)
        if not all_names:
            errors.append(f"{mod_name}: missing __all__")
            continue
        for name in all_names:
            if name in SKIP_NAMES or name.startswith("_"):
                continue
            obj = getattr(mod, name, None)
            if obj is None:
                errors.append(f"{mod_name}.{name}: not found on module")
                continue
            if not (inspect.isfunction(obj) or inspect.isclass(obj) or inspect.ismethod(obj)):
                continue
            doc = inspect.getdoc(obj)
            if not doc or not doc.strip():
                errors.append(f"{mod_name}.{name}: missing docstring")
    if errors:
        print("API docstring check failed:")
        for e in errors:
            print(" ", e)
        return 1
    print("API docstring check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
