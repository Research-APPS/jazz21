"""jazz21 — jazz and lead-sheet notation on top of music21."""

from jazz21.manifest import (
    describe_chord,
    resolve_guitar_shapes,
    to_manifest,
    notas_de,
    triadas_de,
    cuatriadas_de,
    analizar_en_tonalidad,
    analizar_progresion,
    detectar_patron_progresion,
    progresion_para_ui,
    sugerencias_contextuales,
    notas_audio_de,
)
from jazz21 import concepts

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "describe_chord",
    "resolve_guitar_shapes",
    "to_manifest",
    "notas_de",
    "triadas_de",
    "cuatriadas_de",
    "analizar_en_tonalidad",
    "analizar_progresion",
    "detectar_patron_progresion",
    "progresion_para_ui",
    "sugerencias_contextuales",
    "notas_audio_de",
    "concepts",
]
