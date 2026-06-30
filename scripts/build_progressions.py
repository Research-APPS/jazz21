"""
Genera site/js/progressions.json con progresiones típicas analizadas por jazz21.
Uso: python scripts/build_progressions.py

Las progresiones están ordenadas por nivel de dificultad analítica (1–10):
  1  Tonal diatónico puro
  2  Dominantes secundarias
  3  Intercambio modal
  4  Menor tonal (armónico / melódico)
  5  Blues
  6  Modal (dorian, mixolydian, lydian, phrygian)
  7  Backdoor y sustitución de tritono (SubV)
  8  Coltrane changes y terceras
  9  Casos cromáticos puñeteros
  10 Modal ambiguo (Radio Micelio)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jazz21.manifest import analizar_progresion, describe_chord

# Octava base por nota (para síntesis de audio)
_PC_TO_OCTAVE_NOTE = {
    "C": "C4", "C#": "C#4", "Db": "Db4",
    "D": "D4", "D#": "D#4", "Eb": "Eb4",
    "E": "E4", "F": "F4", "F#": "F#4", "Gb": "Gb4",
    "G": "G3", "G#": "G#3", "Ab": "Ab3",
    "A": "A3", "A#": "A#3", "Bb": "Bb3",
    "B": "B3",
}


def chord_to_audio_notes(simbolo: str) -> list[str]:
    """Convierte un símbolo de acorde a notas con octava para Tone.js."""
    desc = describe_chord(simbolo)
    if not desc:
        return []
    pitches = desc.get("pitches", [])
    result = []
    for p in pitches[:4]:  # máximo 4 notas
        note = _PC_TO_OCTAVE_NOTE.get(p)
        if note:
            result.append(note)
    return result


RAW_PROGRESSIONS = [

    # ══════════════════════════════════════════════════════════════
    # NIVEL 1 · Tonal diatónico puro
    # ══════════════════════════════════════════════════════════════

    {"nivel": 1, "nombre": "ii-V-I (C)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Dm7", "G7", "Cmaj7"]},

    {"nivel": 1, "nombre": "ii-V-I (F)", "tonalidad": "F", "modo": "ionian",
     "acordes": ["Gm7", "C7", "Fmaj7"]},

    {"nivel": 1, "nombre": "I-VI-II-V (turnaround)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "Am7", "Dm7", "G7"]},

    {"nivel": 1, "nombre": "Rhythm Changes (A)", "tonalidad": "Bb", "modo": "ionian",
     "acordes": ["Bbmaj7", "Gm7", "Cm7", "F7"]},

    {"nivel": 1, "nombre": "I-V-vi-IV", "tonalidad": "C", "modo": "ionian",
     "acordes": ["C", "G", "Am", "F"]},

    {"nivel": 1, "nombre": "I-IV-V-I (G)", "tonalidad": "G", "modo": "ionian",
     "acordes": ["G", "C", "D", "G"]},

    {"nivel": 1, "nombre": "vi-IV-I-V", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Am", "F", "C", "G"]},

    {"nivel": 1, "nombre": "50s progression", "tonalidad": "C", "modo": "ionian",
     "acordes": ["C", "Am", "F", "G"]},

    {"nivel": 1, "nombre": "I-IV-V-I (C)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "Fmaj7", "G7", "Cmaj7"]},

    {"nivel": 1, "nombre": "I-III-vi-V (G)", "tonalidad": "G", "modo": "ionian",
     "acordes": ["G", "Em", "C", "D"]},

    {"nivel": 1, "nombre": "Ascenso diatónico (F)", "tonalidad": "F", "modo": "ionian",
     "acordes": ["Fmaj7", "Gm7", "Am7", "Bbmaj7"]},

    {"nivel": 1, "nombre": "Samba ii-V", "tonalidad": "Bb", "modo": "ionian",
     "acordes": ["Cm7", "F7", "Bbmaj7", "Gm7"]},

    # ══════════════════════════════════════════════════════════════
    # NIVEL 2 · Dominantes secundarias
    # ══════════════════════════════════════════════════════════════

    {"nivel": 2, "nombre": "V/ii · A7", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "A7", "Dm7", "G7"]},

    {"nivel": 2, "nombre": "V/vi · E7", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "E7", "Am7", "Dm7", "G7"]},

    {"nivel": 2, "nombre": "V/V · D7", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "D7", "G7", "Cmaj7"]},

    {"nivel": 2, "nombre": "Cadena de dominantes", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "B7", "Em7", "A7", "Dm7", "G7"]},

    {"nivel": 2, "nombre": "V/ii en Bb · G7", "tonalidad": "Bb", "modo": "ionian",
     "acordes": ["Bbmaj7", "G7", "Cm7", "F7"]},

    {"nivel": 2, "nombre": "Dominante final · A7", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Dm7", "G7", "Cmaj7", "A7"]},

    {"nivel": 2, "nombre": "I-III-IV-iv (plagal)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["C", "E7", "F", "Fm"]},

    # ══════════════════════════════════════════════════════════════
    # NIVEL 3 · Intercambio modal
    # ══════════════════════════════════════════════════════════════

    {"nivel": 3, "nombre": "bVII prestado", "tonalidad": "C", "modo": "ionian",
     "acordes": ["C", "Bb", "F", "C"]},

    {"nivel": 3, "nombre": "iv menor (plagal menor)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["C", "F", "Fm", "C"]},

    {"nivel": 3, "nombre": "Backdoor approach", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "Abmaj7", "Bb7", "Cmaj7"]},

    {"nivel": 3, "nombre": "Préstamo rock · bIII bVII", "tonalidad": "C", "modo": "ionian",
     "acordes": ["C", "Eb", "Bb", "F"]},

    {"nivel": 3, "nombre": "Viraje momentáneo", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "Cm7", "F7", "Bbmaj7"]},

    # ══════════════════════════════════════════════════════════════
    # NIVEL 4 · Menor tonal (armónico / melódico)
    # ══════════════════════════════════════════════════════════════

    {"nivel": 4, "nombre": "ii-V-I · menor (Am)", "tonalidad": "A", "modo": "aeolian",
     "acordes": ["Bm7b5", "E7", "Am7"]},

    {"nivel": 4, "nombre": "i-IV-V-i (menor)", "tonalidad": "A", "modo": "aeolian",
     "acordes": ["Am", "Dm", "E7", "Am"]},

    {"nivel": 4, "nombre": "i-bVI-V (menor)", "tonalidad": "A", "modo": "aeolian",
     "acordes": ["Am", "F", "E7", "Am"]},

    {"nivel": 4, "nombre": "i-bVII-bVI-V (menor natural)", "tonalidad": "A", "modo": "aeolian",
     "acordes": ["Am", "G", "F", "E7"]},

    {"nivel": 4, "nombre": "iiø-V-i", "tonalidad": "A", "modo": "aeolian",
     "acordes": ["Bm7b5", "E7", "Am"]},

    {"nivel": 4, "nombre": "i-iv-V-i (menor armónico)", "tonalidad": "A", "modo": "aeolian",
     "acordes": ["Am", "Dm", "E7", "Am"]},

    {"nivel": 4, "nombre": "i-bVI-bVII-i (rock menor)", "tonalidad": "A", "modo": "aeolian",
     "acordes": ["Am", "F", "G", "Am"]},

    {"nivel": 4, "nombre": "Menor melódica", "tonalidad": "A", "modo": "aeolian",
     "acordes": ["AmM7", "Dm7", "E7", "AmM7"]},

    {"nivel": 4, "nombre": "Bossa turnaround", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "Cm7", "Bm7b5", "E7"]},

    # ══════════════════════════════════════════════════════════════
    # NIVEL 5 · Blues
    # ══════════════════════════════════════════════════════════════

    {"nivel": 5, "nombre": "Blues Jazz (F)", "tonalidad": "F", "modo": "ionian",
     "acordes": ["F7", "Bb7", "F7", "C7"]},

    {"nivel": 5, "nombre": "Blues en G", "tonalidad": "G", "modo": "ionian",
     "acordes": ["G7", "C7", "G7", "D7"]},

    {"nivel": 5, "nombre": "Blues menor (Am)", "tonalidad": "A", "modo": "aeolian",
     "acordes": ["Am7", "Dm7", "Am7", "E7"]},

    {"nivel": 5, "nombre": "Blues básico (C)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["C7", "F7", "G7"]},

    {"nivel": 5, "nombre": "Blues jazz 12c (F)", "tonalidad": "F", "modo": "ionian",
     "acordes": ["F7", "Bb7", "F7", "F7", "Bb7", "Bdim7", "F7", "D7", "Gm7", "C7", "F7", "C7"]},

    # ══════════════════════════════════════════════════════════════
    # NIVEL 6 · Modal
    # ══════════════════════════════════════════════════════════════

    # Dórico
    {"nivel": 6, "nombre": "Dórico vamp (Dm7-G)", "tonalidad": "D", "modo": "dorian",
     "acordes": ["Dm7", "G", "Dm7", "G"]},

    {"nivel": 6, "nombre": "Dórico cadencia (I-II-I-bVII)", "tonalidad": "D", "modo": "dorian",
     "acordes": ["Dm7", "Em7", "Dm7", "C"]},

    {"nivel": 6, "nombre": "Dórico medieval", "tonalidad": "D", "modo": "dorian",
     "acordes": ["Dm", "Em", "F", "G"]},

    {"nivel": 6, "nombre": "Modal Dorian (I-II-IV-V7)", "tonalidad": "D", "modo": "dorian",
     "acordes": ["Dm7", "Em7", "Gm7", "A7"]},

    # Mixolidio
    {"nivel": 6, "nombre": "Mixolidio rock (G)", "tonalidad": "G", "modo": "mixolydian",
     "acordes": ["G", "F", "C", "G"]},

    # Lidio
    {"nivel": 6, "nombre": "Lidio II cadencia", "tonalidad": "C", "modo": "lydian",
     "acordes": ["Cmaj7", "D", "Cmaj7"]},

    {"nivel": 6, "nombre": "Lidio flotante", "tonalidad": "C", "modo": "lydian",
     "acordes": ["Cmaj7", "D", "Em7", "Cmaj7"]},

    # Frigio
    {"nivel": 6, "nombre": "Frigio corto (Em-F)", "tonalidad": "E", "modo": "phrygian",
     "acordes": ["Em", "F", "Em"]},

    {"nivel": 6, "nombre": "Andaluza (frigio)", "tonalidad": "A", "modo": "phrygian",
     "acordes": ["Am", "G", "F", "E"]},

    {"nivel": 6, "nombre": "Por arriba (Phrygian dominant)", "tonalidad": "E", "modo": "phrygian",
     "acordes": ["E", "F", "G", "E"]},

    # ══════════════════════════════════════════════════════════════
    # NIVEL 7 · Backdoor y sustitución de tritono (SubV)
    # ══════════════════════════════════════════════════════════════

    {"nivel": 7, "nombre": "Backdoor resolve (Bb7)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Dm7", "G7", "Cmaj7", "Bb7"]},

    {"nivel": 7, "nombre": "Backdoor puro (Bb7→I)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Bb7", "Cmaj7"]},

    {"nivel": 7, "nombre": "SubV (Db7→I)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Dm7", "Db7", "Cmaj7"]},

    {"nivel": 7, "nombre": "SubV extendido (G7→Db7→I)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Dm7", "G7", "Db7", "Cmaj7"]},

    {"nivel": 7, "nombre": "Cromatismo descendente", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Fmaj7", "Fm7", "Em7", "A7"]},

    # ══════════════════════════════════════════════════════════════
    # NIVEL 8 · Coltrane changes y terceras
    # ══════════════════════════════════════════════════════════════

    {"nivel": 8, "nombre": "Coltrane Changes (C)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "Eb7", "Abmaj7", "B7"]},

    {"nivel": 8, "nombre": "Coltrane expandido (B)", "tonalidad": "B", "modo": "ionian",
     "acordes": ["Bmaj7", "D7", "Gmaj7", "Bb7", "Ebmaj7"]},

    {"nivel": 8, "nombre": "Coltrane ciclo completo (C)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "Eb7", "Abmaj7", "B7", "Emaj7", "G7"]},

    {"nivel": 8, "nombre": "Terceras mayores (B)", "tonalidad": "B", "modo": "ionian",
     "acordes": ["Bmaj7", "Dmaj7", "Fmaj7"]},

    # ══════════════════════════════════════════════════════════════
    # NIVEL 9 · Casos cromáticos puñeteros
    # ══════════════════════════════════════════════════════════════

    {"nivel": 9, "nombre": "Semitono vecino (Db)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "Dbmaj7", "Cmaj7"]},

    {"nivel": 9, "nombre": "Ciclo aumentado", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "Ebmaj7", "Gbmaj7", "Amaj7"]},

    {"nivel": 9, "nombre": "Cromático descendente (C-Bb-Ab-G)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["C", "Bb", "Ab", "G"]},

    {"nivel": 9, "nombre": "Aproximación cromática a G7", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "A7", "Ab7", "G7"]},

    {"nivel": 9, "nombre": "Cadena SubV (5→1)", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "E7", "Eb7", "D7", "Db7", "Cmaj7"]},

    {"nivel": 9, "nombre": "Cadena SubV completa", "tonalidad": "C", "modo": "ionian",
     "acordes": ["Cmaj7", "F#7", "F7", "E7", "Eb7", "D7", "Db7", "Cmaj7"]},

    # ══════════════════════════════════════════════════════════════
    # NIVEL 10 · Modal ambiguo (Radio Micelio)
    # ══════════════════════════════════════════════════════════════

    {"nivel": 10, "nombre": "Lidio vamp (I-II-III-II)", "tonalidad": "C", "modo": "lydian",
     "acordes": ["Cmaj7", "D", "Em7", "D", "Cmaj7"]},

    {"nivel": 10, "nombre": "Eólico rock (Am)", "tonalidad": "A", "modo": "aeolian",
     "acordes": ["Am", "G", "F", "G"]},

    {"nivel": 10, "nombre": "Dórico ambiguo (Dm7-Bb)", "tonalidad": "D", "modo": "dorian",
     "acordes": ["Dm7", "G", "Dm7", "Bb"]},

    {"nivel": 10, "nombre": "Mixolidio con bVII-bVI", "tonalidad": "G", "modo": "mixolydian",
     "acordes": ["G", "F", "C", "Bb"]},

    {"nivel": 10, "nombre": "Lidio + préstamo bVII", "tonalidad": "C", "modo": "lydian",
     "acordes": ["Cmaj7", "D", "Bbmaj7", "Cmaj7"]},

    {"nivel": 10, "nombre": "Lidio → dominante secundaria", "tonalidad": "C", "modo": "lydian",
     "acordes": ["Cmaj7", "D", "E7", "Am7"]},
]


def build():
    result = []
    by_nivel: dict[int, int] = {}

    for raw in RAW_PROGRESSIONS:
        tonalidad = raw["tonalidad"]
        modo = raw["modo"]
        nivel = raw.get("nivel", 0)

        chord_list = []
        prog = analizar_progresion(tonalidad, raw["acordes"], modo)
        for sym, analisis in zip(raw["acordes"], prog["acordes"]):
            chord_list.append({
                "simbolo":      sym,
                "notas":        chord_to_audio_notes(sym),
                "grado":        analisis.get("grado"),
                "funcion":      analisis.get("funcion"),
                "tipo_funcion": analisis.get("tipo_funcion"),
                "diatonico":    analisis.get("diatonico", False),
                "confianza":    analisis.get("confianza"),
                "hints":        analisis.get("hints") or [],
            })

        entry: dict = {
            "nivel":     nivel,
            "nombre":    raw["nombre"],
            "tonalidad": tonalidad,
            "modo":      modo,
            "acordes":   chord_list,
        }
        if prog.get("patron"):
            entry["patron"] = prog["patron"]
        result.append(entry)
        by_nivel[nivel] = by_nivel.get(nivel, 0) + 1
        print(f"  N{nivel}  {raw['nombre']} ({tonalidad} {modo})")

    out = Path(__file__).parent.parent / "site" / "js" / "progressions.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n→ {out}  ({len(result)} progresiones)")
    for n in sorted(by_nivel):
        print(f"   nivel {n}: {by_nivel[n]}")


if __name__ == "__main__":
    build()
