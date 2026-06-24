# jazz21

[![CI](https://github.com/Research-APPS/jazz21/actions/workflows/ci.yml/badge.svg)](https://github.com/Research-APPS/jazz21/actions/workflows/ci.yml)
[![Pages](https://github.com/Research-APPS/jazz21/actions/workflows/pages.yml/badge.svg)](https://github.com/Research-APPS/jazz21/actions/workflows/pages.yml)

**jazz21** is a practical jazz, lead-sheet, and guitar layer built on top of [music21](https://pypi.org/project/music21/).

Interactive guides (Spanish, Pyodide in the browser): **[research-apps.github.io/jazz21](https://research-apps.github.io/jazz21/)**

`music21` is excellent for symbolic music analysis, Roman numerals, MusicXML, and MIDI.  
`jazz21` exists to make that foundation easier to use in real-world jazz workflows: American chord spelling, lead-sheet progressions, slash chords, chord normalization, and guitar-friendly representations.

In short:

- use `music21` for general symbolic music infrastructure
- use `jazz21` when you want a more practical API for jazz harmony, lead sheets, and guitar-oriented applications

`jazz21` is designed as a reusable library layer. It can power apps such as CHORDIA, but it is also intended to work on its own in scripts, notebooks, APIs, and research tools.

## Quick Start

```python
import jazz21

print(jazz21.describe_chord("Cmaj7"))
print(jazz21.resolve_guitar_shapes("Am7"))
```

## Requirements

- Python 3.10+
- `pip` 23+ recommended
- `setuptools` 68+ and `wheel`

Older packaging tools may fail on editable installs from `pyproject.toml`. If in doubt, upgrade them first.

## Install

Development install with tests:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
pip install -e ".[dev]"
```

Optional guitar extra:

```bash
pip install -e ".[guitar]"
```

## Verify The Install

```bash
python -c "import jazz21; print(jazz21.__version__)"
pytest -q
```

## Modules

| Module | Role |
|--------|------|
| `jazz21.notation` | Lead-sheet parsing, American/jazz chord → music21, MusicXML/MIDI |
| `jazz21.symbols` | Chord symbol normalizer (canonical, intervals, MusicXML kind) |
| `jazz21.guitar` | CAGED shapes catalog, SVG diagrams, resolve from chord metadata |

## API Overview

| Entry point | Purpose | Returns |
|-------------|---------|---------|
| `american_chord_to_music21_figure(symbol)` | Convert American or jazz chord spelling into a `music21` chord figure | `str` |
| `parse_progression_to_musicxml(text, title=...)` | Parse a lead-sheet progression and export MusicXML | `dict` |
| `normalize_chord_symbol(symbol)` | Canonicalize a chord symbol and expose interval metadata | `dict | None` |
| `attach_guitar_shapes_to_chords(chords)` | Attach SVG guitar diagrams to chord metadata in place | `list[dict]` |
| `describe_chord(symbol)` | Produce a structured chord description for downstream publishing | `dict | None` |

## More Examples

```python
from jazz21.notation import (
    american_chord_to_music21_figure,
    parse_progression_to_musicxml,
)

american_chord_to_music21_figure("Bbmaj9/D")  # → music21 figure
out = parse_progression_to_musicxml("| Dm7 | G7 | Cmaj7 |", title="ii-V-I")
print(out["musicxml"][:200])
```

```python
from jazz21.guitar.resolve import attach_guitar_shapes_to_chords

chords = [{"kind": "major-seventh", "root_pc": 0, "symbol": "Cmaj7", "flat_index": 0}]
attach_guitar_shapes_to_chords(chords)  # uses built-in CAGED seed
print(chords[0]["guitar"]["svg"][:80])
```

```python
from jazz21 import describe_chord

print(describe_chord("Aø7"))
```

## Project Status

`jazz21` is early-stage but tested. The repository currently targets developers integrating notation, MusicXML, MIDI, or guitar-diagram generation into larger applications.

## Relationship to CHORDIA

CHORDIA uses jazz21 as its composition engine. The Django app is the client layer: UI, collections, and guitar views live there, while notation logic lives here.

The CHORDIA repository is not public yet, so this project should be treated as the public library layer.

## License

Released under the [MIT License](LICENSE).
