"""Smoke tests: every name in package ``__all__`` is importable."""

from __future__ import annotations

import importlib
import pkgutil

import pytest

import jazz21
import jazz21.guitar
import jazz21.notation
import jazz21.notation.compose_engine
import jazz21.symbols
from jazz21.guitar import resolve as guitar_resolve


@pytest.mark.parametrize("name", jazz21.__all__)
def test_jazz21_root_exports(name: str) -> None:
    obj = getattr(jazz21, name)
    assert obj is not None or name == "__version__"


@pytest.mark.parametrize("name", jazz21.notation.__all__)
def test_notation_exports(name: str) -> None:
    assert hasattr(jazz21.notation, name)
    assert callable(getattr(jazz21.notation, name)) or name == "DEFAULT_MAX_CHORDS"


@pytest.mark.parametrize("name", jazz21.symbols.__all__)
def test_symbols_exports(name: str) -> None:
    assert callable(getattr(jazz21.symbols, name))


@pytest.mark.parametrize("name", jazz21.guitar.__all__)
def test_guitar_exports(name: str) -> None:
    obj = getattr(jazz21.guitar, name)
    assert obj is not None


@pytest.mark.parametrize("name", guitar_resolve.__all__)
def test_guitar_resolve_exports(name: str) -> None:
    assert callable(getattr(guitar_resolve, name))


@pytest.mark.parametrize("name", jazz21.notation.compose_engine.__all__)
def test_compose_engine_all_matches_notation(name: str) -> None:
    assert name in jazz21.notation.__all__
    assert hasattr(jazz21.notation.compose_engine, name)


def test_resolve_one_chord_public_alias() -> None:
    assert guitar_resolve.resolve_one_chord is guitar_resolve._resolve_one_chord
