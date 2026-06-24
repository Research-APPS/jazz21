"""
Diagramas de acorde para guitarra (SVG) sin dependencias externas.
Se usa si `fretsy` no está instalado en el entorno activo.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from jazz21.guitar.utils import compact_interval_label, compute_intervals_notes

# Colores alineados con ChordIA (style.css --color-tonic, --color-dominant)
_DOT = "#1a5276"
_GRID = "#333333"
_MUTE = "#c0392b"
_BG = "#ffffff"
_MUTED_TEXT = "#666666"
# Etiqueta de traste inicial (mucho contraste; evita perderse tras los dots)
_BASE_FRET_TEXT = "#0d3d5c"


def render_chord_svg_fallback(
    name: str,
    frets: list[int],
    fingers: list[int],
    barre: tuple[int, int, int] | None = None,
    base_fret: int = 1,
    subtitle: str | None = None,
    show_finger_numbers: bool = True,
    *,
    show_degree_labels: bool = True,
    chord_figure: str | None = None,
) -> str:
    """
    ``frets`` / ``fingers``: 6 elementos, cuerda Mi grave → Mi agudo.
    ``barre``: (traste, cuerda_inicio, cuerda_fin) con cuerdas 1-indexadas (1 = Mi grave).
    ``chord_figure``: símbolo para music21 si difiere del título ``name`` (p. ej. título bonito).
    """
    if len(frets) != 6:
        raise ValueError("frets must have 6 elements")
    fingers = list(fingers) if fingers else [0] * 6
    while len(fingers) < 6:
        fingers.append(0)

    figure = (chord_figure or name or "").strip()
    degree_labels: list[str] = []
    if show_degree_labels and figure:
        raw_iv, _ = compute_intervals_notes(figure, frets)
        degree_labels = [compact_interval_label(x) for x in raw_iv]

    w: float = 200
    # Banda inferior fija para «Forma X» sin cambiar la geometría del mástil entre acordes.
    h: float = 298
    pad_lr = 28
    # Misma anchura de rejilla que en 1.er traste: el número de traste base va solo en el margen izquierdo.
    pad_left = pad_lr
    title_y = 26
    y_nut = 72
    grid_h = 190
    num_frets = 5
    fret_h = grid_h / num_frets
    x0, x1 = pad_left, w - pad_lr
    string_gap = (x1 - x0) / 5.0

    def sx(i: int) -> float:
        return x0 + i * string_gap

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">',
        f'<rect x="0" y="0" width="{w}" height="{h}" fill="{_BG}"/>',
        f'<text x="{w / 2:.1f}" y="{title_y}" text-anchor="middle" '
        f'font-family="Georgia,serif" font-size="22" font-weight="600" fill="{_DOT}">'
        f"{escape(name)}</text>",
    ]
    # Cejilla: líneas de traste + silleta, luego cuerdas, luego barra (cejilla dedo)
    parts.append(
        f'<rect x="{x0 - 0.5:.1f}" y="{y_nut:.1f}" width="{x1 - x0 + 1:.1f}" height="5" fill="{_DOT}"/>'
    )
    for k in range(1, num_frets + 1):
        y = y_nut + k * fret_h
        parts.append(
            f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" '
            f'stroke="{_GRID}" stroke-width="1.1"/>'
        )

    for i in range(6):
        x = sx(i)
        parts.append(
            f'<line x1="{x:.1f}" y1="{y_nut:.1f}" x2="{x:.1f}" '
            f'y2="{y_nut + grid_h:.1f}" stroke="{_GRID}" stroke-width="1.4"/>'
        )

    barre_cy = None
    b_fret: int | None = None
    b_lo: int | None = None
    b_hi: int | None = None
    if barre and len(barre) == 3:
        b_fret, b_lo, b_hi = int(barre[0]), int(barre[1]), int(barre[2])
        rel_b = b_fret - base_fret + 1
        if 1 <= rel_b <= num_frets:
            barre_cy = y_nut + (rel_b - 0.5) * fret_h
            xi_lo = sx(b_lo - 1)
            xi_hi = sx(b_hi - 1)
            pad_b = 5.0
            parts.append(
                f'<rect x="{xi_lo - pad_b:.1f}" y="{barre_cy - 10:.1f}" '
                f'width="{xi_hi - xi_lo + 2 * pad_b:.1f}" height="20" rx="8" fill="{_DOT}"/>'
            )

    r_dot = min(string_gap, fret_h) * 0.34

    for i, fr in enumerate(frets):
        x = sx(i)
        if fr <= 0:
            continue
        rel = fr - base_fret + 1
        rel = max(1, min(num_frets, rel))
        cy = y_nut + (rel - 0.5) * fret_h
        covered = (
            b_fret is not None
            and b_lo is not None
            and b_hi is not None
            and b_lo <= i + 1 <= b_hi
            and fr == b_fret
        )
        if not covered:
            parts.append(f'<circle cx="{x:.1f}" cy="{cy:.1f}" r="{r_dot:.1f}" fill="{_DOT}"/>')
            deg = degree_labels[i] if i < len(degree_labels) else ""
            if show_degree_labels and deg:
                fs = 7.5 if len(deg) > 3 else (9.5 if len(deg) > 1 else 11)
                parts.append(
                    f'<text x="{x:.1f}" y="{cy + 4:.1f}" text-anchor="middle" '
                    f'font-family="Arial,sans-serif" font-size="{fs:.1f}" font-weight="700" '
                    f'fill="#ffffff">{escape(deg)}</text>'
                )
            else:
                fn = fingers[i] if show_finger_numbers else 0
                if fn > 0:
                    parts.append(
                        f'<text x="{x:.1f}" y="{cy + 4:.1f}" text-anchor="middle" '
                        f'font-family="Arial,sans-serif" font-size="11" font-weight="600" '
                        f'fill="#ffffff">{fn}</text>'
                    )

    if barre_cy is not None and b_lo is not None and b_hi is not None:
        if show_degree_labels and degree_labels and any(degree_labels):
            for idx in range(b_lo - 1, b_hi):
                dg = degree_labels[idx] if idx < len(degree_labels) else ""
                if not dg:
                    continue
                bx = sx(idx)
                fs = 7.5 if len(dg) > 3 else (9.5 if len(dg) > 1 else 11)
                parts.append(
                    f'<text x="{bx:.1f}" y="{barre_cy + 4:.1f}" text-anchor="middle" '
                    f'font-family="Arial,sans-serif" font-size="{fs:.1f}" font-weight="700" '
                    f'fill="#ffffff">{escape(dg)}</text>'
                )
        elif show_finger_numbers:
            fn_barre = fingers[b_lo - 1]
            if fn_barre > 0:
                bx = (sx(b_hi - 1) + sx(b_lo - 1)) / 2
                parts.append(
                    f'<text x="{bx:.1f}" y="{barre_cy + 4:.1f}" text-anchor="middle" '
                    f'font-family="Arial,sans-serif" font-size="11" font-weight="600" '
                    f'fill="#ffffff">{fn_barre}</text>'
                )

    for i, fr in enumerate(frets):
        x = sx(i)
        if fr < 0:
            parts.append(
                f'<text x="{x:.1f}" y="{y_nut - 8:.1f}" text-anchor="middle" '
                f'font-family="Arial,sans-serif" font-size="12" font-weight="700" '
                f'fill="{_MUTE}">✕</text>'
            )
        elif fr == 0:
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y_nut - 12:.1f}" r="6" fill="none" '
                f'stroke="{_DOT}" stroke-width="2"/>'
            )
            dg0 = degree_labels[i] if i < len(degree_labels) else ""
            if show_degree_labels and dg0:
                parts.append(
                    f'<text x="{x:.1f}" y="{y_nut - 22:.1f}" text-anchor="middle" '
                    f'font-family="Arial,sans-serif" font-size="9.5" font-weight="700" '
                    f'fill="{_DOT}">{escape(dg0)}</text>'
                )

    if base_fret > 1:
        fy = y_nut + fret_h * 0.55
        fret_lbl = str(int(base_fret))
        label_x = pad_lr / 2
        fs = 10.5 if len(fret_lbl) >= 2 else 12.0
        parts.append(
            f'<text x="{label_x:.1f}" y="{fy + 4.5:.1f}" text-anchor="middle" '
            f'font-family="Arial,sans-serif" font-size="{fs:.1f}" font-weight="700" '
            f'fill="{_BASE_FRET_TEXT}">{fret_lbl}</text>'
        )

    if subtitle:
        sub_y_bottom = h - 9.0
        parts.append(
            f'<text x="{w / 2:.1f}" y="{sub_y_bottom:.1f}" text-anchor="middle" '
            f'font-family="Arial,sans-serif" font-size="11" fill="{_MUTED_TEXT}">'
            f"{escape(subtitle)}</text>"
        )

    parts.append("</svg>")
    return "\n".join(parts)
