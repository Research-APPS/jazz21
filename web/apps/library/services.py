"""Normalización del payload del widget → campos de Progression."""

from __future__ import annotations

from typing import Any

import jazz21


def build_progression_payload(source: dict[str, Any]) -> dict[str, Any]:
    """Deriva chords/analysis/ontology desde el payload del widget.

    ``source`` se guarda aparte en ``source_json`` sin modificar.
    """
    prog = source.get("current_progression") or source.get("progression") or {}
    tonalidad = source.get("key") or prog.get("tonalidad") or "C"
    modo = source.get("mode") or prog.get("modo") or "ionian"
    nombre = source.get("title") or prog.get("nombre") or "Sin título"

    symbols = _extract_symbols(source, prog)
    ui = jazz21.progresion_para_ui(tonalidad, symbols, modo, nombre)

    chords_out = []
    analysis_out = []
    for sym, chord in zip(symbols, ui["acordes"]):
        chords_out.append(sym)
        analysis_out.append({
            "simbolo": sym,
            "grado": chord.get("grado"),
            "funcion": chord.get("funcion"),
            "tipo_funcion": chord.get("tipo_funcion"),
            "diatonico": chord.get("diatonico", False),
            "confianza": chord.get("confianza"),
            "hints": chord.get("hints") or [],
            "notas": chord.get("notas") or [],
        })

    ontology = {
        "jazz21_version": jazz21.__version__,
        "analysis_engine": "manifest.py",
        "saved_from": source.get("saved_from", "widget"),
        "progression_meta": {
            "nombre": nombre,
            "nivel": prog.get("nivel"),
            "patron": ui.get("patron") or prog.get("patron"),
            "tonalidad": tonalidad,
            "modo": modo,
        },
        "chords": analysis_out,
        "relations": [],
        "internal_labels": [],
    }

    widget_state = source.get("widget_state") or {
        "selected_key": tonalidad,
        "selected_mode": modo,
        "current_progression": prog,
        "selected_chord_index": source.get("selected_chord_index"),
        "filters": source.get("filters") or {},
        "ui_state": source.get("ui_state") or {},
    }

    return {
        "title": nombre,
        "key": tonalidad,
        "mode": modo,
        "chords_json": chords_out,
        "analysis_json": analysis_out,
        "ontology_json": ontology,
        "widget_state_json": widget_state,
    }


def _extract_symbols(source: dict[str, Any], prog: dict[str, Any]) -> list[str]:
    if source.get("chords"):
        return [c if isinstance(c, str) else c.get("simbolo", "") for c in source["chords"]]
    acordes = prog.get("acordes") or []
    return [a.get("simbolo", a) if isinstance(a, dict) else str(a) for a in acordes]
