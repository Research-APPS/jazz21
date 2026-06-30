"""Vocabulario conceptual de jazz21 sobre teoría armónica.

Definiciones originales con voz propia de jazz21, fundamentadas en fuentes
académicas (Riemann, DCML, Piston, Tymoczko). No copiar — citar y reinterpretar.
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Concept:
    id: str
    name_es: str
    name_en: str
    definition_es: str
    examples: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"Concept(id={self.id!r}, name_es={self.name_es!r})"


CONCEPTS: dict[str, Concept] = {
    c.id: c
    for c in [
        Concept(
            id="harmonic_function",
            name_es="Función armónica",
            name_en="Harmonic function",
            definition_es=(
                "Papel estructural que desempeña un acorde dentro de un contexto tonal o modal. "
                "En jazz21 distinguimos tres funciones primarias: Tónica (T) — reposo y resolución; "
                "Subdominante (SD) — movimiento y apertura; Dominante (D) — tensión hacia la tónica. "
                "La función depende del contexto: un mismo acorde puede tener funciones distintas "
                "en tonalidades o modos diferentes."
            ),
            examples=["G7 → C (D→T)", "Dm → G7 (SD→D)", "E7 → Am (D secundaria → VI)"],
            sources=["Riemann 1893 · Vereinfachte Harmonielehre", "DCML Harmony Annotation Standard", "Piston 1941 · Harmony"],
        ),
        Concept(
            id="diatonic_chord",
            name_es="Acorde diatónico",
            name_en="Diatonic chord",
            definition_es=(
                "Acorde cuyos pitch-classes pertenecen íntegramente a la escala activa. "
                "En jazz21 comprobamos diatonicidad por subconjunto de pitch-classes (enfoque CHORDIA): "
                "un acorde es diatónico si y solo si el conjunto {raíz, tercera, quinta, séptima...} "
                "está contenido en el conjunto de notas de la escala. "
                "Bm en C mayor no es diatónico porque F# (pc 6) no pertenece a C jónico."
            ),
            examples=["Dm7 en C mayor (D·F·A·C ⊆ escala)", "Bm en C mayor ✗ (F# ∉ escala)"],
            sources=["DCML Harmony Annotation Standard", "music21 · ChordSymbol pitch-class analysis"],
        ),
        Concept(
            id="modal_borrowing",
            name_es="Préstamo modal",
            name_en="Modal borrowing",
            definition_es=(
                "Uso de un acorde procedente de un modo paralelo (misma tónica, escala distinta). "
                "El acorde no es diatónico en el modo activo pero sí lo es en otro modo con la misma raíz. "
                "En jazz21 detectamos el modo de procedencia comparando los pitch-classes del acorde "
                "contra todas las escalas paralelas."
            ),
            examples=["Bb en C mayor (préstamo de C Mixolidio o C Eólico)", "Ab en C mayor (préstamo de C Eólico / C Frigio)"],
            sources=["Tymoczko 2011 · A Geometry of Music", "DCML Harmony Annotation Standard"],
        ),
        Concept(
            id="secondary_dominant",
            name_es="Dominante secundaria",
            name_en="Secondary dominant",
            definition_es=(
                "Acorde dominante (con tercera mayor y, en jazz, frecuentemente séptima menor) "
                "que resuelve hacia un grado diatónico distinto de la tónica. "
                "Se denota V/X, donde X es el grado al que resuelve. "
                "En jazz21 la detectamos cuando la raíz tiene tercera mayor y la quinta justa abajo "
                "es un grado diatónico de la tonalidad activa."
            ),
            examples=["E7 → Am en C mayor (V/VI)", "A7 → Dm en C mayor (V/II)", "D7 → G en C mayor (V/V)"],
            sources=["Piston 1941 · Harmony", "Riemann 1893 · Vereinfachte Harmonielehre", "DCML Harmony Annotation Standard"],
        ),
        Concept(
            id="harmonic_degree",
            name_es="Grado armónico",
            name_en="Harmonic degree",
            definition_es=(
                "Posición de un acorde dentro de una escala, expresada en número romano. "
                "El grado identifica la raíz del acorde por su distancia en semitonos a la tónica "
                "(enfoque pitch-class de CHORDIA): G13 y G7 son ambos V en C mayor "
                "porque sus raíces comparten el mismo pitch-class. "
                "Las alteraciones (bIII, #IV, bVII...) indican grados modificados en modos no jónicos."
            ),
            examples=["I=C, II=Dm, III=Em, IV=F, V=G, VI=Am, VII=Bdim en C jónico", "bIII=Eb, bVII=Bb en C eólico"],
            sources=["DCML Harmony Annotation Standard", "music21 · RomanNumeral"],
        ),
        Concept(
            id="modal_scale",
            name_es="Escala modal",
            name_en="Modal scale",
            definition_es=(
                "Una de las siete escalas derivadas de rotar el patrón de tonos y semitonos de la escala mayor. "
                "Cada modo tiene una sonoridad y un conjunto de grados característicos. "
                "En jazz21 soportamos los siete modos eclesiásticos: jónico, dórico, frigio, lidio, "
                "mixolidio, eólico y locrio. Solo jónico y eólico tienen etiquetas de función T/SD/D; "
                "los demás muestran únicamente grado romano."
            ),
            examples=["C Dórico: C·D·Eb·F·G·A·Bb (bIII, bVII)", "C Lidio: C·D·E·F#·G·A·B (#IV)"],
            sources=["Tymoczko 2011 · A Geometry of Music", "music21 · DorianScale, LydianScale..."],
        ),
    ]
}


def concept(id: str) -> Concept:
    """Devuelve el concepto por id, o lanza KeyError si no existe."""
    return CONCEPTS[id]
