"""CAGED chord shape records and built-in seed catalog."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from jazz21.guitar.utils import compute_intervals_notes

# shape, quality, name, music21 figure, frets, fingers, barre, base_fret
CAGED_SEED_ROWS: list[tuple] = [
    ("C", "major", "C", "C", [-1, 3, 2, 0, 1, 0], [0, 3, 2, 0, 1, 0], None, 1),
    ("C", "minor", "Cm", "Cm", [-1, 3, 5, 5, 4, 3], [0, 1, 4, 3, 2, 1], None, 1),
    ("C", "dom7", "C7", "C7", [-1, 3, 2, 3, 1, 0], [0, 3, 2, 4, 1, 0], None, 1),
    ("C", "maj7", "Cmaj7", "Cmaj7", [-1, 3, 2, 0, 0, 0], [0, 3, 2, 0, 0, 0], None, 1),
    ("C", "min7", "Cm7", "Cm7", [-1, 3, 5, 3, 4, 3], [0, 1, 3, 1, 2, 1], None, 1),
    ("C", "dim", "C°", "Cdim", [-1, 3, 4, 2, 4, 3], [0, 2, 4, 1, 4, 3], None, 1),
    ("C", "aug", "C+", "Caug", [-1, 3, 2, 1, 1, 0], [0, 3, 2, 1, 1, 0], None, 1),
    ("A", "major", "A", "A", [-1, 0, 2, 2, 2, 0], [0, 0, 1, 2, 3, 0], None, 1),
    ("A", "minor", "Am", "Am", [-1, 0, 2, 2, 1, 0], [0, 0, 2, 3, 1, 0], None, 1),
    ("A", "dom7", "A7", "A7", [-1, 0, 2, 0, 2, 0], [0, 0, 2, 0, 3, 0], None, 1),
    ("A", "maj7", "Amaj7", "Amaj7", [-1, 0, 2, 1, 2, 0], [0, 0, 2, 1, 3, 0], None, 1),
    ("A", "min7", "Am7", "Am7", [-1, 0, 2, 0, 1, 0], [0, 0, 2, 0, 1, 0], None, 1),
    ("A", "dim", "A°", "Adim", [-1, 0, 1, 2, 1, 2], [0, 0, 1, 3, 2, 4], None, 1),
    ("A", "aug", "A+", "Aaug", [-1, 0, 3, 2, 2, 1], [0, 0, 3, 1, 2, 1], None, 1),
    ("G", "major", "G", "G", [3, 2, 0, 0, 0, 3], [2, 1, 0, 0, 0, 4], None, 1),
    ("G", "minor", "Gm", "Gm", [3, 5, 5, 3, 3, 3], [1, 3, 4, 1, 2, 1], [3, 1, 6], 1),
    ("G", "dom7", "G7", "G7", [3, 2, 0, 0, 0, 1], [2, 1, 0, 0, 0, 1], None, 1),
    ("G", "maj7", "Gmaj7", "Gmaj7", [3, -1, 0, 0, 0, 2], [3, 0, 0, 0, 0, 4], None, 1),
    ("G", "min7", "Gm7", "Gm7", [3, -1, 3, 3, 3, -1], [2, 0, 3, 3, 3, 0], None, 1),
    ("G", "dim", "G°", "Gdim", [3, -1, 2, 3, 2, 0], [2, 0, 1, 4, 3, 0], None, 1),
    ("G", "aug", "G+", "Gaug", [3, 2, 1, 0, 0, 3], [4, 2, 1, 0, 0, 4], None, 1),
    ("E", "major", "E", "E", [0, 2, 2, 1, 0, 0], [0, 2, 3, 1, 0, 0], None, 1),
    ("E", "minor", "Em", "Em", [0, 2, 2, 0, 0, 0], [0, 2, 3, 0, 0, 0], None, 1),
    ("E", "dom7", "E7", "E7", [0, 2, 0, 1, 0, 0], [0, 2, 0, 1, 0, 0], None, 1),
    ("E", "maj7", "Emaj7", "Emaj7", [0, 2, 1, 1, 0, 0], [0, 2, 1, 1, 0, 0], None, 1),
    ("E", "min7", "Em7", "Em7", [0, 2, 2, 0, 3, 0], [0, 2, 3, 0, 4, 0], None, 1),
    ("E", "dim", "E°", "Edim", [-1, -1, 2, 3, 2, 3], [0, 0, 1, 3, 2, 4], None, 1),
    ("E", "aug", "E+", "Eaug", [0, 3, 2, 1, 1, 0], [0, 3, 2, 1, 1, 0], None, 1),
    ("D", "major", "D", "D", [-1, -1, 0, 2, 3, 2], [0, 0, 0, 1, 2, 3], None, 1),
    ("D", "minor", "Dm", "Dm", [-1, -1, 0, 2, 3, 1], [0, 0, 0, 1, 3, 1], None, 1),
    ("D", "dom7", "D7", "D7", [-1, -1, 0, 2, 1, 2], [0, 0, 0, 2, 1, 3], None, 1),
    ("D", "maj7", "Dmaj7", "Dmaj7", [-1, -1, 0, 2, 2, 2], [0, 0, 0, 1, 1, 1], [2, 4, 6], 1),
    ("D", "min7", "Dm7", "Dm7", [-1, -1, 0, 2, 1, 1], [0, 0, 0, 2, 1, 1], None, 1),
    ("D", "dim", "D°", "Ddim", [-1, -1, 0, 1, 0, 1], [0, 0, 0, 1, 0, 2], None, 1),
    ("D", "aug", "D+", "Daug", [-1, -1, 0, 3, 3, 2], [0, 0, 0, 2, 3, 4], None, 1),
]


@dataclass
class ChordShapeRecord:
    """Portable CAGED (or other) guitar shape — no ORM dependency.

    Attributes:
        name: Display name (e.g. ``"Cmaj7"``).
        quality: Catalog quality key (``"maj7"``, ``"min7"``, …).
        shape: CAGED letter (``"C"``, ``"A"``, ``"G"``, ``"E"``, ``"D"``).
        frets: Six string frets, low E to high E; ``-1`` = muted.
        fingers: Fingering per string (optional).
        base_fret: Nut position for diagram rendering.
        intervals, notes: Computed from the music21 figure and frets.
    """

    name: str
    quality: str
    shape: str
    frets: list[int]
    fingers: list[int] = field(default_factory=list)
    system: str = "caged"
    inversion: str = "root"
    base_fret: int = 1
    intervals: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    playable: bool = True
    orden: int = 0
    barre: list[int] | tuple[int, int, int] | None = None


def chord_shape_from_row(row: tuple, *, orden: int) -> ChordShapeRecord:
    """Build a :class:`ChordShapeRecord` from a ``CAGED_SEED_ROWS`` tuple."""
    sh, quality, name, figure, frets, fingers, barre, base_fret = row
    intervals, notes_list = compute_intervals_notes(figure, list(frets))
    return ChordShapeRecord(
        name=name,
        quality=quality,
        shape=sh,
        frets=list(frets),
        fingers=list(fingers),
        base_fret=int(base_fret),
        intervals=list(intervals),
        notes=list(notes_list),
        barre=list(barre) if barre else None,
        orden=orden,
        playable=True,
        system="caged",
        inversion="root",
    )


def chord_shape_from_mapping(obj: Any) -> ChordShapeRecord:
    """Build from any object with ChordShape-like attributes (e.g. Django model)."""
    return ChordShapeRecord(
        name=str(getattr(obj, "name", "")),
        quality=str(getattr(obj, "quality", "")),
        shape=str(getattr(obj, "shape", "")),
        frets=list(getattr(obj, "frets", []) or []),
        fingers=list(getattr(obj, "fingers", []) or []),
        system=str(getattr(obj, "system", "caged")),
        inversion=str(getattr(obj, "inversion", "root")),
        base_fret=int(getattr(obj, "base_fret", None) or 1),
        intervals=list(getattr(obj, "intervals", []) or []),
        notes=list(getattr(obj, "notes", []) or []),
        playable=bool(getattr(obj, "playable", True)),
        orden=int(getattr(obj, "orden", 0) or 0),
        barre=getattr(obj, "barre", None),
    )


class ShapesCatalog:
    """In-memory catalog of guitar chord shapes."""

    def __init__(self, shapes: list[ChordShapeRecord]) -> None:
        self._shapes = list(shapes)

    @classmethod
    def default_caged(cls) -> ShapesCatalog:
        """Return the built-in CAGED seed catalog shipped with jazz21."""
        shapes = [
            chord_shape_from_row(row, orden=i)
            for i, row in enumerate(CAGED_SEED_ROWS)
        ]
        return cls(shapes)

    def playable_shapes(self, *, system: str = "caged") -> list[ChordShapeRecord]:
        """Return shapes marked playable for the given fretboard system."""
        return [
            s
            for s in self._shapes
            if s.playable and s.system == system
        ]

    def __iter__(self) -> Iterator[ChordShapeRecord]:
        return iter(self._shapes)
