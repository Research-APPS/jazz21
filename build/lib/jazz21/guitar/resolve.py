"""Resuelve un diagrama CAGED (ChordShape + transposición) por metadato de acorde del compose."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from jazz21.guitar.render import (
    render_chord_shape_model_svg,
    render_chord_shape_svg,
)

_SHAPE_RANK = {"E": 0, "A": 1, "G": 2, "D": 3, "C": 4}


def _shape_rank(shape: str) -> int:
    return _SHAPE_RANK.get(shape, 99)


def music21_kind_to_quality(kind: str) -> str | None:
    k = (kind or "").replace("_", "-").lower().strip()
    if not k:
        return None
    if "half-diminished" in k:
        return None
    if "diminished-seventh" in k or (
        "diminished" in k and "seventh" in k and "half" not in k
    ):
        return "dim"
    if k == "diminished" or (k.endswith("diminished") and "seventh" not in k):
        return "dim"
    if "augmented" in k:
        return "aug"
    if "major-seventh" in k:
        return "maj7"
    if "minor-ninth" in k:
        # Biblia CAGED sin plantilla m9: mostramos la forma menor con 7 (base armónica similar).
        return "min7"
    if "major-ninth" in k:
        return "maj7"
    if "minor-seventh" in k:
        return "min7"
    if "dominant" in k:
        return "dom7"
    if k == "minor":
        return "minor"
    if k == "major":
        return "major"
    if "seventh" in k and "major" not in k and "minor" not in k:
        return "dom7"
    return None


def music21_kind_to_caged_approx(kind: str) -> tuple[str | None, str]:
    """Aproximación cuando no hay plantilla exacta (6, sus, ø…)."""
    k = (kind or "").replace("_", "-").lower().strip()
    if not k:
        return None, ""
    if "major-sixth" in k:
        return "major", "6ª mayor → triada mayor CAGED (sin la 6ª en el diagrama)."
    if "minor-sixth" in k:
        return "minor", "6ª menor → triada menor CAGED (sin la 6ª en el diagrama)."
    if "suspended-fourth" in k:
        if "seventh" in k or "dominant" in k:
            return "dom7", "sus7 → séptima dominante CAGED aproximada."
        return "major", "sus → triada mayor CAGED aproximada."
    if "half-diminished" in k:
        return "dim", "ø7 → disminuido CAGED aproximado."
    return None, ""


def infer_caged_quality_from_pcs(root_pc: int, pcs: set[int] | list[int]) -> tuple[str | None, str]:
    """
    Infiere calidad CAGED desde clases de altura sonoras (mástil / teclado).
    Ignora extensiones (6, 9, 11…) y se queda con triada o séptima básica.
    """
    if not pcs:
        return None, ""
    try:
        root = int(root_pc) % 12
    except (TypeError, ValueError):
        return None, ""
    rel = {(int(p) - root) % 12 for p in pcs}

    has_m3 = 3 in rel
    has_M3 = 4 in rel
    has_d5 = 6 in rel
    has_m7 = 10 in rel
    has_M7 = 11 in rel

    if has_m3 and has_d5 and has_m7:
        return "dim", ""
    if has_M3 and 8 in rel:
        return "aug", ""
    if has_m3 and has_m7 and not has_M3:
        return "min7", ""
    if has_M3 and has_M7 and not has_m3:
        return "maj7", ""
    if has_M3 and has_m7 and not has_m3:
        return "dom7", ""
    if has_m3 and not has_M3:
        return "minor", ""
    if has_M3 and not has_m3:
        return "major", ""
    if 5 in rel and 7 in rel and not has_m3 and not has_M3:
        return "major", "sus (4ª+5ª) → mayor aproximado desde notas."
    return None, "sin 3ª clara en las notas sonoras"


def resolve_caged_quality(
    *,
    kind: str,
    root_pc: int,
    sound_pcs: set[int] | list[int] | None = None,
) -> dict[str, Any]:
    """
    Elige calidad CAGED: notas sonoras si son concluyentes; si no, cifrado MusicXML.
    """
    from_notes, notes_note = infer_caged_quality_from_pcs(root_pc, sound_pcs or [])
    from_kind = music21_kind_to_quality(kind)
    from_approx, approx_hint = music21_kind_to_caged_approx(kind)

    k = (kind or "").replace("_", "-").lower()
    kind_implies_seventh = any(
        tok in k for tok in ("seventh", "dominant", "ninth", "eleventh", "thirteenth")
    )

    quality: str | None = None
    source = ""
    hint = ""

    if from_notes and from_kind and from_notes != from_kind:
        # Voicing incompleto (triada en partitura, cifrado con 7ª)
        if kind_implies_seventh and from_notes in ("major", "minor"):
            quality = from_kind
            source = "kind"
            hint = (
                f"Voicing parcial en partitura (sin 7ª audible); "
                f"se usa calidad del cifrado ({from_kind})."
            )
        # Tensiones / #11 / tritonos: priorizar cifrado si no es ø explícito
        elif from_notes == "dim" and from_kind in ("min7", "maj7", "dom7", "minor", "major"):
            if "half-diminished" not in k:
                quality = from_kind
                source = "kind"
                hint = (
                    f"Notas con tritono/extensión; cifrado ({from_kind}) "
                    f"prevalece sobre «{from_notes}» inferido."
                )
            else:
                quality = from_notes
                source = "notes"
                hint = notes_note
        else:
            quality = from_notes
            source = "notes"
            hint = (
                f"Cifrado ({kind or '?'}) → {from_kind or from_approx or '?'}; "
                f"teclado/partitura → {from_notes}."
            )
    elif from_notes:
        quality = from_notes
        source = "notes"
        if from_kind and from_kind == from_notes:
            hint = notes_note
        elif from_kind and from_kind != from_notes:
            hint = (
                f"Cifrado ({kind or '?'}) → {from_kind}; "
                f"teclado/partitura → {from_notes}."
            )
        elif from_approx and from_approx != from_notes:
            hint = (
                f"Cifrado ({kind or '?'}) ~{from_approx}; "
                f"teclado/partitura → {from_notes}."
            )
        elif from_approx:
            hint = approx_hint or notes_note
        else:
            hint = notes_note
    elif from_kind:
        quality = from_kind
        source = "kind"
    elif from_approx:
        quality = from_approx
        source = "approx"
        hint = approx_hint

    return {
        "quality": quality,
        "source": source,
        "hint": hint,
        "from_kind": from_kind,
        "from_notes": from_notes,
        "from_approx": from_approx,
    }


def _shortest_pc_delta(target_pc: int, source_pc: int) -> int:
    d = (target_pc - source_pc) % 12
    if d > 6:
        d -= 12
    return d


def _pitch_class_from_m21_root(r: Any) -> int | None:
    if r is None:
        return None
    if hasattr(r, "pitchClass"):
        try:
            return int(r.pitchClass)
        except (TypeError, ValueError):
            return None
    p = getattr(r, "pitch", None)
    if p is not None and hasattr(p, "pitchClass"):
        try:
            return int(p.pitchClass)
        except (TypeError, ValueError):
            return None
    return None


def _root_pc_from_chordshape_name(name: str) -> int | None:
    if not name or not str(name).strip():
        return None
    s = str(name).strip()
    try:
        from music21 import harmony

        cs = harmony.ChordSymbol(s)
        return _pitch_class_from_m21_root(cs.root())
    except Exception:
        try:
            from music21 import harmony

            from jazz21.notation.compose_engine import american_chord_to_music21_figure

            fig = american_chord_to_music21_figure(s)
            cs = harmony.ChordSymbol(fig)
            return _pitch_class_from_m21_root(cs.root())
        except Exception:
            return None


def _transpose_frets_barre_base(
    tmpl_frets: list[int],
    tmpl_barre: tuple[int, int, int] | None,
    delta: int,
) -> tuple[list[int], tuple[int, int, int] | None, int] | None:
    """
    Trasponer un patrón de trastes (cuerdas standard) por ``delta`` semitonos.

    Cuando alguna cuerda al aire (0) tras ``+ delta`` daría traste negativo,
    sumamos la misma octava (+12k) en **todas** las cuerdas pulsadas/nota al aire
    (exc. mudas): así se mantiene el armónico antes imposible bajo cejilla.
    """
    if len(tmpl_frets) != 6:
        return None
    abs_new: list[int] = []
    for fr in tmpl_frets:
        fr = int(fr)
        if fr < 0:
            abs_new.append(-1)
            continue
        abs_new.append(fr + delta)

    # Notas realmente tocadas (no mudas -1). Incluye trastes negativos antes del reajuste de octava.
    voiced = [abs_new[i] for i in range(6) if tmpl_frets[i] >= 0]
    if not voiced:
        return None
    mn = min(voiced)
    add = ((-mn + 11) // 12) * 12 if mn < 0 else 0
    if add:
        for i in range(6):
            if tmpl_frets[i] >= 0:
                abs_new[i] += add

    barre_out: tuple[int, int, int] | None = None
    if tmpl_barre and len(tmpl_barre) == 3:
        bf = int(tmpl_barre[0]) + delta + add
        lo, hi = int(tmpl_barre[1]), int(tmpl_barre[2])
        while bf < 0:
            bf += 12
        while bf > 24:
            bf -= 12
            if bf < 0:
                return None
        barre_out = (bf, lo, hi)

    while True:
        played = [f for f in abs_new if f >= 0]
        if not played:
            return None
        if max(played) <= 24:
            break
        fretted = [f for f in abs_new if f > 0]
        if not fretted or min(fretted) < 12:
            return None
        for i in range(6):
            if abs_new[i] > 0:
                abs_new[i] -= 12
        if barre_out is not None:
            bb, blo, bhi = barre_out
            if bb < 12:
                return None
            barre_out = (bb - 12, blo, bhi)

    if barre_out is not None:
        bb = barre_out[0]
        if bb < 0 or bb > 24:
            return None

    positives = [f for f in abs_new if f > 0]
    if not positives:
        return None
    lo_p = min(positives)
    hi_p = max(positives)
    if hi_p - lo_p <= 4:
        base_out = lo_p
    else:
        base_out = max(1, hi_p - 4)
    return abs_new, barre_out, base_out


# Tokens en símbolo que suelen llevar tensión/modificación más allá de triada o 7 básicas CAGED.
_EXT_SUBSTRINGS = (
    "b13",
    "#13",
    "13(",  # alterations in parens often list extensions
    "majsus",
    "maj13",
    "maj11",
    "maj9",
    "^13",
    "^9",
    "m13",
    "m11",
    "m69",
    "69",
    "add",
    "(9",
    "(11",
    "(13",
    "(#11",
    "(b9",
    "(#9",
    "sus2",
    "sus4",
    "omit",
)


def diagram_review_reasons(*, symbol_display: str, kind_raw: str) -> list[str]:
    """
    Avisos de revisión: el usuario sigue teniendo SVG, pero la forma CAGED puja a una aproximación.
    Mensajes cortos para la UI y lista en perfil.
    """
    out: list[str] = []
    seen: set[str] = set()

    def add(msg: str) -> None:
        if msg not in seen:
            seen.add(msg)
            out.append(msg)

    s = (symbol_display or "").strip()
    kind = (kind_raw or "").replace("_", "-").lower()

    if "/" in s:
        add(
            "Acorde slash (bajo en el símbolo): la forma dibujada puede no remarcar el bajo inversional "
            "en la digitación estándar CAGED."
        )

    lc = "".join((symbol_display or "").strip().split()).lower()

    # Heurística simbólica: extensiones o alteraciones frecuentes
    if any(tok in lc for tok in _EXT_SUBSTRINGS):
        add(
            "El símbolo sugiere extensiones o modificaciones más allá del «esqueleto» CAGED (triada "
            "o séptima básico). El dibujo muestra una plantilla cercana; conviene comprobar notas "
            "y tensiones sobre la propia obra."
        )
    else:
        for m in ("#11", "b11", "#9", "b9", "alt"):
            if m in lc:
                add(
                    "Incluye tensión indicada (#9, #11… o alt). Solo se muestra forma base disponible "
                    "en biblioteca — revisión recomendada."
                )
                break

    kind_has_extension_class = (
        "ninth" in kind or "eleventh" in kind or "thirteenth" in kind or "altered" in kind
    )
    if kind_has_extension_class:
        add(
            "El clasificador interno (tipo de acorde amplio tipo 9.ª, 13.ª, alt…) aquí se aproxima a "
            "la plantilla CAGED más cercana sin modelar todas las tensiones nominalmente correctas "
            "(comprueba funcionamiento tonal en contexto)."
        )

    return out


def _ordered_caged_candidates(candidates: list[Any], *, root_pc_i: int) -> list[Any]:
    """Orden estable: coincide raíz figurada primero (p. ej. Dm7 en traste); luego E→A→G→D→C."""
    return sorted(
        candidates,
        key=lambda cs: (
            0
            if (_rpc := _root_pc_from_chordshape_name(cs.name)) is not None
            and int(_rpc) == int(root_pc_i)
            else 1,
            _shape_rank(cs.shape),
            int(getattr(cs, "orden", 0) or 0),
        ),
    )


def _resolve_one_chord(
    chord: dict[str, Any],
    by_quality: dict[str, list[Any]],
    *,
    shape_cycle: int = 0,
) -> tuple[dict[str, Any] | None, str | None]:
    kind_raw = chord.get("kind") or ""
    root_pc = chord.get("root_pc")
    try:
        root_pc_i = int(root_pc) % 12
    except (TypeError, ValueError):
        return None, "Sin clase de altura de raíz (root_pc) para trasponer el diagrama."

    resolved = resolve_caged_quality(
        kind=kind_raw,
        root_pc=root_pc_i,
        sound_pcs=chord.get("sound_pcs"),
    )
    quality = resolved.get("quality")
    if not quality:
        k = str(kind_raw).strip() or "(vacío)"
        return None, (
            f"Calidad no mapeada a CAGED (music21 kind «{k}»). "
            "Soportado aprox.: mayor, menor, 7, maj7, m7, dim, aug."
        )

    candidates = by_quality.get(quality) or []
    if not candidates:
        return None, f"No hay formas ChordShape CAGED para calidad «{quality}»."

    cand_sorted = _ordered_caged_candidates(candidates, root_pc_i=root_pc_i)
    n_templates = len(cand_sorted)
    try:
        sc = int(shape_cycle)
    except (TypeError, ValueError):
        sc = 0
    cyc_mod = sc % n_templates if n_templates else 0

    tmpl = cand_sorted[cyc_mod]
    symbol_display = (chord.get("symbol") or "?").strip()

    trpc_match = _root_pc_from_chordshape_name(tmpl.name)
    if trpc_match is not None and trpc_match == root_pc_i:
        fingers = (
            tmpl.fingers
            if isinstance(tmpl.fingers, list) and len(tmpl.fingers) == 6
            else [0, 0, 0, 0, 0, 0]
        )
        try:
            svg = render_chord_shape_model_svg(
                tmpl,
                fingers,
                display_name=symbol_display or None,
                show_finger_numbers=True,
            )
        except Exception:
            return None, (
                f"Fallo al generar SVG (forma {tmpl.shape} · «{tmpl.name}»)."
            )
        rr = diagram_review_reasons(symbol_display=symbol_display, kind_raw=kind_raw)
        if resolved.get("hint"):
            rr = list(rr) + [resolved["hint"]]
        if resolved.get("source") in ("approx", "notes"):
            rr = list(rr) + [
                f"Plantilla CAGED vía {'notas sonoras' if resolved['source'] == 'notes' else 'aproximación'} "
                f"(«{quality}»)."
            ]
        frets_diagram = [int(x) for x in list(tmpl.frets)]
        return {
            "svg": svg,
            "shape": tmpl.shape,
            "caged_shape": tmpl.shape,
            "matched": True,
            "transposed": False,
            "caged_cycle": int(cyc_mod),
            "caged_options": n_templates,
            "needs_review": bool(rr),
            "review_reasons": rr,
            "diagram_frets": frets_diagram,
            "diagram_base_fret": int(getattr(tmpl, "base_fret", None) or 1),
            "quality_source": resolved.get("source") or "",
            "quality_hint": resolved.get("hint") or "",
            "caged_quality": quality,
        }, None

    trpc_t = _root_pc_from_chordshape_name(tmpl.name)
    if trpc_t is None:
        return None, (
            f"No se pudo leer la raíz de plantilla «{tmpl.name}» (forma {tmpl.shape}) para trasponer."
        )
    delta = _shortest_pc_delta(root_pc_i, trpc_t)
    tmpl_frets = [int(x) for x in list(tmpl.frets)]
    barre_t = None
    if tmpl.barre and isinstance(tmpl.barre, (list, tuple)) and len(tmpl.barre) == 3:
        barre_t = (int(tmpl.barre[0]), int(tmpl.barre[1]), int(tmpl.barre[2]))
    transposed_shape = _transpose_frets_barre_base(tmpl_frets, barre_t, delta)
    if transposed_shape is None:
        return None, (
            f"Trasposición desde forma {tmpl.shape} imposible (trastes fuera de rango o sin pulsaciones)."
        )
    abs_new, barre_out, base_out = transposed_shape
    try:
        svg = render_chord_shape_svg(
            name=symbol_display,
            shape_letter=tmpl.shape,
            frets=abs_new,
            fingers=[0, 0, 0, 0, 0, 0],
            base_fret=base_out,
            barre=barre_out,
            show_finger_numbers=False,
        )
    except Exception:
        return None, f"Fallo al generar SVG tras trasponer desde forma {tmpl.shape}."
    rr = diagram_review_reasons(symbol_display=symbol_display, kind_raw=kind_raw)
    if resolved.get("hint"):
        rr = list(rr) + [resolved["hint"]]
    if resolved.get("source") in ("approx", "notes"):
        rr = list(rr) + [
            f"Plantilla CAGED vía {'notas sonoras' if resolved['source'] == 'notes' else 'aproximación'} "
            f"(«{quality}»)."
        ]
    return {
        "svg": svg,
        "shape": tmpl.shape,
        "caged_shape": tmpl.shape,
        "matched": False,
        "transposed": True,
        "caged_cycle": int(cyc_mod),
        "caged_options": n_templates,
        "needs_review": bool(rr),
        "review_reasons": rr,
        "diagram_frets": [int(x) for x in abs_new],
        "diagram_base_fret": int(base_out),
        "quality_source": resolved.get("source") or "",
        "quality_hint": resolved.get("hint") or "",
        "caged_quality": quality,
    }, None


def attach_guitar_shapes_to_chords(
    chords: list[dict[str, Any]] | None,
    *,
    shape_cycle_by_flat: dict[int, int] | None = None,
    shapes: list[Any] | None = None,
) -> None:
    """Añade la clave ``guitar`` a cada elemento de ``chords`` (mutación in-place)."""
    if not chords:
        return
    from jazz21.guitar.shapes import ShapesCatalog

    if shapes is None:
        shapes = ShapesCatalog.default_caged().playable_shapes()
    by_quality: dict[str, list[Any]] = defaultdict(list)
    for cs in shapes:
        if getattr(cs, "playable", True) and getattr(cs, "system", "caged") == "caged":
            by_quality[cs.quality].append(cs)

    cmap = dict(shape_cycle_by_flat) if shape_cycle_by_flat else {}

    for c in chords:
        c.pop("guitar", None)
        fi = c.get("flat_index")
        cycle_for = cmap.get(int(fi)) if isinstance(fi, int) else None
        cyc_arg = cycle_for if cycle_for is not None else 0
        try:
            cyc_arg = int(cyc_arg)
        except (TypeError, ValueError):
            cyc_arg = 0
        g, reason = _resolve_one_chord(c, by_quality, shape_cycle=cyc_arg)
        if g is not None:
            c["guitar"] = g
        else:
            c["guitar"] = {
                "unavailable": True,
                "reason": reason or "Motivo no detallado.",
            }
