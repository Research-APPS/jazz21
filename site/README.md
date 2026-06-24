# Sitio didáctico jazz21 (GitHub Pages)

Publicado en: **https://research-apps.github.io/jazz21/**

El workflow `.github/workflows/pages.yml` construye el wheel y despliega esta carpeta en cada push a `main`. En el repo, activa **Settings → Pages → Source: GitHub Actions** (una sola vez).

## Spike Pyodide

Prueba si jazz21 puede ejecutarse en el navegador.

```bash
# Desde la raíz del repo
python -m build --wheel -o site/wheels
cd site && python -m http.server 8765
```

Abre [http://localhost:8765/spike.html](http://localhost:8765/spike.html) y pulsa **Ejecutar spike**.

### Resultado esperado (pre-PyPI)

| Paso | Resultado |
|------|-----------|
| Pyodide + micropip | OK |
| `music21` desde PyPI | Probable OK (`py3-none-any` wheel) |
| `jazz21` desde PyPI | Falla (aún no publicado) |
| `jazz21` wheel local | OK si construiste `site/wheels/*.whl` |

En producción, el workflow de Pages construirá el wheel y los JSON/SVG de fallback antes del deploy.
