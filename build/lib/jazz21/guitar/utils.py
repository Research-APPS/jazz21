"""Utilidades para ChordShape: intervalos y notas por cuerda (music21)."""

from __future__ import annotations

from music21 import harmony, interval, pitch

# Cuerdas Mi(bajo) → mi(alto); MIDI al aire.
OPEN_MIDI = [40, 45, 50, 55, 59, 64]


def compute_intervals_notes(figure: str, frets: list[int]) -> tuple[list[str], list[str]]:
    """
    ``figure``: símbolo que entiende music21 (p. ej. Cmaj7, Adim, Gaug).
    ``frets``: 6 enteros, -1 = mute, 0 = al aire.
    """
    intervals: list[str] = []
    notes_list: list[str] = []
    try:
        ch = harmony.ChordSymbol(figure)
    except Exception:
        return [""] * 6, [""] * 6
    root = ch.root()
    if root is None:
        return [""] * 6, [""] * 6
    for i, fr in enumerate(frets):
        if fr < 0:
            intervals.append("")
            notes_list.append("")
            continue
        p_play = pitch.Pitch(midi=OPEN_MIDI[i] + fr)
        notes_list.append(p_play.name)
        try:
            iv = interval.Interval(root, p_play)
            lab = iv.simpleName
            if lab in ("P1", "P8"):
                lab = "R"
            intervals.append(lab)
        except Exception:
            intervals.append("")
    return intervals, notes_list


def compact_interval_label(music21_simple: str) -> str:
    """
    Convierte el nombre simple de intervalo de music21 (M3, m7, P5…) en etiqueta
    compacta de grado (3, b7, 5…) respecto a la raíz.
    """
    if not music21_simple:
        return ""
    s = music21_simple.strip()
    table = {
        "R": "R",
        "P1": "R",
        "P8": "R",
        "m2": "b2",
        "M2": "2",
        "m3": "b3",
        "M3": "3",
        "P4": "4",
        "d4": "b4",
        "A4": "#4",
        "d5": "b5",
        "P5": "5",
        "A5": "#5",
        "m6": "b6",
        "M6": "6",
        "m7": "b7",
        "M7": "maj7",
    }
    return table.get(s, s)
