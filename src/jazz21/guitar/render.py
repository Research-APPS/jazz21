"""Render de diagramas de acorde (fretsy si está instalado, SVG propio si no)."""

from __future__ import annotations

from typing import Any


def render_chord_shape_svg(
    *,
    name: str,
    shape_letter: str,
    frets: list[int],
    fingers: list[int],
    base_fret: int,
    barre: tuple[int, int, int] | None,
    show_finger_numbers: bool,
    show_degree_labels: bool = True,
    chord_figure: str | None = None,
) -> str:
    """Render an SVG chord diagram for six strings.

    Args:
        name: Chord label shown on the diagram.
        shape_letter: CAGED shape letter.
        frets: Six fret positions (low E → high E); ``-1`` = muted.
        fingers: Fingering indices per string.
        base_fret: Starting fret for the diagram window.
        barre: Optional ``(from_string, to_string, fret)`` barre.
        show_finger_numbers: Draw fingering digits on dots.
        show_degree_labels: Show interval degree labels (forces fallback SVG
            when fretsy is installed but neck position is non-open).
        chord_figure: Optional music21 figure for degree labels.

    Returns:
        SVG markup string.

    Raises:
        ValueError: If ``frets`` does not have exactly six elements.
    """
    if len(frets) != 6:
        raise ValueError("frets must have 6 elements")
    finger_src = list(fingers) if fingers else [0] * 6
    while len(finger_src) < 6:
        finger_src.append(0)
    use_fingers = finger_src[:6]
    b_f = int(base_fret) if base_fret else 1

    from jazz21.guitar.diagram import render_chord_svg_fallback

    def fallback() -> str:
        return render_chord_svg_fallback(
            name=name,
            frets=list(frets),
            fingers=use_fingers,
            barre=barre,
            base_fret=b_f,
            subtitle=f"Forma {shape_letter}",
            show_finger_numbers=show_finger_numbers,
            show_degree_labels=show_degree_labels,
            chord_figure=chord_figure,
        )

    # ``fretsy`` interpreta cada traste como fila dentro de una rejilla fija (~5 trastes).
    # Con ``base_fret > 1`` o trastes “absolutos” altos (>5), los círculos quedaban fuera
    # del viewBox (diagrama vacío). El fallback SVG propio sí hace rel = fr − base + 1.
    # Con grados armónicos en los puntos siempre usamos el SVG propio (fretsy no los pinta).
    max_pf = max((int(x) for x in frets if int(x) > 0), default=0)
    neck_outside_fretsy_grid = b_f > 1 or max_pf > 5 or show_degree_labels

    try:
        from fretsy import ChordDiagram, DiagramStyle, render_svg

        if neck_outside_fretsy_grid:
            return fallback()

        kw: dict[str, Any] = {
            "name": name,
            "frets": list(frets),
            "fingers": use_fingers,
            "base_fret": b_f,
            "label": f"Forma {shape_letter}",
        }
        if barre:
            kw["barre"] = barre

        style = DiagramStyle(
            chord_name_color="#1a5276",
            dot_color="#1a5276",
            open_dot_color="#1a5276",
            nut_color="#1a5276",
            barre_color="#1a5276",
            mute_color="#c0392b",
            label_color="#5a5a5a",
        )
        diagram = ChordDiagram(**kw)
        return render_svg(diagram, style=style)
    except ImportError:
        return fallback()


def render_chord_shape_model_svg(
    cs: Any,
    use_fingers: list[int],
    *,
    display_name: str | None = None,
    show_finger_numbers: bool,
) -> str:
    """Compatibilidad con instancia ``ChordShape``."""
    barre_t = None
    if cs.barre and isinstance(cs.barre, (list, tuple)) and len(cs.barre) == 3:
        barre_t = (int(cs.barre[0]), int(cs.barre[1]), int(cs.barre[2]))
    title = str(display_name).strip() if display_name else getattr(cs, "name", "?")
    figure = title if title and title != "?" else getattr(cs, "name", None)
    return render_chord_shape_svg(
        name=title if title else "?",
        shape_letter=cs.shape,
        frets=list(cs.frets),
        fingers=use_fingers,
        base_fret=cs.base_fret or 1,
        barre=barre_t,
        show_finger_numbers=show_finger_numbers,
        chord_figure=str(figure).strip() if figure else None,
    )
