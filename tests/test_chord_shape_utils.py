"""Tests para chord_shape_utils."""

from jazz21.guitar.utils import compact_interval_label, compute_intervals_notes


def test_compute_intervals_notes_c_major_open():
    intervals, notes = compute_intervals_notes("C", [-1, 3, 2, 0, 1, 0])
    assert len(intervals) == 6
    assert len(notes) == 6
    assert intervals[0] == ""
    assert notes[0] == ""
    # Cuerdas al aire / posiciones típicas del acorde de Do mayor
    assert "C" in notes
    assert "R" in intervals or "1" in "".join(intervals)


def test_compute_intervals_notes_muted_strings():
    intervals, notes = compute_intervals_notes("Am7", [-1, -1, 2, 0, 1, 0])
    assert intervals[0] == "" and notes[0] == ""
    assert intervals[1] == "" and notes[1] == ""


def test_compute_intervals_notes_invalid_figure():
    intervals, notes = compute_intervals_notes("not_a_chord_symbol___", [0, 0, 0, 0, 0, 0])
    assert intervals == [""] * 6
    assert notes == [""] * 6


def test_compact_interval_label_maps_quality():
    assert compact_interval_label("M3") == "3"
    assert compact_interval_label("m3") == "b3"
    assert compact_interval_label("P5") == "5"
    assert compact_interval_label("d5") == "b5"
    assert compact_interval_label("R") == "R"
