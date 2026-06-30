"""Structured chord descriptions for SEO, GEO, and downstream publishers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from jazz21.guitar.resolve import resolve_one_chord
from jazz21.guitar.shapes import ShapesCatalog
from jazz21.notation.compose_engine import american_chord_to_music21_figure
from jazz21.symbols import normalize_chord_symbol

# Semitones from tonic → (roman numeral, harmonic function) for major keys (Ionian).
# Mirrors CHORDIA's cadence_detection.MAJOR_DEGREES.
_MAJOR_DEGREES: dict[int, tuple[str, str]] = {
    0:  ("I",    "Tónica"),
    2:  ("II",   "Subdominante"),
    4:  ("III",  "Tónica"),
    5:  ("IV",   "Subdominante"),
    7:  ("V",    "Dominante"),
    9:  ("VI",   "Tónica"),
    11: ("VII",  "Subdominante"),  # viiø7 prepara a V, no lo sustituye
}

# Semitones from tonic → (roman numeral, harmonic function) for natural minor (Aeolian).
# V (natural) = Tónica porque sin sensible no genera tensión dominante clásica.
# bVII = None: no tiene sensible ni tritono; su función depende del contexto melódico.
# E7 (armónico) aparece como no-diatónico y se analiza por contexto (V→I en menor).
_AEOLIAN_DEGREES: dict[int, tuple[str, str]] = {
    0:  ("I",    "Tónica"),
    2:  ("II",   "Subdominante"),
    3:  ("bIII", "Tónica"),
    5:  ("IV",   "Subdominante"),
    7:  ("V",    None),          # V natural: sin sensible, función ambigua
    8:  ("bVI",  "Subdominante"),
    10: ("bVII", None),          # bVII: contraste modal, no dominante clásica
}

# Semitones from tonic → roman numeral only (modos sin función T/SD/D fija).
_MODE_DEGREES: dict[str, dict[int, str]] = {
    "ionian":     {0:"I",  2:"II",  4:"III",  5:"IV",  7:"V",   9:"VI",  11:"VII"},
    "dorian":     {0:"I",  2:"II",  3:"bIII", 5:"IV",  7:"V",   9:"VI",  10:"bVII"},
    "phrygian":   {0:"I",  1:"bII", 3:"bIII", 5:"IV",  7:"V",   8:"bVI", 10:"bVII"},
    "lydian":     {0:"I",  2:"II",  4:"III",  6:"#IV", 7:"V",   9:"VI",  11:"VII"},
    "mixolydian": {0:"I",  2:"II",  4:"III",  5:"IV",  7:"V",   9:"VI",  10:"bVII"},
    "aeolian":    {0:"I",  2:"II",  3:"bIII", 5:"IV",  7:"V",   8:"bVI", 10:"bVII"},
    "locrian":    {0:"I",  1:"bII", 3:"bIII", 5:"IV",  6:"bV",  8:"bVI", 10:"bVII"},
}

# Modos con función armónica completa T/SD/D (los dos modos "estándar").
_FUNCTIONAL_MODES: dict[str, dict[int, tuple[str, str]]] = {
    "ionian":  _MAJOR_DEGREES,
    "aeolian": _AEOLIAN_DEGREES,
}

# Intervalos cuyo grado diatónico lleva acorde menor/disminuido → V/minúscula en V/X.
_TARGET_MINOR_INTERVALS: dict[str, frozenset[int]] = {
    "ionian":     frozenset({2, 4, 9}),
    "dorian":     frozenset({0, 2, 4, 9}),
    "phrygian":   frozenset({0, 1, 5, 8}),
    "lydian":     frozenset({0, 2, 4, 9}),
    "mixolydian": frozenset({0, 2, 4, 9}),
    "aeolian":    frozenset({0, 2, 5, 7}),
    "locrian":    frozenset({0, 1, 3, 5, 6, 8, 10}),
}

# Dominantes 7 en eje de tercia (Coltrane / modulación) — intervalo raíz→tónica.
_CAMBIO_TERCERA_INTERVALS: frozenset[int] = frozenset({3, 4, 8, 9})

def _m21_pitch_to_jazz(name: str) -> str:
    """Convierte nombre de pitch music21 ('E-') a notación jazz ('Eb')."""
    return name.replace("-", "b")


def _get_m21_scale(tonalidad: str, modo: str):
    """Devuelve la instancia music21 Scale para el modo dado."""
    from music21 import scale as m21s
    _MAP = {
        "ionian":     m21s.MajorScale,
        "dorian":     m21s.DorianScale,
        "phrygian":   m21s.PhrygianScale,
        "lydian":     m21s.LydianScale,
        "mixolydian": m21s.MixolydianScale,
        "aeolian":    m21s.MinorScale,
        "locrian":    m21s.LocrianScale,
    }
    return _MAP.get(modo, m21s.MajorScale)(tonalidad)


def _suffix_from_intervals(ivls: tuple[int, ...]) -> str:
    """Infiere el sufijo de acorde a partir de los intervalos sobre la raíz."""
    return {
        (4, 7):       "",
        (3, 7):       "m",
        (3, 6):       "dim",
        (4, 8):       "aug",
        (4, 7, 11):   "maj7",
        (3, 7, 10):   "m7",
        (4, 7, 10):   "7",
        (3, 6, 10):   "m7b5",
        (3, 6, 9):    "dim7",
        (4, 8, 11):   "maj7#5",
        (4, 8, 10):   "7#5",
    }.get(ivls, "")


def _diatonic_chords(tonalidad: str, seventh: bool = False, modo: str = "ionian") -> list[dict[str, Any]]:
    """Construye los 7 acordes diatónicos de cualquier modo apilando terceras."""
    from music21 import pitch as m21p

    sc = _get_m21_scale(tonalidad, modo)
    pitches = [sc.pitchFromDegree(i) for i in range(1, 8)]
    tonic_pc  = int(m21p.Pitch(tonalidad).pitchClass)
    degree_map = _MODE_DEGREES.get(modo, _MODE_DEGREES["ionian"])

    result = []
    for i in range(7):
        root_pc = pitches[i].pitchClass
        # apilar terceras diatónicas
        idx = [i, (i + 2) % 7, (i + 4) % 7]
        if seventh:
            idx.append((i + 6) % 7)
        ivls = tuple(sorted((pitches[j].pitchClass - root_pc) % 12 for j in idx[1:]))
        suffix    = _suffix_from_intervals(ivls)
        root_name = _m21_pitch_to_jazz(pitches[i].name)
        simbolo   = root_name + suffix
        desc      = describe_chord(simbolo) or {}
        interval  = (root_pc - tonic_pc) % 12
        grado     = degree_map.get(interval, str(i + 1))
        fn_map    = _FUNCTIONAL_MODES.get(modo)
        funcion   = fn_map[interval][1] if fn_map and interval in fn_map else None
        result.append({
            "simbolo":    simbolo,
            "grado":      grado,
            "funcion":    funcion,
            "notas":      desc.get("pitches") or [],
            "intervalos": desc.get("intervals") or [],
        })
    return result


def notas_de(tonalidad: str, modo: str = "ionian") -> list[str]:
    """Devuelve las 7 notas de una escala modal.

    Args:
        tonalidad: Tónica (e.g. ``"C"``, ``"F#"``, ``"Bb"``).
        modo:      Modo de la escala — ``"ionian"``, ``"dorian"``, ``"phrygian"``,
                   ``"lydian"``, ``"mixolydian"``, ``"aeolian"``, ``"locrian"``.

    Returns:
        Lista de 7 strings con los nombres de las notas en notación jazz
        (e.g. ``["C", "D", "Eb", "F", "G", "A", "Bb"]`` para C Dórico).
    """
    sc = _get_m21_scale(tonalidad, modo)
    return [_m21_pitch_to_jazz(p.name) for p in sc.getPitches()[:7]]


def triadas_de(tonalidad: str, modo: str = "ionian") -> list[dict[str, Any]]:
    """Devuelve las 7 triadas diatónicas de una tonalidad y modo.

    Args:
        tonalidad: Tónica (e.g. ``"C"``, ``"Bb"``, ``"F#"``).
        modo:      Modo de la escala (por defecto ``"ionian"``).

    Returns:
        Lista de 7 dicts con ``simbolo``, ``grado``, ``funcion``,
        ``notas`` e ``intervalos``.
    """
    return _diatonic_chords(tonalidad, seventh=False, modo=modo)


def cuatriadas_de(tonalidad: str, modo: str = "ionian") -> list[dict[str, Any]]:
    """Devuelve las 7 cuatriadas diatónicas (acordes de séptima) de una tonalidad y modo.

    Args:
        tonalidad: Tónica (e.g. ``"C"``, ``"Bb"``, ``"F#"``).
        modo:      Modo de la escala (por defecto ``"ionian"``).

    Returns:
        Lista de 7 dicts con ``simbolo``, ``grado``, ``funcion``,
        ``notas`` e ``intervalos``.
    """
    return _diatonic_chords(tonalidad, seventh=True, modo=modo)


def _is_dom7(root_pc: int, chord_pcs: frozenset[int]) -> bool:
    """Acorde dominante: tercera mayor + séptima menor sobre la raíz."""
    return (root_pc + 4) % 12 in chord_pcs and (root_pc + 10) % 12 in chord_pcs


def _chord_pitch_info(simbolo: str) -> tuple[int, frozenset[int], Any] | None:
    """Raíz (pitch-class), pitch-classes del acorde e instancia ChordSymbol."""
    from music21 import harmony as m21h

    desc = describe_chord(simbolo)
    if not desc or not desc.get("music21_figure"):
        return None
    try:
        cs = m21h.ChordSymbol(desc["music21_figure"])
        root = cs.root()
        if root is None:
            return None
        root_pc = int(root.pitchClass)
        chord_pcs = frozenset(int(p.pitchClass) for p in cs.pitches)
        return root_pc, chord_pcs, cs
    except Exception:
        return None


def _is_tonic_center(root_pc: int, chord_pcs: frozenset[int]) -> bool:
    """Centro tonal mayor: triada mayor o maj7 (no menor ni dominante)."""
    if (root_pc + 3) % 12 in chord_pcs:
        return False
    if (root_pc + 4) % 12 not in chord_pcs:
        return False
    if (root_pc + 10) % 12 in chord_pcs:
        return False
    return True


def _chord_diatonic_in_key(
    root_pc: int,
    chord_pcs: frozenset[int],
    tonic_pc: int,
    modo: str,
) -> bool:
    """True si raíz y notas pertenecen al modo activo."""
    degree_map = _MODE_DEGREES.get(modo, _MODE_DEGREES["ionian"])
    interval = (root_pc - tonic_pc) % 12
    if interval not in degree_map:
        return False
    sc = _get_m21_scale_from_pc(tonic_pc, modo)
    scale_pcs = frozenset(int(p.pitchClass) for p in sc.getPitches())
    return chord_pcs.issubset(scale_pcs)


def _get_m21_scale_from_pc(tonic_pc: int, modo: str):
    """Escala modal a partir de pitch-class de tónica."""
    from music21 import pitch as m21p

    tonic_name = _m21_pitch_to_jazz(m21p.Pitch(tonic_pc).name)
    return _get_m21_scale(tonic_name, modo)


def _analizar_por_resolucion(
    root_pc: int,
    chord_pcs: frozenset[int],
    tonic_pc: int,
    degree_map: dict[int, str],
    modo: str,
    scale_pcs: frozenset[int],
    siguiente: str,
) -> dict[str, Any] | None:
    """Clasifica un acorde no diatónico según su resolución al acorde siguiente.

    Orden: SubV (½ tono) → Backdoor → V/X (quinta abajo, diatónico) → cambio tonal.
    """
    nxt = _chord_pitch_info(siguiente)
    if nxt is None:
        return None
    next_pc, next_pcs, _ = nxt

    if not _is_dom7(root_pc, chord_pcs):
        return None

    half_step_down = (root_pc - next_pc) % 12

    # SubV → I o cadena cromática de dominantes
    if half_step_down == 1:
        if next_pc == tonic_pc:
            tonic_degree = degree_map.get(0, "I")
            return {
                "label":   "SubV",
                "detalle": f"SubV→{tonic_degree} (½ tono)",
                "tipo":    "tritone_substitution",
            }
        if _is_dom7(next_pc, next_pcs):
            return {
                "label":   None,
                "detalle": "Cadena cromática de dominantes",
                "tipo":    None,
            }

    # Backdoor: bVII7 sube tono a I
    if (
        modo == "ionian"
        and (root_pc - tonic_pc) % 12 == 10
        and next_pc == tonic_pc
        and (next_pc - root_pc) % 12 == 2
    ):
        return {
            "label":   "Backdoor",
            "detalle": "Dominante backdoor (bVII7→I)",
            "tipo":    "backdoor_dominant",
        }

    # Quinta justa abajo → siguiente acorde
    if next_pc == (root_pc + 5) % 12:
        target_interval = (next_pc - tonic_pc) % 12
        next_diatonic = (
            target_interval in degree_map
            and next_pcs.issubset(scale_pcs)
        )

        if next_diatonic and target_interval != 0:
            root_interval = (root_pc - tonic_pc) % 12
            if root_interval != 0:
                target_degree = _roman_for_v_of(
                    degree_map[target_interval], target_interval, modo,
                )
                return {
                    "label":   f"V/{target_degree}",
                    "detalle": f"Dominante secundaria → {target_degree}",
                    "tipo":    "dominante_secundaria",
                }

        if not next_diatonic and _is_tonic_center(next_pc, next_pcs):
            return {
                "label":   None,
                "detalle": "Dominante hacia nuevo centro tonal",
                "tipo":    "cambio_tonal",
            }

    return None


def _static_non_diatonic(
    root_pc: int,
    chord_pcs: frozenset[int],
    interval: int,
    tonic_pc: int,
    degree_map: dict[int, str],
    modo: str,
    *,
    allow_secondary: bool = True,
) -> dict[str, Any] | None:
    """Análisis sin contexto de progresión (fallback)."""
    sec = _melodic_minor_tonic(root_pc, chord_pcs, interval, modo)
    if sec is None:
        sec = _tritone_substitution(root_pc, chord_pcs, tonic_pc, degree_map)
    if sec is None and allow_secondary:
        sec = _secondary_dominant(root_pc, chord_pcs, tonic_pc, degree_map, modo)
    if sec is None and interval == 7:
        maj3_pc = (root_pc + 4) % 12
        if maj3_pc in chord_pcs:
            sec = {
                "label":   "Dominante",
                "detalle": "Dominante principal (menor armónico)",
                "tipo":    "tonal",
            }
    if sec is None:
        sec = _backdoor_dominant(root_pc, chord_pcs, tonic_pc, modo)
    if sec is None:
        sec = _cambio_por_tercera(root_pc, chord_pcs, tonic_pc, modo)
    return sec


def _roman_for_v_of(degree: str, target_interval: int, modo: str) -> str:
    """Formatea el grado objetivo en V/X (minúscula si el grado diatónico es menor)."""
    minor_ivls = _TARGET_MINOR_INTERVALS.get(modo, _TARGET_MINOR_INTERVALS["ionian"])
    if target_interval not in minor_ivls:
        return degree
    prefix = ""
    roman = degree
    if degree and degree[0] in "b#":
        prefix, roman = degree[0], degree[1:]
    return prefix + roman.lower()


def _tritone_substitution(
    root_pc: int,
    chord_pcs: frozenset[int],
    tonic_pc: int,
    degree_map: dict[int, str],
) -> dict[str, Any] | None:
    """SubV: dom7 a tritono de V7 que resuelve a la tónica (p.ej. Db7 por G7→C)."""
    if not _is_dom7(root_pc, chord_pcs):
        return None

    primary_dom_pc = (root_pc + 6) % 12
    ultimate_pc    = (primary_dom_pc + 5) % 12
    if (ultimate_pc - tonic_pc) % 12 != 0:
        return None
    if (primary_dom_pc - tonic_pc) % 12 != 7:
        return None

    tonic_degree = degree_map.get(0, "I")
    return {
        "label":   "SubV",
        "detalle": f"Sustitución de tritono de V7→{tonic_degree}",
        "tipo":    "tritone_substitution",
    }


def _backdoor_dominant(
    root_pc: int,
    chord_pcs: frozenset[int],
    tonic_pc: int,
    modo: str,
) -> dict[str, Any] | None:
    """Backdoor: bVII7→I en mayor (p.ej. Bb7→Cmaj7)."""
    if modo != "ionian" or not _is_dom7(root_pc, chord_pcs):
        return None
    if (root_pc - tonic_pc) % 12 != 10:
        return None
    return {
        "label":   "Backdoor",
        "detalle": "Dominante backdoor (bVII7→I)",
        "tipo":    "backdoor_dominant",
    }


def _cambio_por_tercera(
    root_pc: int,
    chord_pcs: frozenset[int],
    tonic_pc: int,
    modo: str,
) -> dict[str, Any] | None:
    """Dom7 en eje de tercia mayor — modulación / ciclo de Coltrane, no préstamo modal."""
    if modo != "ionian" or not _is_dom7(root_pc, chord_pcs):
        return None
    if (root_pc - tonic_pc) % 12 not in _CAMBIO_TERCERA_INTERVALS:
        return None
    return {
        "label":   None,
        "detalle": "Dominante en eje de tercia (cambio tonal)",
        "tipo":    "cambio_tonal",
    }


def _melodic_minor_tonic(
    root_pc: int,
    chord_pcs: frozenset[int],
    interval: int,
    modo: str,
) -> dict[str, Any] | None:
    """i con maj7 en eólico — tónica de menor melódica (p.ej. AmM7 en A eólico)."""
    if modo != "aeolian" or interval != 0:
        return None
    if (root_pc + 3) % 12 not in chord_pcs or (root_pc + 11) % 12 not in chord_pcs:
        return None
    return {
        "label":   "Tónica",
        "detalle": "Tónica menor melódica (i maj7)",
        "tipo":    "tonal",
    }


def _secondary_dominant(
    root_pc: int,
    chord_pcs: frozenset[int],
    tonic_pc: int,
    degree_map: dict[int, str],
    modo: str = "ionian",
) -> dict[str, Any] | None:
    """Detecta si un acorde no diatónico actúa como dominante secundaria.

    Condición: dom7 (M3 + m7) cuya quinta justa abajo es un grado diatónico.

    Returns:
        Dict con ``label`` (e.g. ``"V/vi"``) y ``detalle``, o None.
    """
    if not _is_dom7(root_pc, chord_pcs):
        return None

    target_pc       = (root_pc + 5) % 12    # resolución: quinta abajo
    target_interval = (target_pc - tonic_pc) % 12

    if target_interval not in degree_map:
        return None                          # el objetivo no es un grado diatónico

    # V/I no es dominante secundaria: es simplemente la dominante principal
    if target_interval == 0:
        return None

    # I7: tónica con séptima de blues — no es V/IV aunque tenga tercera mayor
    root_interval = (root_pc - tonic_pc) % 12
    if root_interval == 0:
        return None

    target_degree = _roman_for_v_of(
        degree_map[target_interval], target_interval, modo,
    )
    return {
        "label":   f"V/{target_degree}",
        "detalle": f"Dominante secundaria → {target_degree}",
        "tipo":    "dominante_secundaria",
    }


_FUNCIONES_TONALES: frozenset[str] = frozenset({"Tónica", "Subdominante", "Dominante"})


def _tipo_funcion(
    funcion: str | None,
    sec: dict[str, Any] | None,
    hints: list[dict[str, Any]],
) -> str | None:
    """Clasifica el rol armónico del acorde en una categoría estable para UI/serialización.

    Valores posibles:
    - ``"tonal"``                  — función T/SD/D dentro del modo activo
    - ``"dominante_secundaria"``   — V/X resolviendo a un grado no-tónico
    - ``"tritone_substitution"``   — SubV de V7→I
    - ``"backdoor_dominant"``      — bVII7→I
    - ``"cambio_tonal"``           — dom7 en eje de tercia (Coltrane, etc.)
    - ``"prestamo_modal"``         — pitch-classes encajan en un modo paralelo
    - ``None``                     — sin clasificación identificada
    """
    if sec and sec.get("tipo"):
        return sec["tipo"]
    if funcion in _FUNCIONES_TONALES:
        return "tonal"
    if funcion and funcion.startswith("V/"):
        return "dominante_secundaria"
    if funcion == "SubV":
        return "tritone_substitution"
    if funcion == "Backdoor":
        return "backdoor_dominant"
    if any(h.get("tipo") == "modal" for h in hints):
        return "prestamo_modal"
    return None


def analizar_en_tonalidad(
    tonalidad: str,
    simbolo: str,
    modo: str = "ionian",
    *,
    anterior: str | None = None,
    siguiente: str | None = None,
) -> dict[str, Any]:
    """Analiza un acorde dentro de una tonalidad y modo.

    Usa comparación de pitch-class de la raíz (enfoque CHORDIA): G7, G9, G13
    son todos V en C mayor. Soporta los 7 modos: ionian, dorian, phrygian,
    lydian, mixolydian, aeolian, locrian.

    Con ``siguiente`` (y opcionalmente ``anterior``) la función armónica se
    infiere por resolución contextual; sin vecinos se usa el fallback estático.

    Args:
        tonalidad: Tónica (e.g. ``"C"``, ``"Bb"``).
        simbolo:   Símbolo de acorde (e.g. ``"G13"``, ``"Gb9"``).
        modo:      Modo de la escala (por defecto ``"ionian"``).
        anterior:  Acorde precedente en la progresión (opcional).
        siguiente: Acorde siguiente en la progresión (opcional).

    Returns:
        Dict con ``simbolo``, ``notas``, ``intervalos``.
        Si diatónico: ``diatonico=True``, ``grado``, ``funcion`` (None si no ionian).
        Si no diatónico: ``diatonico=False``, ``hints``.
    """
    _ = anterior  # reservado para reglas futuras (p.ej. ivm7–bVII7–I)
    from music21 import harmony as m21h, pitch as m21p

    desc = describe_chord(simbolo) or {}
    entry: dict[str, Any] = {
        "simbolo":    simbolo,
        "notas":      desc.get("pitches") or [],
        "intervalos": desc.get("intervals") or [],
    }

    m21_fig = desc.get("music21_figure")
    if not m21_fig:
        entry.update({"diatonico": False, "hints": [], "error": "Símbolo no reconocido"})
        return entry

    degree_map = _MODE_DEGREES.get(modo, _MODE_DEGREES["ionian"])

    try:
        cs        = m21h.ChordSymbol(m21_fig)
        root_pc   = int(cs.root().pitchClass)
        tonic_pc  = int(m21p.Pitch(tonalidad).pitchClass)
        interval  = (root_pc - tonic_pc) % 12

        sc        = _get_m21_scale(tonalidad, modo)
        scale_pcs = frozenset(int(p.pitchClass) for p in sc.getPitches())
        chord_pcs = frozenset(int(p.pitchClass) for p in cs.pitches)

        notas_fuera = [
            _m21_pitch_to_jazz(p.name)
            for p in cs.pitches
            if int(p.pitchClass) not in scale_pcs
        ]

        if interval in degree_map and chord_pcs.issubset(scale_pcs):
            # diatónico: raíz y todas las notas en la escala
            grado   = degree_map[interval]
            fn_map  = _FUNCTIONAL_MODES.get(modo)
            funcion = fn_map[interval][1] if fn_map and interval in fn_map else None
            entry.update({
                "diatonico":    True,
                "grado":        grado,
                "funcion":      funcion,
                "tipo_funcion": _tipo_funcion(funcion, None, []),
                "confianza":    "alta",
                "notas_fuera":  [],
                "hints":        [],
            })
        else:
            root_grado = degree_map.get(interval)
            sec: dict[str, Any] | None = None

            if siguiente:
                sec = _analizar_por_resolucion(
                    root_pc, chord_pcs, tonic_pc, degree_map, modo, scale_pcs, siguiente,
                )

            if sec is None:
                sec = _static_non_diatonic(
                    root_pc, chord_pcs, interval, tonic_pc, degree_map, modo,
                    allow_secondary=siguiente is None,
                )

            hints = _modal_hints(tonalidad, simbolo, cs)
            funcion = sec["label"] if sec else None
            confianza = "alta" if (sec and siguiente) else ("media" if sec else None)
            entry.update({
                "diatonico":       False,
                "grado":           root_grado,
                "funcion":         funcion,
                "tipo_funcion":    _tipo_funcion(funcion, sec, hints),
                "confianza":       confianza,
                "funcion_detalle": sec["detalle"] if sec else None,
                "hints":           hints,
                "notas_fuera":     notas_fuera,
            })
    except Exception as exc:
        entry.update({"diatonico": False, "grado": None, "funcion": None,
                      "tipo_funcion": None, "confianza": None, "hints": [], "error": str(exc)})

    return entry


def detectar_patron_progresion(
    tonalidad: str,
    acordes: list[str],
    modo: str = "ionian",
) -> str | None:
    """Detecta patrones globales de progresión (etiqueta de la secuencia completa).

    Patrones soportados: ``coltrane_cycle``. Los demás (blues_form, rhythm_changes…)
    se añadirán en iteraciones posteriores.
    """
    if modo != "ionian" or len(acordes) < 5:
        return None
    if _matches_coltrane_cycle(tonalidad, acordes):
        return "coltrane_cycle"
    return None


def _matches_coltrane_cycle(tonalidad: str, acordes: list[str]) -> bool:
    """Ciclo de centros tonales en tercias mayores unidos por V7→I locales."""
    from music21 import pitch as m21p

    tonic_pc = int(m21p.Pitch(tonalidad).pitchClass)
    aug_axis = {tonic_pc, (tonic_pc + 4) % 12, (tonic_pc + 8) % 12}

    centers: set[int] = set()
    dom7_to_foreign = 0

    for sym in acordes:
        info = _chord_pitch_info(sym)
        if info and _is_tonic_center(info[0], info[1]):
            centers.add(info[0])

    for i in range(len(acordes) - 1):
        cur = _chord_pitch_info(acordes[i])
        nxt = _chord_pitch_info(acordes[i + 1])
        if not cur or not nxt:
            continue
        r1, pcs1, _ = cur
        r2, pcs2, _ = nxt
        if not _is_dom7(r1, pcs1) or not _is_tonic_center(r2, pcs2):
            continue
        if r2 != (r1 + 5) % 12:
            continue
        if not _chord_diatonic_in_key(r2, pcs2, tonic_pc, "ionian"):
            dom7_to_foreign += 1

    on_axis = centers & aug_axis
    return len(on_axis) >= 3 and dom7_to_foreign >= 2


def analizar_progresion(
    tonalidad: str,
    acordes: list[str],
    modo: str = "ionian",
) -> dict[str, Any]:
    """Analiza una progresión completa con contexto prev/siguiente por acorde.

    Returns:
        Dict con ``patron`` (etiqueta global o None) y ``acordes`` (lista de análisis).
    """
    patron = detectar_patron_progresion(tonalidad, acordes, modo)
    n = len(acordes)
    analizados: list[dict[str, Any]] = []
    for i, sym in enumerate(acordes):
        anterior = acordes[i - 1] if i > 0 else None
        siguiente = acordes[i + 1] if i < n - 1 else None
        analizados.append(
            analizar_en_tonalidad(
                tonalidad, sym, modo, anterior=anterior, siguiente=siguiente,
            )
        )
    return {"patron": patron, "acordes": analizados}


_PC_TO_OCTAVE_NOTE: dict[str, str] = {
    "C": "C4", "C#": "C#4", "Db": "Db4",
    "D": "D4", "D#": "D#4", "Eb": "Eb4",
    "E": "E4", "F": "F4", "F#": "F#4", "Gb": "Gb4",
    "G": "G3", "G#": "G#3", "Ab": "Ab3",
    "A": "A3", "A#": "A#3", "Bb": "Bb3",
    "B": "B3",
}

_SUGERENCIA_QUALITIES: tuple[str, ...] = ("", "m", "7", "maj7", "m7", "dim", "m7b5")


def notas_audio_de(simbolo: str) -> list[str]:
    """Notas con octava para síntesis en navegador (Tone.js)."""
    desc = describe_chord(simbolo)
    if not desc:
        return []
    return [
        note for p in (desc.get("pitches") or [])[:4]
        if (note := _PC_TO_OCTAVE_NOTE.get(p))
    ]


def _chord_root_name(simbolo: str) -> str | None:
    desc = describe_chord(simbolo)
    if desc and desc.get("pitches"):
        return desc["pitches"][0]
    return None


def progresion_para_ui(
    tonalidad: str,
    acordes: list[str],
    modo: str = "ionian",
    nombre: str = "",
) -> dict[str, Any]:
    """Progresión analizada lista para el widget del sitio."""
    prog = analizar_progresion(tonalidad, acordes, modo)
    chord_list = []
    for sym, analisis in zip(acordes, prog["acordes"]):
        chord_list.append({
            "simbolo":      sym,
            "notas":        notas_audio_de(sym),
            "grado":        analisis.get("grado"),
            "funcion":      analisis.get("funcion"),
            "tipo_funcion": analisis.get("tipo_funcion"),
            "diatonico":    analisis.get("diatonico", False),
            "confianza":    analisis.get("confianza"),
            "hints":        analisis.get("hints") or [],
        })
    out: dict[str, Any] = {
        "nombre":    nombre,
        "tonalidad": tonalidad,
        "modo":      modo,
        "acordes":   chord_list,
    }
    if prog.get("patron"):
        out["patron"] = prog["patron"]
    return out


def sugerencias_contextuales(
    tonalidad: str,
    acordes: list[str],
    indice: int,
    modo: str = "ionian",
    *,
    max_sugerencias: int = 12,
) -> list[dict[str, Any]]:
    """Alternativas musicales para una posición de la progresión.

    Combina variantes de calidad, diatónicos del modo, dominantes secundarias
    probables, préstamos modales y re-analiza cada candidato con contexto prev/sig.
    """
    from music21 import pitch as m21p

    if not acordes or not (0 <= indice < len(acordes)):
        return []

    actual = acordes[indice]
    root = _chord_root_name(actual)
    if not root:
        return []

    candidatos: list[str] = []
    vistos: set[str] = set()

    def _add(sym: str) -> None:
        sym = sym.strip()
        if sym and sym != actual and sym not in vistos and describe_chord(sym):
            vistos.add(sym)
            candidatos.append(sym)

    for q in _SUGERENCIA_QUALITIES:
        _add(root + q)

    for grupo in (triadas_de(tonalidad, modo), cuatriadas_de(tonalidad, modo)):
        for t in grupo:
            _add(t["simbolo"])

    tonic_pc = int(m21p.Pitch(tonalidad).pitchClass)
    degree_map = _MODE_DEGREES.get(modo, _MODE_DEGREES["ionian"])

    for ivl in degree_map:
        if ivl == 0:
            continue
        target_pc = (tonic_pc + ivl) % 12
        dom_pc = (target_pc + 7) % 12
        dom_name = _m21_pitch_to_jazz(m21p.Pitch(dom_pc).name)
        _add(dom_name + "7")

    if modo == "ionian":
        for ivl in (5, 8, 10):
            pc = (tonic_pc + ivl) % 12
            name = _m21_pitch_to_jazz(m21p.Pitch(pc).name)
            _add(name)
            _add(name + "m")
            if ivl == 10:
                _add(name + "7")
        subv_pc = (tonic_pc + 7 + 6) % 12
        _add(_m21_pitch_to_jazz(m21p.Pitch(subv_pc).name) + "7")

    n = len(acordes)
    anterior = acordes[indice - 1] if indice > 0 else None
    siguiente = acordes[indice + 1] if indice < n - 1 else None

    resultados: list[dict[str, Any]] = []
    for sym in candidatos:
        a = analizar_en_tonalidad(
            tonalidad, sym, modo, anterior=anterior, siguiente=siguiente,
        )
        resultados.append({
            "simbolo":      sym,
            "grado":        a.get("grado"),
            "funcion":      a.get("funcion"),
            "tipo_funcion": a.get("tipo_funcion"),
            "diatonico":    a.get("diatonico", False),
        })

    def _rank(r: dict[str, Any]) -> tuple[int, str]:
        score = 0
        if _chord_root_name(r["simbolo"]) == root:
            score -= 25
        if r.get("diatonico"):
            score -= 20
        if r.get("funcion"):
            score -= 10
        tipo = r.get("tipo_funcion")
        if tipo in ("dominante_secundaria", "tritone_substitution", "backdoor_dominant"):
            score -= 5
        elif tipo == "prestamo_modal":
            score -= 2
        return (score, r["simbolo"])

    resultados.sort(key=_rank)
    variantes = [r for r in resultados if _chord_root_name(r["simbolo"]) == root]
    otros = [r for r in resultados if _chord_root_name(r["simbolo"]) != root]
    return (variantes + otros)[:max_sugerencias]


def _modal_hints(tonalidad: str, simbolo: str, cs: Any) -> list[dict[str, Any]]:
    """Devuelve posibles contextos modales para un acorde no diatónico."""
    from music21 import scale as m21s, key as m21k

    try:
        chord_pcs = frozenset(int(p.pitchClass) for p in cs.pitches)
    except Exception:
        return []

    hints: list[dict[str, Any]] = []

    parallel_modes = [
        ("Dorian",     m21s.DorianScale(tonalidad)),
        ("Phrygian",   m21s.PhrygianScale(tonalidad)),
        ("Lydian",     m21s.LydianScale(tonalidad)),
        ("Mixolydian", m21s.MixolydianScale(tonalidad)),
        ("Aeolian",    m21s.MinorScale(tonalidad)),
        ("Locrian",    m21s.LocrianScale(tonalidad)),
    ]
    for nombre, sc in parallel_modes:
        scale_pcs = frozenset(int(p.pitchClass) for p in sc.getPitches())
        if chord_pcs.issubset(scale_pcs):
            hints.append({"tipo": "modal", "modo": nombre})

    try:
        rel = m21k.Key(tonalidad, "major").getRelativeMinor().tonic.name.replace("-", "b")
        rel_pcs = frozenset(int(p.pitchClass) for p in m21s.MinorScale(rel).getPitches())
        if chord_pcs.issubset(rel_pcs):
            hints.append({"tipo": "relativo", "tonica": rel})
    except Exception:
        pass

    return hints


def describe_chord(symbol: str) -> dict[str, Any] | None:
    """Return a JSON-serializable description of a chord symbol.

    Combines :func:`jazz21.symbols.normalize_chord_symbol` with the music21
    figure used internally for harmony and export.

    Args:
        symbol: American or jazz chord token (e.g. ``"Cmaj7"``, ``"Aø7"``).

    Returns:
        Dict with keys ``input``, ``canonical``, ``music21_figure``,
        ``intervals``, ``pitches``, ``musicxml_kind``, ``quality``,
        ``chord_kind_m21``. ``None`` if *symbol* is empty or unrecognized.
    """
    raw = (symbol or "").strip()
    if not raw:
        return None
    norm = normalize_chord_symbol(raw)
    if norm is None:
        return None
    fig = american_chord_to_music21_figure(norm.get("canonical") or raw)
    return {
        "input": raw,
        "canonical": norm.get("canonical"),
        "music21_figure": fig,
        "intervals": norm.get("intervals") or [],
        "pitches": norm.get("pitches") or [],
        "musicxml_kind": norm.get("musicxml_kind"),
        "quality": norm.get("quality"),
        "chord_kind_m21": norm.get("chord_kind_m21"),
    }


def _chord_meta_for_guitar(symbol: str, desc: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    try:
        from music21 import harmony

        cs = harmony.ChordSymbol(desc["music21_figure"])
        r = cs.root()
        if r is None:
            return None, "No se pudo determinar la raíz del acorde."
        kind = str(desc.get("chord_kind_m21") or getattr(cs, "chordKind", "") or "")
        return {
            "kind": kind,
            "root_pc": int(r.pitchClass) % 12,
            "symbol": symbol.strip(),
            "sound_pcs": {int(p.pitchClass) for p in cs.pitches},
        }, None
    except Exception as e:
        return None, str(e)


def resolve_guitar_shapes(
    symbol: str,
    *,
    shape_cycle: int | None = None,
) -> dict[str, Any]:
    """Resolve CAGED guitar diagram(s) for a chord symbol.

    Args:
        symbol: Chord symbol to diagram.
        shape_cycle: If set, include ``selected`` for that CAGED placement index.

    Returns:
        On success: ``symbol``, ``canonical``, ``caged_quality``, ``options``
        (list of dicts with ``svg``, ``caged_shape``, ``shape_cycle``, …).
        On failure: ``{"options": [], "unavailable": True, "reason": str}``.
        When *shape_cycle* is given and options exist, also ``selected``.
    """
    desc = describe_chord(symbol)
    if desc is None:
        return {"options": [], "unavailable": True, "reason": "Símbolo no reconocido."}

    chord, err = _chord_meta_for_guitar(symbol, desc)
    if chord is None:
        return {"options": [], "unavailable": True, "reason": err or "Sin metadatos."}

    by_quality: dict[str, list[Any]] = defaultdict(list)
    for s in ShapesCatalog.default_caged().playable_shapes():
        by_quality[s.quality].append(s)

    probe, reason = resolve_one_chord(chord, by_quality, shape_cycle=0)
    if probe is None:
        return {"options": [], "unavailable": True, "reason": reason or "Sin forma CAGED."}

    n_opt = int(probe.get("caged_options") or 1)
    options: list[dict[str, Any]] = []
    for cyc in range(n_opt):
        g, err_c = resolve_one_chord(chord, by_quality, shape_cycle=cyc)
        if g is None:
            if cyc == 0:
                return {"options": [], "unavailable": True, "reason": err_c or reason}
            break
        options.append(
            {
                "shape_cycle": cyc,
                "caged_shape": g.get("caged_shape"),
                "svg": g.get("svg"),
                "matched": g.get("matched"),
                "transposed": g.get("transposed"),
                "diagram_frets": g.get("diagram_frets"),
                "diagram_base_fret": g.get("diagram_base_fret"),
                "needs_review": g.get("needs_review"),
                "review_reasons": g.get("review_reasons"),
            }
        )

    out: dict[str, Any] = {
        "symbol": symbol.strip(),
        "canonical": desc.get("canonical"),
        "caged_quality": probe.get("caged_quality"),
        "options": options,
    }
    if shape_cycle is not None and options:
        out["selected"] = options[int(shape_cycle) % len(options)]
    return out


def to_manifest(symbols: list[str]) -> list[dict[str, Any]]:
    """Build a manifest list for a set of chord symbols.

    Args:
        symbols: Chord tokens to describe.

    Returns:
        One dict per symbol with ``symbol`` and either:
        - ``chord`` (from :func:`describe_chord`) and ``guitar``
          (from :func:`resolve_guitar_shapes`), or
        - ``error``: ``"unrecognized"`` when the symbol cannot be parsed.
    """
    manifest: list[dict[str, Any]] = []
    for sym in symbols:
        entry: dict[str, Any] = {"symbol": sym.strip()}
        desc = describe_chord(sym)
        if desc is None:
            entry["error"] = "unrecognized"
            manifest.append(entry)
            continue
        entry["chord"] = desc
        entry["guitar"] = resolve_guitar_shapes(sym)
        manifest.append(entry)
    return manifest
