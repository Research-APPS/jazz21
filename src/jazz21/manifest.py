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
    11: ("VII",  "Dominante"),
}

# Semitones from tonic → (roman numeral, harmonic function) for natural minor (Aeolian).
# bVII actúa como Dominante modal en jazz menor (sustituye al V natural sin sensible).
_AEOLIAN_DEGREES: dict[int, tuple[str, str]] = {
    0:  ("I",    "Tónica"),
    2:  ("II",   "Subdominante"),
    3:  ("bIII", "Tónica"),
    5:  ("IV",   "Subdominante"),
    7:  ("V",    "Tónica"),
    8:  ("bVI",  "Subdominante"),
    10: ("bVII", "Dominante"),
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


def _secondary_dominant(
    root_pc: int,
    chord_pcs: frozenset[int],
    tonic_pc: int,
    degree_map: dict[int, str],
) -> dict[str, Any] | None:
    """Detecta si un acorde no diatónico actúa como dominante secundaria.

    Condición: el acorde tiene tercera mayor (intervalo 4 st sobre la raíz)
    y el acorde que resuelve (quinta justa abajo) es un grado diatónico.

    Returns:
        Dict con ``label`` (e.g. ``"V/VI"``) y ``detalle``, o None.
    """
    maj3_pc = (root_pc + 4) % 12
    if maj3_pc not in chord_pcs:
        return None                          # sin tercera mayor → no es dominante

    target_pc       = (root_pc + 5) % 12    # resolución: quinta abajo
    target_interval = (target_pc - tonic_pc) % 12

    if target_interval not in degree_map:
        return None                          # el objetivo no es un grado diatónico

    target_degree = degree_map[target_interval]
    return {
        "label":   f"V/{target_degree}",
        "detalle": f"Dominante secundaria → {target_degree}",
    }


def analizar_en_tonalidad(tonalidad: str, simbolo: str, modo: str = "ionian") -> dict[str, Any]:
    """Analiza un acorde dentro de una tonalidad y modo.

    Usa comparación de pitch-class de la raíz (enfoque CHORDIA): G7, G9, G13
    son todos V en C mayor. Soporta los 7 modos: ionian, dorian, phrygian,
    lydian, mixolydian, aeolian, locrian.

    Para modos distintos de ionian, se devuelve el grado romano (bIII, #IV…)
    sin etiqueta de función T/SD/D.

    Args:
        tonalidad: Tónica (e.g. ``"C"``, ``"Bb"``).
        simbolo:   Símbolo de acorde (e.g. ``"G13"``, ``"Gb9"``).
        modo:      Modo de la escala (por defecto ``"ionian"``).

    Returns:
        Dict con ``simbolo``, ``notas``, ``intervalos``.
        Si diatónico: ``diatonico=True``, ``grado``, ``funcion`` (None si no ionian).
        Si no diatónico: ``diatonico=False``, ``hints``.
    """
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
                "diatonico":  True,
                "grado":      grado,
                "funcion":    funcion,
                "confianza":  "alta",
                "notas_fuera": [],
                "hints":      [],
            })
        else:
            # no diatónico: buscar dominante secundaria o función desconocida
            sec = _secondary_dominant(root_pc, chord_pcs, tonic_pc, degree_map)
            hints = _modal_hints(tonalidad, simbolo, cs)
            entry.update({
                "diatonico":       False,
                "grado":           None,
                "funcion":         sec["label"] if sec else None,
                "confianza":       "media" if sec else None,
                "funcion_detalle": sec["detalle"] if sec else None,
                "hints":           hints,
                "notas_fuera":     notas_fuera,
            })
    except Exception as exc:
        entry.update({"diatonico": False, "grado": None, "funcion": None,
                      "confianza": None, "hints": [], "error": str(exc)})

    return entry


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
