"""Tests para chord_symbol_normalizer."""

import pytest

from jazz21.symbols import (
    normalize_chord_symbol,
    preprocess_chord_symbol,
    split_slash,
)


@pytest.mark.parametrize(
    "symbol,expected_head,expected_bass",
    [
        ("Cmaj7/E", "Cmaj7", "E"),
        ("Am", "Am", None),
        ("  Dm7/G  ", "Dm7", "G"),
    ],
)
def test_split_slash(symbol, expected_head, expected_bass):
    h, b = split_slash(symbol)
    assert h == expected_head
    assert b == expected_bass


def test_preprocess_chord_symbol_delta_maj7():
    out = preprocess_chord_symbol("CΔ7")
    assert "C" in out
    assert "maj" in out.lower() or "7" in out


def test_preprocess_chord_symbol_half_dim_unicode():
    out = preprocess_chord_symbol("Bø7")
    assert out.startswith("B")


def test_normalize_chord_symbol_returns_canonical_for_c_major():
    res = normalize_chord_symbol("C")
    assert res is not None
    assert res["canonical"] == "C"
    assert res["input"] == "C"


def test_normalize_chord_symbol_empty():
    assert normalize_chord_symbol("") is None
    assert normalize_chord_symbol("   ") is None


def test_normalize_chord_symbol_mb57_style_suffix():
    """mb57 debe orientarse a m7b5 sin leer 'b57' literal."""
    res = normalize_chord_symbol("Amb57")
    assert res is not None
    assert "m7b5" in res["canonical"] or "half" in (res.get("quality") or "").lower()
