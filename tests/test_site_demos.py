"""Execute Python snippets embedded in site/ HTML demos (biblioteca web)."""

from __future__ import annotations

import html
import io
import json
import re
from contextlib import redirect_stdout
from pathlib import Path

import pytest

SITE_ROOT = Path(__file__).resolve().parents[1] / "site"
_DEMO_RE = re.compile(
    r'<textarea class="pg-editor">(.*?)</textarea>',
    re.DOTALL,
)


def _site_demo_paths() -> list[Path]:
    skip = {"index.html", "spike.html", "venv.html"}
    paths = []
    for p in sorted(SITE_ROOT.rglob("*.html")):
        if p.name in skip:
            continue
        text = p.read_text(encoding="utf-8")
        if _DEMO_RE.search(text):
            paths.append(p)
    return paths


def _extract_code(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = _DEMO_RE.search(text)
    assert m is not None, path
    return html.unescape(m.group(1).strip())


def _run_demo(code: str) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(code, {"__name__": "__main__"}, {})  # noqa: S102
    return buf.getvalue()


@pytest.fixture(params=_site_demo_paths(), ids=lambda p: str(p.relative_to(SITE_ROOT)))
def site_demo(request: pytest.FixtureRequest) -> tuple[Path, str]:
    path: Path = request.param
    return path, _extract_code(path)


def test_site_demo_executes_without_error(site_demo: tuple[Path, str]) -> None:
    path, code = site_demo
    out = _run_demo(code)
    assert out.strip(), f"{path}: expected non-empty stdout"


def test_importar_demo_output() -> None:
    out = _run_demo(_extract_code(SITE_ROOT / "python" / "importar.html"))
    import jazz21 as _j21; assert _j21.__version__ in out
    assert "Cmaj7" in out
    assert "dict" in out.lower() or "Canonical" in out


def test_describe_chord_demo_output() -> None:
    out = _run_demo(_extract_code(SITE_ROOT / "guias" / "acordes" / "describe-chord.html"))
    assert "Am7b5" in out
    assert "music21_figure" in out


def test_diccionarios_demo_output() -> None:
    out = _run_demo(_extract_code(SITE_ROOT / "python" / "diccionarios.html"))
    assert "Cmaj7" in out
    assert "Aø7" in out or "Am7b5" in out
    assert "Bbmaj9/D" in out


def test_normalizar_demo_output() -> None:
    out = _run_demo(_extract_code(SITE_ROOT / "guias" / "acordes" / "normalizar.html"))
    assert "C → C" in out or "C →" in out
    assert "Amb57" in out


def test_progression_demo_output() -> None:
    out = _run_demo(_extract_code(SITE_ROOT / "guias" / "notacion" / "progression.html"))
    assert "Errores:" in out
    assert "score-partwise" in out or "<score-partwise" in out


def test_inversiones_demo_output() -> None:
    out = _run_demo(_extract_code(SITE_ROOT / "guias" / "notacion" / "inversiones.html"))
    assert "Ciclo de 'Cmaj7'" in out
    assert "Plan de tour" in out


def test_guitar_diagramas_demo_output() -> None:
    out = _run_demo(_extract_code(SITE_ROOT / "guias" / "guitarra" / "diagramas.html"))
    assert "Opciones CAGED: 5" in out
    assert "__JAZZ21_GALLERY__" in out
    assert "[0] forma C" in out
    assert "[1] forma E" in out
    assert "shape_cycle=1" in out
    assert "forma: E" in out
    assert "traste: 8" in out
    marker = "__JAZZ21_GALLERY__"
    gallery_json = out.split(marker, 1)[1].split("\n")[0]
    gallery = json.loads(gallery_json)
    assert len(gallery) == 5
    assert all(item.get("svg", "").startswith("<svg") for item in gallery)


def test_manifest_demo_output() -> None:
    out = _run_demo(_extract_code(SITE_ROOT / "guias" / "manifest" / "to-manifest.html"))
    assert "C: C" in out or "C:" in out
    assert "??? → ERROR" in out
    assert "guitar options" in out


def test_site_html_has_playground_assets(site_demo: tuple[Path, str]) -> None:
    path, _ = site_demo
    text = path.read_text(encoding="utf-8")
    assert "pyodide-playground.js" in text
    assert "pyodide.js" in text


def test_guitar_page_has_svg_gallery_mode() -> None:
    text = (SITE_ROOT / "guias" / "guitarra" / "diagramas.html").read_text(encoding="utf-8")
    assert "data-svg-gallery" in text
    assert "pg-svg-gallery" in text
