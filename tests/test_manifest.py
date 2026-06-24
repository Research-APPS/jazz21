"""Tests for jazz21.manifest (SEO/GEO bridge)."""

from jazz21.manifest import describe_chord, resolve_guitar_shapes, to_manifest


def test_describe_chord_cmaj7():
    d = describe_chord("Cmaj7")
    assert d is not None
    assert d["canonical"] == "Cmaj7"
    assert d["intervals"]
    assert "music21_figure" in d


def test_resolve_guitar_shapes_cmaj7():
    r = resolve_guitar_shapes("Cmaj7")
    assert not r.get("unavailable")
    assert len(r["options"]) >= 1
    assert "<svg" in (r["options"][0].get("svg") or "").lower()


def test_to_manifest_smoke():
    m = to_manifest(["C", "Cm7", "G7alt"])
    assert len(m) == 3
    assert m[0]["chord"]["canonical"] == "C"
    assert "guitar" in m[0]
    assert m[2]["chord"] is not None
