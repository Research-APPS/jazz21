"""Tests del motor de composición (parsing y figuras)."""

from jazz21.notation import (
    american_chord_to_music21_figure,
    advance_chord_inversion,
    analyze_chord_inversion_step,
    build_inversion_tour_plan,
    chord_inversion_cycle_length,
    measures_from_progression,
    normalize_progression,
    parse_progression_to_musicxml,
    parse_lead_sheet,
    progression_to_midi_bytes,
    replace_chord_with_next_inversion,
    replace_chord_with_next_inversion_detail,
    strip_trailing_chord_dots,
    tokenize_progression,
    total_inversion_tour_steps,
)
from jazz21.notation.compose_engine import (
    _format_roman_display,
    _simplify_music21_figure_digits,
)


def test_normalize_progression_double_space_becomes_bar():
    assert "|" in normalize_progression("C  G")


def test_strip_trailing_chord_dots():
    assert strip_trailing_chord_dots("Cmaj7.") == "Cmaj7"


def test_parse_lead_sheet_percent_repeat():
    p = parse_lead_sheet("C | %")
    assert len(p["expanded"]) == 2
    assert p["expanded"][1] == p["expanded"][0]


def test_measures_from_progression_pipe_chords():
    m = measures_from_progression("C | G Am")
    assert m == [["C"], ["G", "Am"]]


def test_tokenize_progression_flat():
    t = tokenize_progression("| Dm7 | G7 | C |")
    assert t == ["Dm7", "G7", "C"]


def test_american_chord_to_music21_figure_b_flat():
    assert "B-" in american_chord_to_music21_figure("Bb")
    assert "Bb" not in american_chord_to_music21_figure("Bb")


def test_american_chord_to_music21_figure_with_slash():
    fig = american_chord_to_music21_figure("F#m7/B")
    assert "F#" in fig
    assert "/" in fig


def test_american_chord_to_music21_figure_slash_bass_flat():
    """music21 no acepta Gm/Bb ('mb'); el bajo con bemol debe ir como B-."""
    assert american_chord_to_music21_figure("Gm/Bb") == "Gm/B-"


def test_american_jazz_aliases_convert_for_music21():
    assert "M9/" in american_chord_to_music21_figure("Bbmaj9/D")
    assert american_chord_to_music21_figure("G7alt/B").startswith("G7/")
    assert american_chord_to_music21_figure("C#º7") == "C#dim7"


def test_american_minor_major_seventh_aliases():
    """mmaj7 = menor + 7ª mayor; music21 no reconoce 'mmaj7' pero sí 'mM7'."""
    assert american_chord_to_music21_figure("Bmmaj7") == "BmM7"
    assert american_chord_to_music21_figure("Bmmaj7/A#") == "BmM7/A#"
    assert american_chord_to_music21_figure("Bm ( maj7 )") == "BmM7"
    assert american_chord_to_music21_figure("EbminMaj11") == "E-minmaj11"


def test_american_extended_suspended_dominant_aliases():
    """C13sus4-style compact jazz; music21 needs explícitos 7sus4add9add13."""
    assert american_chord_to_music21_figure("C13sus4") == "C7sus4add9add13"
    assert american_chord_to_music21_figure("Bb13sus") == "B-7sus4add9add13"
    assert american_chord_to_music21_figure("C 9 Sus 4") == "C7sus4add9"


def test_parse_progression_accepts_bmmaj7_and_am13():
    prog = (
        "Am7 D7 | Gmaj7 | E | | Am| Bmmaj7 | || | | Am13"
    )
    toks = tokenize_progression(prog)
    out = parse_progression_to_musicxml(prog, title="mM7 smoke")
    assert len(out["chords"]) == len(toks)
    assert not (out.get("errors") or [])


def test_dense_jazz_progression_parses_every_chord_chip():
    """Todos los tokens deben generar entrada en ``chords`` (chips de inversión)."""
    prog = (
        "Dm9 G13b9/B | Cmaj9/E C#º7 |Dm7 C#13 | Cmaj9 G7alt/B |Cm9 F13 | "
        "Bbmaj9/D Bbm9/Db |Abm9 C#13b9/F | Gbmaj9/Bb E7alt | Amaj9/C# C#7b9 | "
        "F#m9 B13 |Emaj9/G# G#7alt | C#m9 F#13 | Bmaj9/D# Bb13 | Ebmaj9/G Ab13 |"
        "Dbmaj9/F Fm9 Bb13 | Ebmaj9/G Eº7"
    )
    toks = tokenize_progression(prog)
    out = parse_progression_to_musicxml(prog, title="Jazz dense")
    assert len(out["chords"]) == len(toks)
    assert not (out.get("errors") or [])


def test_parse_gm_slash_bb_after_inversion_smoke():
    """Inversión de Gm → Gm/Bb en texto; el motor debe seguir generando XML y chips."""
    inv = replace_chord_with_next_inversion("Gm", 0)
    assert inv is not None
    assert "Bb" in inv or "B♭" in inv
    out = parse_progression_to_musicxml(inv, title="Test")
    assert len(out["chords"]) == 1
    assert "<score-partwise" in out["musicxml"] or "score-partwise" in out["musicxml"]


def test_simplify_bVII7532_to_9():
    assert "9" in _simplify_music21_figure_digits("bVII7532")


def test_format_roman_display_delta_from_maj7():
    assert "Δ" in _format_roman_display("iimaj7")


def test_replace_chord_with_next_inversion_flat_index():
    new_p = replace_chord_with_next_inversion("C", 0)
    assert new_p is not None
    assert "C/E" in new_p


def test_replace_chord_inversion_detail_index_out_of_range():
    r = replace_chord_with_next_inversion_detail("| C |", 99)
    assert r["ok"] is False
    assert r["reason"] == "index_out_of_range"
    assert r["symbol"] is None


def test_replace_chord_inversion_detail_parse_error_includes_symbol():
    r = replace_chord_with_next_inversion_detail("| ZzzInvalidChord |", 0)
    assert r["ok"] is False
    assert r["reason"] == "parse_error"
    assert r["symbol"] == "ZzzInvalidChord"
    assert r["flat_index"] == 0


def test_advance_chord_inversion_direct():
    nxt = advance_chord_inversion("C")
    assert nxt in ("C/E", "C/G")
    nxt = advance_chord_inversion("C")
    assert nxt in ("C/E", "C/G")


def test_chord_inversion_cycle_length_triad_vs_seventh():
    assert chord_inversion_cycle_length("C") == 3
    n_cm7 = chord_inversion_cycle_length("Cmaj7")
    assert n_cm7 == 4


def test_build_inversion_tour_plan_sums_lengths():
    prog = "| C Am7 | Dm7 |"
    plan = build_inversion_tour_plan(prog)
    assert [x[0] for x in plan] == [0, 1, 2]
    assert sum(x[1] for x in plan) == total_inversion_tour_steps(prog)
    assert sum(x[1] for x in plan) == (
        chord_inversion_cycle_length("C")
        + chord_inversion_cycle_length("Am7")
        + chord_inversion_cycle_length("Dm7")
    )


def test_full_inversion_cycle_restores_chord_symbol():
    """n avances en el mismo slot devuelven al símbolo inicial (rotación completa)."""
    start = "Cmaj7"
    n = chord_inversion_cycle_length(start)
    assert n == 4
    prog = f"| {start} |"
    cur = prog
    for _ in range(n):
        nxt = replace_chord_with_next_inversion(cur, 0)
        assert nxt is not None
        cur = nxt
    flat_tokens = [t for meas in measures_from_progression(cur) for t in meas]
    assert flat_tokens == [start]


def test_extended_dominant_slash_inversion_uses_pitch_rotation_fallback():
    cases = [
        ("C13", "C13/D", "pitch_rotation"),
        ("C13b9", "C13b9/D", "pitch_rotation"),
        ("C7b9/Db", "C7b9/E", "pitch_rotation"),
        ("C7sus4", "C7sus4/F", "pitch_rotation"),
        ("C5", "C5/G", "pitch_rotation"),
        ("Cmmaj7/B", "Cmmaj7", "pitch_rotation"),
        ("Cadd9/G", "Cadd9", "pitch_rotation"),
    ]
    for tok, expect_next, engine in cases:
        r = analyze_chord_inversion_step(tok)
        assert r.get("ok") is True, tok
        assert r.get("next_symbol") == expect_next, (tok, r)
        assert r.get("inversion_engine") == engine, r


def test_full_inversion_cycle_extended_chord_still_closes():
    """Tras n rotaciones (fallback o music21) debe volver el head del símbolo inicial."""
    start = "C13"
    n = chord_inversion_cycle_length(start)
    assert n == 7
    prog = f"| {start} |"
    cur = prog
    for _ in range(n):
        nxt = replace_chord_with_next_inversion(cur, 0)
        assert nxt is not None
        cur = nxt
    flat_tokens = [t for meas in measures_from_progression(cur) for t in meas]
    assert flat_tokens == [start]


def test_parse_progression_includes_inversion_cycle_len():
    out = parse_progression_to_musicxml("| C G7 |", title="t")
    assert not (out.get("errors") or [])
    ch = out.get("chords") or []
    assert len(ch) == 2
    assert ch[0].get("inversion_cycle_len") == 3
    assert ch[1].get("inversion_cycle_len") == chord_inversion_cycle_length("G7")


def test_c5_musicxml_not_marked_kind_none_for_osmd():
    """Quintas tipo C5: music21 escribe kind=none → OSMD muestra N.C.; se sanea antes de servir."""
    out = parse_progression_to_musicxml("| C5 |", title="t")
    assert "<kind>none</kind>" not in out["musicxml"]
    rw = out.get("render_warnings") or []
    assert any("«C5»" in x or "C5»" in x for x in rw)


def test_parse_progression_to_musicxml_smoke():
    out = parse_progression_to_musicxml("| C | G |", title="Test")
    assert "musicxml" in out
    assert isinstance(out["musicxml"], str)
    assert "<score-partwise" in out["musicxml"] or "score-partwise" in out["musicxml"]
    assert "chords" in out and len(out["chords"]) >= 1
    assert out["chords"][0].get("symbol") == "C"


def test_progression_to_midi_bytes_smoke():
    raw, err = progression_to_midi_bytes("| Am | Dm | E7 | Am |", title="Test")
    assert err is None
    assert raw is not None
    assert len(raw) > 100
    assert raw[:4] == b"MThd"
