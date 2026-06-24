"""Tests para guitar_shape_resolve (helpers y mapping de calidad)."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

import jazz21.guitar.resolve as gsr


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("major", "major"),
        ("minor", "minor"),
        ("dominant", "dom7"),
        ("dominant-seventh", "dom7"),
        ("major-seventh", "maj7"),
        ("minor-ninth", "min7"),
        ("major-ninth", "maj7"),
        ("minor-seventh", "min7"),
        ("diminished", "dim"),
        ("augmented", "aug"),
        ("half-diminished", None),
        ("diminished-seventh", "dim"),
        ("", None),
    ],
)
def test_music21_kind_to_quality(kind, expected):
    assert gsr.music21_kind_to_quality(kind) == expected


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("major-sixth", "major"),
        ("minor-sixth", "minor"),
        ("suspended-fourth", "major"),
        ("dominant-suspended-fourth", "dom7"),
        ("half-diminished-seventh", "dim"),
    ],
)
def test_music21_kind_to_caged_approx(kind, expected):
    q, _hint = gsr.music21_kind_to_caged_approx(kind)
    assert q == expected


@pytest.mark.parametrize(
    "root_pc,pcs,expected",
    [
        (7, {7, 10, 2, 5}, "min7"),   # G Bb D F
        (7, {7, 10, 2}, "minor"),     # G Bb D
        (2, {2, 6, 9, 0}, "dom7"),    # D F# A C
        (3, {3, 7, 10, 1}, "dom7"),   # Eb G Bb C#
        (7, {7, 9, 2}, None),         # G A D — sin 3ª clara
    ],
)
def test_infer_caged_quality_from_pcs(root_pc, pcs, expected):
    q, _ = gsr.infer_caged_quality_from_pcs(root_pc, pcs)
    assert q == expected


def test_resolve_caged_quality_prefers_notes_over_sixth_label():
    r = gsr.resolve_caged_quality(
        kind="major-sixth",
        root_pc=3,
        sound_pcs={3, 7, 10, 1},
    )
    assert r["quality"] == "dom7"
    assert r["source"] == "notes"


def test_resolve_caged_quality_partial_voicing_keeps_dom7():
    r = gsr.resolve_caged_quality(
        kind="dominant-seventh",
        root_pc=2,
        sound_pcs={2, 6, 9, 7},  # D F# A G — triada sin 7ª
    )
    assert r["quality"] == "dom7"
    assert r["source"] == "kind"
    assert "parcial" in r["hint"].lower()


def test_resolve_caged_quality_extension_keeps_min7():
    r = gsr.resolve_caged_quality(
        kind="minor-seventh",
        root_pc=7,
        sound_pcs={7, 1, 10, 5},  # G Db Bb F — sugiere dim pero es m7+#11
    )
    assert r["quality"] == "min7"
    assert r["source"] == "kind"


@pytest.mark.parametrize(
    "target,source,expected_delta",
    [
        (0, 0, 0),
        (5, 0, 5),
        (0, 7, 5),
        (0, 11, 1),
        (7, 0, -5),
    ],
)
def test_shortest_pc_delta(target, source, expected_delta):
    assert gsr._shortest_pc_delta(target, source) == expected_delta


def test_transpose_frets_barre_base_simple():
    tmpl = [0, 2, 2, 1, 0, 0]  # patrón tipo forma E
    out = gsr._transpose_frets_barre_base(tmpl, None, 2)
    assert out is not None
    abs_new, barre_out, base_out = out
    assert len(abs_new) == 6
    assert barre_out is None
    assert all(x >= -1 for x in abs_new)


def test_transpose_frets_barre_base_em7_down_fifth_bm7_octave_fixup():
    """Em7 + −5 semitonos ⇒ acorde raíz Si: cuerdas al aire quedan negativas sin +12k."""
    em7 = [0, 2, 2, 0, 3, 0]
    out = gsr._transpose_frets_barre_base(em7, None, -5)
    assert out is not None
    frets, _, _ = out
    assert all(x == -1 or 0 <= x <= 24 for x in frets)


def test_transpose_frets_barre_base_ebmaj7_from_e_shape():
    """Emaj7 forma E −1 semitono ⇒ trastes negativos en cuerdas al aire; subir octava."""
    e_maj7 = [0, 2, 1, 1, 0, 0]
    out = gsr._transpose_frets_barre_base(e_maj7, None, -1)
    assert out is not None
    frets, _, _ = out
    assert max(f for f in frets if f >= 0) <= 24


def test_transpose_frets_barre_base_all_muted_fails():
    assert gsr._transpose_frets_barre_base([-1, -1, -1, -1, -1, -1], None, 0) is None


def test_transpose_frets_barre_base_high_delta_normalizes_down():
    """Analogía cejilla alta + salto tonal: antes se rechazaba por nf > 24."""
    tmpl = [20, 0, 0, 0, 0, 0]
    out = gsr._transpose_frets_barre_base(tmpl, None, 12)
    assert out is not None
    abs_new, _, _ = out
    assert max(f for f in abs_new if f >= 0) <= 24


def test_root_pc_from_chordshape_name_c_major():
    pc = gsr._root_pc_from_chordshape_name("C")
    assert pc == 0


def test_root_pc_from_chordshape_name_bb():
    pc = gsr._root_pc_from_chordshape_name("Bb")
    assert pc == 10


def test_diagram_review_reasons_gmaj7b13():
    rr = gsr.diagram_review_reasons(symbol_display="Gmaj7b13", kind_raw="major-seventh")
    assert rr
    assert any("extens" in m.lower() or "símbolo" in m.lower() for m in rr)


def test_diagram_review_reasons_slash_only():
    rr = gsr.diagram_review_reasons(symbol_display="Am7/D", kind_raw="minor-seventh")
    assert any("slash" in m.lower() for m in rr)


def test_ordered_caged_candidates_prefers_matching_root_pc():
    em7 = SimpleNamespace(shape="E", name="Em7", orden=0)
    dm7 = SimpleNamespace(shape="D", name="Dm7", orden=0)
    out = gsr._ordered_caged_candidates([em7, dm7], root_pc_i=2)
    assert out[0].shape == "D"


@patch.object(gsr, "render_chord_shape_svg", return_value="<svg>t</svg>")
@patch.object(gsr, "render_chord_shape_model_svg", return_value="<svg>m</svg>")
def test_resolve_one_chord_shape_cycle_rotates_template(
    _mock_model_svg, _mock_svg
):
    """Dm7: candidato con raíz figurada D primero; índice 1 usa otra plantilla (Em7 → trasponer)."""
    dm7 = SimpleNamespace(
        shape="D",
        name="Dm7",
        orden=0,
        frets=[1, 1, 2, 0, 3, 1],
        fingers=[0, 0, 0, 0, 0, 0],
        barre=None,
        base_fret=1,
    )
    em7 = SimpleNamespace(
        shape="E",
        name="Em7",
        orden=0,
        frets=[0, 2, 2, 0, 3, 0],
        fingers=[0, 0, 0, 0, 0, 0],
        barre=None,
        base_fret=1,
    )
    by_q = {"min7": [em7, dm7]}
    chord = {"kind": "minor-seventh", "root_pc": 2, "symbol": "Dm7"}
    g0, err0 = gsr._resolve_one_chord(chord, by_q, shape_cycle=0)
    g1, err1 = gsr._resolve_one_chord(chord, by_q, shape_cycle=1)
    assert err0 is None and err1 is None
    assert g0["caged_shape"] == "D"
    assert g0["matched"] is True
    assert g1["caged_shape"] == "E"
    assert g1["matched"] is False
    assert g1["transposed"] is True
    assert len(g0["diagram_frets"]) == 6
    assert len(g1["diagram_frets"]) == 6


@patch.object(gsr, "render_chord_shape_svg", return_value="<svg>t</svg>")
@patch.object(gsr, "render_chord_shape_model_svg", return_value="<svg>m</svg>")
def test_resolve_one_chord_negative_shape_cycle_wraps(
    _mock_model_svg, _mock_svg
):
    dm7 = SimpleNamespace(
        shape="D",
        name="Dm7",
        orden=0,
        frets=[1, 1, 2, 0, 3, 1],
        fingers=[0, 0, 0, 0, 0, 0],
        barre=None,
        base_fret=1,
    )
    em7 = SimpleNamespace(
        shape="E",
        name="Em7",
        orden=0,
        frets=[0, 2, 2, 0, 3, 0],
        fingers=[0, 0, 0, 0, 0, 0],
        barre=None,
        base_fret=1,
    )
    by_q = {"min7": [em7, dm7]}
    chord = {"kind": "minor-seventh", "root_pc": 2, "symbol": "Dm7"}
    # cycle 0 → D, cycle -1 → E (dos plantillas)
    ge, _ = gsr._resolve_one_chord(chord, by_q, shape_cycle=-1)
    assert ge is not None
    assert ge["caged_shape"] == "E"
