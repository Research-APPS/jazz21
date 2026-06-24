"""Structured chord descriptions for SEO, GEO, and downstream publishers."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from jazz21.guitar.resolve import _resolve_one_chord
from jazz21.guitar.shapes import ShapesCatalog
from jazz21.notation.compose_engine import american_chord_to_music21_figure
from jazz21.symbols import normalize_chord_symbol


def describe_chord(symbol: str) -> dict[str, Any] | None:
    """
    Return a JSON-serializable description of a chord symbol.

    Combines ``normalize_chord_symbol`` with the music21 figure used internally.
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
    """
    Resolve CAGED guitar diagram(s) for a chord symbol.

    Returns ``{options: [...], selected?: ...}`` or ``{unavailable: True, reason: ...}``.
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

    probe, reason = _resolve_one_chord(chord, by_quality, shape_cycle=0)
    if probe is None:
        return {"options": [], "unavailable": True, "reason": reason or "Sin forma CAGED."}

    n_opt = int(probe.get("caged_options") or 1)
    options: list[dict[str, Any]] = []
    for cyc in range(n_opt):
        g, err_c = _resolve_one_chord(chord, by_quality, shape_cycle=cyc)
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
    """Build a manifest list for a set of chord symbols (SEO / GEO bridge)."""
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
