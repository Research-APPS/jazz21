# jazz21

**jazz21** is a Python library for jazz and lead-sheet notation built **on top of [music21](https://pypi.org/project/music21/)**. It is not a replacement for music21.

music21 provides harmonic analysis, `ChordSymbol`, roman numerals, MusicXML, and MIDI. jazz21 adapts that stack to real-world jazz and American chord spelling, lead-sheet syntax (`%`, `/`, bar lines), inversion cycling, and (in later versions) guitar CAGED diagrams.

## Install

```bash
pip install -e .
```

Requires Python 3.10+ and music21 9+.

## Modules

| Module | Role |
|--------|------|
| `jazz21.notation` | Lead-sheet parsing, American/jazz chord → music21, MusicXML/MIDI |
| `jazz21.symbols` | Chord symbol normalizer (canonical, intervals, MusicXML kind) |
| `jazz21.guitar` | CAGED shapes catalog, SVG diagrams, resolve from chord metadata |

## Quick example

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
from jazz21.guitar import ShapesCatalog
from jazz21.guitar.resolve import attach_guitar_shapes_to_chords

chords = [{"kind": "major-seventh", "root_pc": 0, "symbol": "Cmaj7", "flat_index": 0}]
attach_guitar_shapes_to_chords(chords)  # uses built-in CAGED seed
print(chords[0]["guitar"]["svg"][:80])
```

## Relationship to CHORDIA

[CHORDIA](https://github.com/) uses jazz21 as its composition engine. The Django app is a client: UI, collections, and guitar views live in CHORDIA; notation logic lives here.

## License

MIT (align with your project policy).
