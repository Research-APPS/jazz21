"""Guitar: CAGED shapes, SVG diagrams, resolution from chord metadata."""

from jazz21.guitar.render import render_chord_shape_svg
from jazz21.guitar.resolve import attach_guitar_shapes_to_chords, resolve_one_chord
from jazz21.guitar.shapes import ChordShapeRecord, ShapesCatalog, chord_shape_from_row

__all__ = [
    "ChordShapeRecord",
    "ShapesCatalog",
    "attach_guitar_shapes_to_chords",
    "chord_shape_from_row",
    "render_chord_shape_svg",
    "resolve_one_chord",
]
