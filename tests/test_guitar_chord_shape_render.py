"""Tests de render SVG de diagramas."""

from types import SimpleNamespace

import pytest

from jazz21.guitar.render import render_chord_shape_svg


def test_render_chord_shape_svg_returns_svg_string():
    svg = render_chord_shape_svg(
        name="C",
        shape_letter="C",
        frets=[-1, 3, 2, 0, 1, 0],
        fingers=[0, 3, 2, 0, 1, 0],
        base_fret=1,
        barre=None,
        show_finger_numbers=True,
    )
    assert isinstance(svg, str)
    assert "<svg" in svg.lower()


def test_render_chord_shape_svg_with_barre():
    svg = render_chord_shape_svg(
        name="F",
        shape_letter="E",
        frets=[1, 3, 3, 2, 1, 1],
        fingers=[0, 0, 0, 0, 0, 0],
        base_fret=1,
        barre=(1, 1, 6),
        show_finger_numbers=False,
    )
    assert "<svg" in svg.lower()


def test_render_chord_shape_svg_wrong_fret_count():
    with pytest.raises(ValueError, match="6"):
        render_chord_shape_svg(
            name="X",
            shape_letter="X",
            frets=[0, 0, 0],
            fingers=[0, 0, 0],
            base_fret=1,
            barre=None,
            show_finger_numbers=False,
        )


def test_render_chord_shape_svg_shows_dots_low_neck():
    svg = render_chord_shape_svg(
        name="C",
        shape_letter="C",
        frets=[-1, 3, 2, 0, 1, 0],
        fingers=[0, 3, 2, 0, 1, 0],
        base_fret=1,
        barre=None,
        show_finger_numbers=True,
    )
    assert "<circle" in svg.lower()
    # Grados armónicos compactos respecto a la raíz (no cifras de dedos al priorizar grados)
    assert ">3</text>" in svg or ">5</text>" in svg
    assert "maj7" not in svg.lower()  # Do mayor no lleva 7ª mayor en esta forma


def test_render_chord_shape_svg_high_neck_uses_fallback_with_dots():
    """Con ``base_fret`` > 1 se usa SVG propio (trastes relativos correctos); evita rejilla vacía en fretsy."""
    svg = render_chord_shape_svg(
        name="Ebmaj7/G",
        shape_letter="E",
        frets=[11, 13, 12, 12, 11, 11],
        fingers=[0, 0, 0, 0, 0, 0],
        base_fret=11,
        barre=None,
        show_finger_numbers=False,
    )
    assert "<circle" in svg.lower()


def test_subtitle_under_fretboard_not_above_open_strings():
    """«Forma …» va al pie del SVG; el mástil no cambia de altura entre acordes."""
    from jazz21.guitar.diagram import render_chord_svg_fallback

    svg = render_chord_svg_fallback(
        name="G9",
        frets=[3, 2, 0, 0, 0, 1],
        fingers=[0, 0, 0, 0, 0, 0],
        base_fret=1,
        subtitle="Forma G",
        show_finger_numbers=False,
        show_degree_labels=True,
    )
    assert 'height="298"' in svg
    assert "Forma G" in svg


def test_high_base_fret_same_grid_width_as_open_position():
    """El número de traste base ya no desplaza la rejilla; solo aparece en el margen."""
    from jazz21.guitar.diagram import render_chord_svg_fallback

    low = render_chord_svg_fallback(
        "C",
        [-1, 3, 2, 0, 1, 0],
        [0] * 6,
        base_fret=1,
        subtitle=None,
    )
    high = render_chord_svg_fallback(
        "G9",
        [10, 10, 9, 9, 10, 10],
        [0] * 6,
        base_fret=7,
        subtitle=None,
    )
    # Primera cuerda: línea vertical en x0 = pad_left = 28
    assert 'x1="28.0"' in low
    assert 'x1="28.0"' in high
    assert ">7</text>" in high


@pytest.mark.parametrize("display,want_title", [(None, "Gmaj"), ("Eb9", "Eb9")])
def test_render_chord_shape_model_svg_display_name(monkeypatch, display, want_title):
    from jazz21.guitar import render as gcr

    seen = {}

    def fake_render(**kwargs):
        seen["name"] = kwargs.get("name")
        return "<svg>x</svg>"

    monkeypatch.setattr(gcr, "render_chord_shape_svg", fake_render)
    ns = SimpleNamespace(
        name="Gmaj",
        shape="G",
        frets=[0, 0, 0, 0, 0, 3],
        fingers=[0] * 6,
        barre=None,
        base_fret=3,
    )
    out = gcr.render_chord_shape_model_svg(
        ns,
        [0] * 6,
        display_name=display,
        show_finger_numbers=False,
    )
    assert seen.get("name") == want_title
    assert "svg" in out.lower()
