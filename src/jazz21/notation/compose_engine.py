"""
Motor de composición: progresión en cifrado americano → MusicXML vía music21.
Parte del paquete jazz21 (notation). Probado con music21 9.1.0+.
"""

from __future__ import annotations

import pathlib
import re
import tempfile
from collections import defaultdict
from typing import Any

DEFAULT_MAX_CHORDS = 64


def _analysis_key(key_fifths: int, key_mode: str):
    """Tonalidad de análisis (mayor/menor) a partir de armadura y modo MusicXML."""
    from music21 import key as m21key

    mode = (key_mode or "major").lower()
    if mode not in ("major", "minor"):
        mode = "major"
    return m21key.KeySignature(key_fifths).asKey(mode)


def _roman_object_to_figure_string(rn: Any) -> str:
    """
    Extrae texto de análisis (p. ej. ii7, V65) desde RomanNumeral.
    str(rn) suele ser <music21.roman.RomanNumeral …>, no sirve para la UI.
    """
    if rn is None:
        return ""
    fig = getattr(rn, "figure", None)
    if isinstance(fig, str) and fig.strip():
        return fig.strip()
    alone = getattr(rn, "romanNumeralAlone", None)
    written = getattr(rn, "figuresWritten", None)
    if isinstance(alone, str) and alone.strip():
        suf = ""
        if isinstance(written, str):
            suf = written
        elif isinstance(written, (list, tuple)):
            suf = "".join(str(x) for x in written if x is not None)
        elif written is not None:
            suf = str(written)
        combined = (alone.strip() + suf).strip()
        if combined:
            return combined
    # Fallback: parsear repr estándar de music21
    s = repr(rn) if hasattr(rn, "__repr__") else str(rn)
    if "RomanNumeral" in s and " in " in s:
        m = re.search(r"RomanNumeral\s+(\S+)\s+in\s+", s)
        if m:
            return m.group(1).strip()
    s2 = str(rn).strip()
    if s2.startswith("<") or "music21" in s2:
        return ""
    return s2


_ROMAN_HEAD_RE = re.compile(
    r"^([#b♯♭]*(?:[IVXLCDM]+|[ivxlcdm]+))",
    re.UNICODE,
)


def _extract_leading_roman_token(s: str) -> str:
    if not s:
        return ""
    m = _ROMAN_HEAD_RE.match(s.strip())
    return m.group(1) if m else ""


def _chordsymbol_quality_suffix(cs: Any) -> str:
    """
    Sufijo breve estilo jazz (7, 9, Δ7, ø7) desde chordKind de music21 / MusicXML.
    Evita pegar las cifras internas (75#3, b75bb42…) al numeral.
    """
    kind = (getattr(cs, "chordKind", None) or "").replace("_", "-").lower()
    if not kind:
        return ""
    if "half-diminished" in kind:
        return "ø7"
    if "diminished-seventh" in kind:
        return "°7"
    if kind == "diminished" or (kind.endswith("diminished") and "seventh" not in kind):
        return "°"
    if "minor-major" in kind:
        if "thirteenth" in kind:
            return "mΔ13"
        if "eleventh" in kind:
            return "mΔ11"
        if "ninth" in kind:
            return "mΔ9"
        if "seventh" in kind:
            return "mΔ7"
        return ""
    if "dominant-13" in kind or "major-13" in kind:
        return "13"
    if "dominant-11" in kind or "major-11" in kind:
        return "11"
    if "ninth" in kind:
        return "9"
    if "major-seventh" in kind:
        return "Δ7"
    if "minor-seventh" in kind:
        return "7"
    if "dominant" in kind:
        return "7"
    if "seventh" in kind:
        return "7"
    if "sixth" in kind:
        return "6"
    if "augmented" in kind:
        return "+"
    return ""


def _simplify_music21_figure_digits(s: str) -> str:
    """
    music21 a veces concatena grados como 7532 para acordes con 9ª;
    en análisis suele mostrarse …9 (p. ej. bVII7532 → bVII9).
    """
    if not s:
        return s
    out = s
    out = re.sub(
        r"([#b♯♭]*(?:[IVXLCDM]+|[ivxlcdm]+))7532(?=\b|/|$)",
        r"\g<1>9",
        out,
    )
    out = re.sub(
        r"([#b♯♭]*(?:[IVXLCDM]+|[ivxlcdm]+))75311(?=\b|/|$)",
        r"\g<1>11",
        out,
    )
    out = re.sub(
        r"([#b♯♭]*(?:[IVXLCDM]+|[ivxlcdm]+))75313(?=\b|/|$)",
        r"\g<1>13",
        out,
    )
    return out


def _format_roman_display(raw: str) -> str:
    """
    Cadena legible para UI: acerca la notación a ii / V7 / IΔ7 (Unicode).
    music21 suele usar 'maj7' o 'M7' para séptima mayor; Δ es la convención pedida.
    """
    if not raw:
        return ""
    s = str(raw).strip()
    s = _simplify_music21_figure_digits(s)
    s = re.sub(r"(?i)maj7", "Δ7", s)
    s = re.sub(r"(?i)maj\b", "Δ", s)
    # IM7, V7M7 rare — M7 inmediatamente tras numeral romano (mayúsculas)
    s = re.sub(r"([IVXLCDM]+)M7(?=\b|/|$)", r"\1Δ7", s)
    # iiM7-style if music21 emits lowercase roman + M7
    s = re.sub(r"([ivxlcdm]+)M7(?=\b|/|$)", r"\1Δ7", s)
    return s


def _roman_display_for_chord(ch: Any, cs: Any, key_obj: Any) -> str:
    from music21 import roman as m21roman

    def _rn_from_chord(prefer_secondary: bool) -> Any | None:
        try:
            try:
                return m21roman.romanNumeralFromChord(
                    ch, key_obj, preferSecondaryDominants=prefer_secondary
                )
            except TypeError:
                return m21roman.romanNumeralFromChord(ch, key_obj)
        except Exception:
            return None

    rn = _rn_from_chord(True)
    if rn is None:
        return "?"

    # En modo menor, D7 (IV7) y V7/VII (dominante de VII) son la misma torre armónica;
    # preferSecondaryDominants=True favorece la secundaria; para progresiones tipo i — IV7 — VII
    # la lectura diatónica IV es la pedida (véase feedback corpus).
    try:
        mode = (getattr(key_obj, "mode", None) or "").lower()
        if mode == "minor" and rn is not None:
            fig0 = (getattr(rn, "figure", None) or "").strip()
            if fig0 and re.search(r"/VII\b", fig0, flags=re.IGNORECASE):
                rn_alt = _rn_from_chord(False)
                if rn_alt is not None:
                    rn = rn_alt
    except Exception:
        pass

    suffix = _chordsymbol_quality_suffix(cs)
    alone = (getattr(rn, "romanNumeralAlone", None) or "").strip()
    fig = (getattr(rn, "figure", None) or "").strip()

    try:
        if "/" in fig:
            left_part, right_part = fig.split("/", 1)
            left_base = alone if alone else _extract_leading_roman_token(left_part)
            if not left_base:
                left_base = _extract_leading_roman_token(left_part)
            right_clean = _extract_leading_roman_token(right_part.strip())
            if not right_clean:
                right_clean = re.sub(
                    r"[^IVXLCDMivxlcdm#b♯♭].*$",
                    "",
                    right_part,
                    count=1,
                ).strip()
            if not right_clean:
                right_clean = "?"
            out = f"{left_base}{suffix}/{right_clean}"
            return _format_roman_display(out)

        if alone:
            return _format_roman_display(f"{alone}{suffix}")

        token = _extract_leading_roman_token(fig)
        if token:
            return _format_roman_display(f"{token}{suffix}")

        raw = _roman_object_to_figure_string(rn)
        if not raw:
            return "?"
        return _format_roman_display(raw)
    except Exception:
        return "?"

_DEGREE_LABELS: dict[int, str] = {
    0: 'T',  1: 'b2', 2: '2',  3: 'b3', 4: '3',  5: '4',
    6: 'b5', 7: '5',  8: 'b6', 9: '6',  10: 'b7', 11: '7',
}

# Grado simple (clase de altura) una octava más arriba → tensión (b9, 11, 13…)
_COMPOUND_DEGREE_FROM_SIMPLE_PC: dict[int, str] = {
    0: '8',
    1: 'b9',
    2: '9',
    3: 'b10',
    4: '10',
    5: '11',
    6: '#11',
    7: '12',
    8: 'b13',
    9: '13',
    10: 'b7',
    11: 'maj7',
}


def _degree_anchor_root_midi(pitches: list, root_pc: int | None) -> int | None:
    """
    MIDI de referencia para tensiones compuestas (9, 11, 13…).

    Si el bajo es la raíz, ancla = fundamental más grave del voicing.
    Si no (slash / inversión), baja una octava la fundamental más grave para que
    extensiones como la b9 no se etiqueten como b2 respecto a un SI en registro agudo.
    """
    if root_pc is None or not pitches:
        return None
    root_midis = [int(p.midi) for p in pitches if int(p.pitchClass) == int(root_pc)]
    if not root_midis:
        return int(pitches[0].midi)
    low_root = min(root_midis)
    bass_pc = int(pitches[0].pitchClass)
    if bass_pc == int(root_pc):
        return low_root
    return low_root - 12


def _degree_label_for_pitch_over_root_anchor(
    pitch: Any,
    *,
    root_pc: int,
    root_ref_midi: int,
    treat_m2_as_b9: bool = False,
) -> str:
    """
    Etiqueta de grado respecto a la raíz del acorde, con tensiones compuestas (b9 no como b2)
    cuando la nota está a ≥ una octava por encima de la fundamental más grave del bloque.
    """
    simple_pc = (int(pitch.pitchClass) - root_pc) % 12
    diff = int(pitch.midi) - int(root_ref_midi)
    if simple_pc == 0:
        if diff == 0:
            return 'T'
        if diff > 0 and diff % 12 == 0:
            return _COMPOUND_DEGREE_FROM_SIMPLE_PC[0]
        if diff < 0:
            return 'T'
    if (
        treat_m2_as_b9
        and simple_pc == 1
        and 0 <= diff < 12
    ):
        return 'b9'
    if diff < 0:
        return _DEGREE_LABELS.get(simple_pc, '?')
    if diff < 12:
        return _DEGREE_LABELS.get(simple_pc, '?')
    return _COMPOUND_DEGREE_FROM_SIMPLE_PC.get(
        simple_pc, _DEGREE_LABELS.get(simple_pc, '?')
    )


def _degree_labels_for_voicing(
    pitches: list,
    root_pc: int | None,
    *,
    treat_m2_as_b9: bool = False,
) -> list[str]:
    if root_pc is None:
        return ['?'] * len(pitches)
    ref = _degree_anchor_root_midi(pitches, root_pc)
    if ref is None:
        return ['?'] * len(pitches)
    return [
        _degree_label_for_pitch_over_root_anchor(
            p,
            root_pc=root_pc,
            root_ref_midi=ref,
            treat_m2_as_b9=treat_m2_as_b9,
        )
        for p in pitches
    ]

_ROOT_DISPLAY = re.compile(r"^([A-Ga-g])(bb|b|#|##)?$", re.UNICODE)

# Punto ASCII final tras doble espacio (móvil / teclado): "Gmaj7." → "Gmaj7". No toca "N.C." (no empieza por A–G).
_TRAILING_CHORD_DOTS = re.compile(
    r"^(?P<base>[A-Ga-g][A-Za-z0-9#+°º\-\(\)\/]*)\.+$",
    re.UNICODE,
)

# Mac / teclados: punto medio, viñeta o barra vertical ancha en lugar de |;
# NBSP y otros espacios que no cuadran con "  " (solo U+0020).
_MAC_BAR_CHARS = (
    "\u00b7"  # · middle dot (muy habitual como “punto Mac” entre teclas)
    "\u2022"  # • bullet
    "\u2219"  # ∙ bullet operator
    "\u22c5"  # ⋅ dot operator
    "\uff5c"  # ｜ fullwidth vertical line
)
_SPACE_CHARS = (
    "\u00a0"  # NBSP
    "\u202f"  # narrow no-break space
    "\u2007"  # figure space
    "\u2009"  # thin space
    "\u200a"  # hair space
    "\u3000"  # ideographic space
)


def _normalize_mac_keyboard_text(text: str) -> str:
    if not text:
        return ""
    t = str(text)
    for ch in _SPACE_CHARS:
        t = t.replace(ch, " ")
    trans = str.maketrans({c: "|" for c in _MAC_BAR_CHARS})
    t = t.translate(trans)
    return t


def normalize_progression(text: str) -> str:
    """Unicode “Mac-friendly” + dos o más espacios = separador de compás (como |)."""
    if not text:
        return ""
    t = _normalize_mac_keyboard_text(text)
    t = re.sub(r" {2,}", " | ", t)
    return t.strip()


def strip_trailing_chord_dots(symbol: str) -> str:
    """Remove trailing dot ornament from a chord token (e.g. ``Dm7.`` → ``Dm7``)."""
    s = symbol.strip()
    if not s:
        return s
    m = _TRAILING_CHORD_DOTS.fullmatch(s)
    return m.group("base") if m else s


def _trim_decorative_final_barline(t: str) -> str:
    """Quita un | final suelto (p. ej. … G7 |); no altera … || … (compás vacío explícito)."""
    t = t.rstrip()
    while t.endswith("|"):
        if t.endswith("||"):
            break
        t = t[:-1].rstrip()
    return t


def _is_percent_only_measure(row: list[str]) -> bool:
    """Compás formado solo por % (uno o varios)."""
    if not row:
        return False
    return all((tok or "").strip() == "%" for tok in row)


def _tokenize_lead_sheet_segment(seg_st: str) -> list[str]:
    """Espacios separan símbolos; C/E es un símbolo unido por '/'."""
    out: list[str] = []
    for x in re.split(r"\s+", seg_st):
        if not x:
            continue
        xs = strip_trailing_chord_dots(x.strip())
        # Pegado tipo "|Dm7" (sin espacio tras compás) — quita tuberías residuales.
        xs = xs.lstrip("|\u2502").strip()
        if xs:
            out.append(xs)
    return out


def split_measures_tokenized(canonical_pipe_text: str) -> list[list[str]]:
    """
    Parte texto ya normalizado (| de compás, newline → |).
    Una lista de símbolos por compás antes de aplicar % o / repetición.
    """
    rows: list[list[str]] = []
    if not canonical_pipe_text:
        return rows
    for seg in canonical_pipe_text.split("|"):
        rows.append(_tokenize_lead_sheet_segment(seg.strip()))
    return rows


def expand_lead_sheet_measures(measures_tokenized: list[list[str]]) -> list[list[str]]:
    """
    Reglas lead sheet:
    - % en todo el compás = repetir el compás anterior expandido (si no hay, silencio).
    - / = repetir el acorde anterior en el compás, o el último acorde audible si el compás iba vacío hasta aquí.
    """
    out: list[list[str]] = []
    prev_expanded: list[str] = []
    last_audible: str | None = None

    for row in measures_tokenized:
        if _is_percent_only_measure(row):
            cur = list(prev_expanded)
            out.append(cur)
            prev_expanded = cur
            if cur:
                last_audible = cur[-1]
            continue

        if not row:
            out.append([])
            prev_expanded = []
            continue

        cur: list[str] = []
        for tok in row:
            t = (tok or "").strip()
            if t == "/":
                if cur:
                    cur.append(cur[-1])
                elif last_audible is not None:
                    cur.append(last_audible)
            elif t == "%":
                cur.append("%")
            else:
                tt = strip_trailing_chord_dots(t)
                if tt:
                    cur.append(tt)
        out.append(cur)
        prev_expanded = cur
        if cur:
            last_audible = cur[-1]
    return out


def parse_lead_sheet(progression: str) -> dict[str, Any]:
    """
    Capa léxica vs expandida (para harmonía/OSMD/music21 usar siempre expanded).

    - raw: entrada recortada.
    - measures: símbolos por compás (tokens con % y como / sueltos, sin repetir barras ni acordes).
    - expanded: compases con % y / resueltos en lista de símbolos listos para music21.
    """
    raw = progression.strip()
    t = normalize_progression(progression)
    if not t:
        return {"raw": raw, "measures": [], "expanded": []}
    canon = _trim_decorative_final_barline(re.sub(r"[\n\r]+", "|", t))
    measures = split_measures_tokenized(canon)
    expanded = expand_lead_sheet_measures(measures)
    return {"raw": raw, "measures": measures, "expanded": expanded}


def measures_from_progression(text: str) -> list[list[str]]:
    """
    Lista de compases ya expandidos (tipo lead sheet).

    Separadores de compás: | (|| = compás vacío). Nueva línea = |.
    Espacios = acordes en el mismo compás.

    Durante el parse:

    - % solo en el compás = repetir todo el compás anterior.
    - / repite el acorde anterior dentro del compás (o el último acorde del compás previo si aún no hay ninguno aquí).

    Slash chord (Dm7/E) debe ir sin espacios alrededor del / entre raíz y bajo.
    """
    parsed = parse_lead_sheet(text)
    return parsed["expanded"]


def tokenize_progression(text: str) -> list[str]:
    """Lista plana de todos los símbolos (para compatibilidad y límites)."""
    return [c for bar in measures_from_progression(text) for c in bar]


_AMERICAN_ROOT = re.compile(
    r"^([A-Ga-g])(bb|##|b|\u266d|#|\u266f|x)?(.*)$",
    re.UNICODE,
)

# Nota de bajo en slash (Gm/Bb); hay que mapear bemol 'b' a '-' para music21.
_SLASH_BASS_NOTE = re.compile(
    r"^([A-Ga-g])(bb|##|b|\u266d|#|\u266f|x)?$",
    re.UNICODE,
)

# Ej.: B(b9) → triada mayor + 9♭ (Baddb9); Bm7(b9) → Bm7b9; B♭(b9) → Bbaddb9
_PAREN_FLAT_NINTH = re.compile(
    r"^(.*)\(\s*(?:b|♭|\u266d)\s*9\s*\)\s*$",
    re.UNICODE | re.IGNORECASE,
)


def _expand_parenthetical_flat_ninth(symbol: str) -> str:
    """
    Notación «triada/cualidad + (b9) o (♭9)» → sufijo music21 (addb9, m7b9, …).
    No sustituye Bb9 (Si♭ con novena): solo paréntesis explícitos tras la raíz.
    """
    s = (symbol or "").strip()
    if not s or "(" not in s:
        return s
    slash = ""
    head = s
    if "/" in s:
        head, bass = s.split("/", 1)
        head = head.strip()
        slash = "/" + bass.strip()
    mroot = _AMERICAN_ROOT.match(head)
    if not mroot:
        return s
    rest = (mroot.group(3) or "").strip()
    pm = _PAREN_FLAT_NINTH.match(rest)
    if not pm:
        return s
    prefix = pm.group(1).strip()
    letter = mroot.group(1).upper()
    acc = mroot.group(2) or ""
    acc_tok = ""
    if acc in ("bb",):
        acc_tok = "bb"
    elif acc in ("b", "\u266d"):
        acc_tok = "b"
    elif acc in ("#",):
        acc_tok = "#"
    elif acc in ("##", "\u266f", "x"):
        acc_tok = "##"
    pl = prefix.lower()
    if not prefix:
        new_suffix = "addb9"
    elif pl in ("m", "min"):
        new_suffix = "maddb9"
    else:
        new_suffix = prefix + "b9"
    return letter + acc_tok + new_suffix + slash


# Dominante suspendido en cifrado compacto; music21 no reconoce «13sus4» ni «9sus».
_JAZZ_DOM_SUS_COMPACT_TO_M21: dict[str, str] = {
    "13sus4": "7sus4add9add13",
    "13sus": "7sus4add9add13",
    "11sus4": "7sus4add9add11",
    "11sus": "7sus4add9add11",
    "9sus4": "7sus4add9",
    "9sus": "7sus4add9",
}


def _normalize_quality_suffix_for_music21(rest: str) -> str:
    """
    Aliases de leadsheet no reconocidos por music21.harmony.ChordSymbol.
    Solo el sufijo tras la raíz (sin bajo /…).

    Incluye: menor+maj7 (mmaj7), dominant suspendido compacto (13sus4 → 7sus4add9add13), …
    """
    r = (rest or "").strip()
    if not r:
        return r
    r = "".join(r.split())
    repl_sus = _JAZZ_DOM_SUS_COMPACT_TO_M21.get(r.lower())
    if repl_sus is not None:
        r = repl_sus
    # Menor + extensión con 7ª mayor (Bmmaj7, Bm(maj7), B m (maj7)): music21 → mM<n> / minmaj<n>.
    r = re.sub(r"(?i)^m\s*\(\s*maj\s*(\d{1,2})\s*\)", r"mM\1", r)
    r = re.sub(r"(?i)^minmaj(\d{1,2})\b", r"minmaj\1", r)
    r = re.sub(r"(?i)^mmaj7\b", "mM7", r)
    # Disminuido con ordinal tipográfico: C#º7, E°7
    if r[0] in ("\u00ba", "\u00b0"):  # º °
        tail = r[1:]
        if tail == "7":
            return "dim7"
        if tail == "":
            return "dim"
        if tail.startswith("7") and len(tail) > 1:
            return "dim7" + tail[1:]
        return "dim" + tail
    # No tocar «maj9/11/13» dentro de «minmaj…» (p. ej. minmaj11 → no convertir a minM11).
    if not re.match(r"(?i)^minmaj", r):
        r = re.sub(r"(?i)maj13\b", "M13", r)
        r = re.sub(r"(?i)maj11\b", "M11", r)
        r = re.sub(r"(?i)maj9\b", "M9", r)
    r = re.sub(r"(?i)7\s*alt\b", "7", r)
    return r


def american_chord_to_music21_figure(symbol: str) -> str:
    """
    Cifrado tipo americano (Bb, Eb, F#m7) → figura que entiende music21.
    music21 usa '-' para bemol en la raíz, no 'b' (Bb falla; B- es Si♭ mayor).
    Lo mismo aplica al bajo tras '/': Gm/Bb provoca error ('mb'); debe ser Gm/B-.
    """
    s = _expand_parenthetical_flat_ninth(symbol.strip())
    if not s:
        return s
    bass_raw: str | None = None
    head = s
    if "/" in s:
        head, bass_raw = s.split("/", 1)
        head = head.strip()
        bass_raw = bass_raw.strip()
    m = _AMERICAN_ROOT.match(head.strip())
    if not m:
        return s
    letter = m.group(1).upper()
    acc = m.group(2) or ""
    rest = _normalize_quality_suffix_for_music21(m.group(3) or "")
    if acc in ("bb",):
        acc_m21 = "--"
    elif acc in ("b", "\u266d"):  # ♭
        acc_m21 = "-"
    elif acc in ("#",):
        acc_m21 = "#"
    elif acc in ("##", "\u266f", "x"):  # ♯, x = doble sostenido alternativo
        acc_m21 = "##"
    else:
        acc_m21 = ""
    core = letter + acc_m21 + rest
    if bass_raw is None:
        return core
    bm = _SLASH_BASS_NOTE.match(bass_raw)
    if bm is None:
        return core + "/" + bass_raw
    b_letter = bm.group(1).upper()
    b_acc = bm.group(2) or ""
    if b_acc in ("bb",):
        b_m21 = "--"
    elif b_acc in ("b", "\u266d"):
        b_m21 = "-"
    elif b_acc in ("#",):
        b_m21 = "#"
    elif b_acc in ("##", "\u266f", "x"):
        b_m21 = "##"
    else:
        b_m21 = ""
    return core + "/" + b_letter + b_m21


def _token_implies_flat_ninth(token: str) -> bool:
    """
    Símbolos con ♭9 armónica explícita: la clase 1 sobre la raíz se muestra como b9
    aunque el voicing real sea una 2ª menor adyacente (diff < 12 MIDI).
    """
    s = (token or "").strip()
    if not s:
        return False
    if _expand_parenthetical_flat_ninth(s) != s:
        return True
    fig = american_chord_to_music21_figure(s).lower()
    if "addb9" in fig or "7b9" in fig or "maj7b9" in fig:
        return True
    return False


def _user_root_display(letter: str, acc: str) -> str:
    """Representación en cifrado americano de la raíz (p. ej. Bb, A#, D)."""
    if acc in ("bb",):
        return letter + "bb"
    if acc in ("b", "\u266d"):
        return letter + "b"
    if acc in ("#",):
        return letter + "#"
    if acc in ("##", "\u266f", "x"):
        return letter + "##"
    return letter


def _parse_root_display(display: str) -> tuple[str, str] | None:
    """'Bb' → (B, 'b'); 'A#' → (A, '#'); 'D' → (D, '')."""
    m = _ROOT_DISPLAY.match(display.strip())
    if not m:
        return None
    letter = m.group(1).upper()
    acc = (m.group(2) or "").lower()
    return letter, acc


def _build_american_token(letter: str, acc: str, suffix: str) -> str:
    """acc: '', 'b', 'bb', '#', '##' (minúsculas)."""
    a = acc if acc else ""
    return letter + a + suffix


def _measures_to_progression_string(measures: list[list[str]]) -> str:
    return " | ".join(" ".join(bar) for bar in measures)


_OCT_END = re.compile(r"\d+$")


def pitch_american_no_octave(p: Any) -> str:
    """Altura tipo C, Bb2 → Bb para uso en slash (sin número de octava)."""
    s = pitch_american_with_octave(p)
    return _OCT_END.sub("", s)


def _ordered_pitch_classes_for_rotation(cs) -> list[int]:
    """
    Clases de tono ordenadas por distancia cromática ascendente desde la raíz
    del símbolo (0 = raíz, luego notas que suben en el círculo sin duplicar clase).

    Cuando no hay raíz (raro), orden cromático desde la nota más grave del voicing.
    Así el «tour» rota bajos sin depender de ``Chord.inversion`` de music21
    (falla en símbolos extendidos/alterados densos).
    """
    pcs_m21 = list(cs.pitches)
    if not pcs_m21:
        return []
    pitch_classes = sorted({int(p.pitchClass) for p in pcs_m21})
    root = None
    try:
        root = cs.root()
    except Exception:
        root = None
    if root is None:
        bass_pc = int(min(pcs_m21, key=lambda p: float(p.ps)).pitchClass)
        return sorted(pitch_classes, key=lambda pc: (pc - bass_pc) % 12)
    root_pc = int(root.pitchClass)
    return sorted(pitch_classes, key=lambda pc: (pc - root_pc) % 12)


def _pick_spelled_pitch_for_pc(pitches: list[Any], target_pc: int) -> Any | None:
    for p in sorted(pitches, key=lambda x: float(x.ps)):
        if int(p.pitchClass) == int(target_pc):
            return p
    return None


def _next_inversion_via_pitch_rotation(
    cs,
    c_m21,
    head: str,
    inv_cur_m21: int,
) -> dict[str, Any] | None:
    """
    Fallback si ``Chord.inversion(n)`` lanza: siguiente bajo = siguiente clase de tono
    en el ciclo ``_ordered_pitch_classes_for_rotation``.
    """
    ordered = _ordered_pitch_classes_for_rotation(cs)
    n = len(ordered)
    if n < 2:
        return None
    bass = c_m21.bass()
    if bass is None:
        return None
    bass_pc = int(bass.pitchClass)
    try:
        idx = ordered.index(bass_pc)
    except ValueError:
        idx = max(0, int(inv_cur_m21)) % n
    next_idx = (idx + 1) % n
    target_pc = ordered[next_idx]
    bs = _pick_spelled_pitch_for_pc(list(c_m21.pitches), target_pc)
    if bs is None:
        bs = _pick_spelled_pitch_for_pc(list(cs.pitches), target_pc)
    if bs is None:
        return None
    new_sym = head if next_idx == 0 else head + "/" + pitch_american_no_octave(bs)
    return {
        "ok": True,
        "next_symbol": new_sym,
        "current_inversion": idx,
        "target_inversion": next_idx,
        "num_pitches": n,
        "unchanged": False,
        "inversion_engine": "pitch_rotation",
    }


def analyze_chord_inversion_step(token: str) -> dict[str, Any]:
    """
    Calcula la siguiente inversión de un token de cifrado.

    Usa music21 para el paso normal; si ``Chord.inversion`` falla (símbolos densos,
    extensiones, etc.), aplica rotación de bajo sobre las clases de tono ordenadas
    desde la raíz del ``ChordSymbol`` (motor propio, music21 solo aporta notas).
    """
    import copy

    from music21 import chord as m21chord
    from music21 import harmony

    raw = (token or "").strip()
    if not raw:
        return {
            "ok": False,
            "symbol": raw,
            "reason": "empty",
            "message": "El símbolo del acorde está vacío.",
            "current_inversion": None,
            "target_inversion": None,
            "num_pitches": None,
        }
    try:
        fig = american_chord_to_music21_figure(raw)
        cs = harmony.ChordSymbol(fig)
    except Exception:
        return {
            "ok": False,
            "symbol": raw,
            "reason": "parse_error",
            "message": (
                "No se pudo interpretar el símbolo para invertir "
                "(cifrado no reconocido por music21)."
            ),
            "current_inversion": None,
            "target_inversion": None,
            "num_pitches": None,
        }
    pcs = list(cs.pitches)
    if not pcs:
        return {
            "ok": False,
            "symbol": raw,
            "reason": "no_pitches",
            "message": "El símbolo no produjo ninguna nota; no se puede invertir.",
            "current_inversion": None,
            "target_inversion": None,
            "num_pitches": 0,
        }
    c = m21chord.Chord(pcs)
    inv_cur = c.inversion()
    if inv_cur is None:
        inv_cur = 0
    n = len(c.pitches)
    if n < 2:
        return {
            "ok": True,
            "next_symbol": raw,
            "current_inversion": inv_cur,
            "target_inversion": inv_cur,
            "num_pitches": n,
            "unchanged": True,
        }
    next_inv = (inv_cur + 1) % n
    head = raw.split("/", 1)[0].strip()
    try:
        c2 = copy.deepcopy(c)
        c2.inversion(next_inv)
    except Exception:
        fb = _next_inversion_via_pitch_rotation(cs, c, head, inv_cur)
        if fb is None:
            return {
                "ok": False,
                "symbol": raw,
                "reason": "inversion_failed",
                "message": (
                    "No se pudo aplicar la siguiente inversión "
                    "(límite de music21 con este símbolo o voicing)."
                ),
                "current_inversion": inv_cur,
                "target_inversion": next_inv,
                "num_pitches": n,
            }
        return fb
    bs = c2.bass()
    if bs is None:
        fb = _next_inversion_via_pitch_rotation(cs, c, head, inv_cur)
        if fb is not None:
            return fb
        return {
            "ok": False,
            "symbol": raw,
            "reason": "no_bass",
            "message": "No se pudo obtener el bajo tras la inversión.",
            "current_inversion": inv_cur,
            "target_inversion": next_inv,
            "num_pitches": n,
        }
    if next_inv == 0:
        new_sym = head
    else:
        new_sym = head + "/" + pitch_american_no_octave(bs)
    return {
        "ok": True,
        "next_symbol": new_sym,
        "current_inversion": inv_cur,
        "target_inversion": next_inv,
        "num_pitches": n,
        "unchanged": False,
        "inversion_engine": "music21",
    }


def advance_chord_inversion(token: str) -> str | None:
    """
    Siguiente inversión en ciclo según las notas del símbolo (music21 y, si falla,
    rotación de bajo propia sin depender de ``Chord.inversion``).

    Ej.: C ↔ C/E ↔ C/G; Am7 con cuatro alturas cicla en cuatro grillas de bajo.
    """
    d = analyze_chord_inversion_step(token)
    if not d.get("ok"):
        return None
    return str(d.get("next_symbol") or "")


def replace_chord_with_next_inversion_detail(
    progression: str, flat_index: int
) -> dict[str, Any]:
    """
    Como ``replace_chord_with_next_inversion`` pero con detalle para la API/UI.

    Éxito: ``ok``, ``progression``, ``flat_index``, ``symbol`` (token original),
    ``next_symbol``, ``current_inversion``, ``target_inversion``, ``num_pitches``, ``unchanged``.

    Fallo: ``ok`` False, ``message``, ``reason``, ``flat_index``, ``symbol`` (o None si índice inválido).
    """
    measures = measures_from_progression(progression)
    fi = 0
    for bar in measures:
        for ti, tok in enumerate(bar):
            if fi == flat_index:
                step = analyze_chord_inversion_step(tok)
                if not step.get("ok"):
                    out = {k: v for k, v in step.items() if k != "ok"}
                    out["flat_index"] = flat_index
                    return {"ok": False, **out}
                new_t = str(step.get("next_symbol") or "")
                bar[ti] = new_t
                return {
                    "ok": True,
                    "progression": _measures_to_progression_string(measures),
                    "flat_index": flat_index,
                    "symbol": tok,
                    "next_symbol": new_t,
                    "current_inversion": step["current_inversion"],
                    "target_inversion": step["target_inversion"],
                    "num_pitches": step["num_pitches"],
                    "unchanged": step.get("unchanged", False),
                    "inversion_engine": step.get("inversion_engine"),
                }
            fi += 1
    return {
        "ok": False,
        "symbol": None,
        "flat_index": flat_index,
        "reason": "index_out_of_range",
        "message": (
            f"No hay acorde en la posición #{flat_index} "
            "(índice fuera de rango respecto a la progresión actual)."
        ),
        "current_inversion": None,
        "target_inversion": None,
        "num_pitches": None,
    }


def replace_chord_with_next_inversion(progression: str, flat_index: int) -> str | None:
    """Sustituye el acorde en la posición plana `flat_index` por su siguiente inversión."""
    r = replace_chord_with_next_inversion_detail(progression, flat_index)
    if not r.get("ok"):
        return None
    return str(r.get("progression") or "")


def chord_inversion_cycle_length(token: str) -> int:
    """
    Cuántas inversiones distintas al rotar con ``advance_chord_inversion`` (ciclo completo).
    Devuelve 0 si el token no es invertible; 1 si no hay rotación real (menos de 2 alturas).
    """
    d = analyze_chord_inversion_step((token or "").strip())
    if not d.get("ok"):
        return 0
    n = int(d.get("num_pitches") or 0)
    if n < 2:
        return 1
    return n


def build_inversion_tour_plan(progression: str) -> list[tuple[int, int]]:
    """
    Plan de «tour» por la progresión: lista de ``(flat_index, pasos)`` en orden,
    donde ``pasos`` es la longitud del ciclo de inversión de ese acorde.
    """
    measures = measures_from_progression(progression)
    plan: list[tuple[int, int]] = []
    fi = 0
    for bar in measures:
        for tok in bar:
            n = chord_inversion_cycle_length(tok)
            if n > 0:
                plan.append((fi, n))
            fi += 1
    return plan


def total_inversion_tour_steps(progression: str) -> int:
    """Return the total number of inversion steps across a lead-sheet progression."""
    return sum(n for _fi, n in build_inversion_tour_plan(progression))


def enharmonic_conflicts_from_parsed(
    success_entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    success_entries: {index, token, cs} por acorde parseado OK.
    Detecta misma pitchClass con distinta escritura de raíz (p. ej. Bb vs A#).
    """
    by_pc_spellings: dict[int, set[str]] = defaultdict(set)
    by_pc_occ: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for ent in success_entries:
        tok = ent["token"]
        cs = ent["cs"]
        flat_i = ent["index"]
        root = cs.root()
        if root is None:
            continue
        pc = int(root.pitchClass)
        m = _AMERICAN_ROOT.match(tok.strip())
        if not m:
            continue
        letter = m.group(1).upper()
        acc = m.group(2) or ""
        ud = _user_root_display(letter, acc)
        by_pc_spellings[pc].add(ud)
        by_pc_occ[pc].append(
            {
                "flat_index": flat_i,
                "token": tok,
                "root_display": ud,
            }
        )

    conflicts: list[dict[str, Any]] = []
    for pc in sorted(by_pc_spellings.keys()):
        spellings = by_pc_spellings[pc]
        if len(spellings) < 2:
            continue
        conflicts.append(
            {
                "pitch_class": pc,
                "spellings": sorted(spellings, key=lambda s: (len(s), s)),
                "occurrences": by_pc_occ[pc],
            }
        )
    return conflicts


def apply_enharmonic_root_spelling(
    progression: str, pitch_class: int, target_root_display: str
) -> str | None:
    """Unifica la escritura de la raíz para todos los acordes con esa pitch class."""
    from music21 import harmony

    parsed_root = _parse_root_display(target_root_display)
    if parsed_root is None:
        return None
    new_letter, new_acc = parsed_root

    measures = measures_from_progression(progression)
    new_measures: list[list[str]] = []
    for bar in measures:
        new_bar: list[str] = []
        for tok in bar:
            try:
                fig = american_chord_to_music21_figure(tok)
                cs = harmony.ChordSymbol(fig)
                r = cs.root()
                if r is not None and int(r.pitchClass) == int(pitch_class):
                    m = _AMERICAN_ROOT.match(tok.strip())
                    sfx = m.group(3) if m else ""
                    new_bar.append(_build_american_token(new_letter, new_acc, sfx))
                else:
                    new_bar.append(tok)
            except Exception:
                new_bar.append(tok)
        new_measures.append(new_bar)
    return _measures_to_progression_string(new_measures)


def _voicing_pitches(cs) -> list:
    """Lleva las notas a un rango legible en pentagrama (aprox. A2–G5)."""
    from music21 import chord as m21chord

    ps = list(cs.pitches)
    if not ps:
        return []
    ch = m21chord.Chord(ps)
    # Octavas con P8 (no transpose(12)): el cromático respella p. ej. D#→E♭ y
    # rompe acordes con alteraciones (B7♭9) y el análisis romano (p. ej. A♭→G#).
    while ch.bass().midi < 55:
        ch = ch.transpose("P8")
    while ch.bass().midi > 72:
        ch = ch.transpose("-P8")
    return list(ch.pitches)


def pitch_american_with_octave(p) -> str:
    """Altura para UI: Bb3, F#4 (mismo criterio que el cifrado americano)."""
    step = p.step
    o = p.octave
    acc = p.accidental
    if acc is None:
        acc_s = ""
    else:
        al = int(round(float(acc.alter)))
        if al <= -2:
            acc_s = "bb"
        elif al == -1:
            acc_s = "b"
        elif al == 1:
            acc_s = "#"
        elif al >= 2:
            acc_s = "##"
        else:
            acc_s = ""
    return f"{step}{acc_s}{o}"


_MELODY_DURATION_QL: dict[str, float] = {
    "whole": 4.0,
    "half": 2.0,
    "quarter": 1.0,
    "eighth": 0.5,
    "sixteenth": 0.25,
    "thirty-second": 0.125,
}


def _dotted_quarter_length(base_ql: float, dots: int) -> float:
    """Quarter length incl. puntillo(s) clásicos (1.5, 1.75, …)."""
    if dots <= 0:
        return base_ql
    total = base_ql
    add = base_ql * 0.5
    for _ in range(dots):
        total += add
        add *= 0.5
    return total


def _melody_pitch_from_payload(d: dict[str, Any]) -> Any:
    from music21 import pitch as m21pitch

    step = str(d.get("step", "C")).strip()[:1].upper()
    if step not in ("A", "B", "C", "D", "E", "F", "G"):
        step = "C"
    try:
        alter = int(d.get("alter", 0) or 0)
    except (TypeError, ValueError):
        alter = 0
    try:
        octave = int(d.get("octave", 4))
    except (TypeError, ValueError):
        octave = 4
    octave = max(0, min(9, octave))
    p = m21pitch.Pitch()
    p.step = step
    p.octave = octave
    if alter:
        p.accidental = m21pitch.Accidental(alter)
    return p


def _events_to_melody_measure(
    events: list[dict[str, Any]] | None,
    *,
    time_sig_ql: float = 4.0,
) -> tuple[Any, list[str]]:
    """
    Construye un Measure de melodía desde JSON.
    Devuelve (Measure, warnings).
    """
    from music21 import chord as m21chord
    from music21 import note
    from music21 import stream
    from music21 import tie

    warnings: list[str] = []
    m = stream.Measure()

    if not events:
        m.insert(0, note.Rest(quarterLength=time_sig_ql))
        return m, warnings

    cursor = 0.0

    for ev in events:
        if not isinstance(ev, dict):
            continue
        et = str(ev.get("type", "note")).lower()
        dur_name = str(ev.get("duration", "quarter")).lower()
        base = _MELODY_DURATION_QL.get(dur_name)
        if base is None:
            warnings.append(f"Figura desconocida «{dur_name}», se usa negra.")
            base = 1.0
        try:
            dots = int(ev.get("dots", 0) or 0)
        except (TypeError, ValueError):
            dots = 0
        dots = max(0, min(2, dots))
        ql = _dotted_quarter_length(base, dots)

        if cursor + ql - time_sig_ql > 1e-6:
            overflow = cursor + ql - time_sig_ql
            warnings.append(
                f"Evento recortado ({overflow:.3f} negras de más en el compás)."
            )
            ql = max(0.0, time_sig_ql - cursor)
            if ql <= 0:
                break

        tie_val = ev.get("tie")
        if tie_val is not None and str(tie_val).lower() not in ("start", "stop"):
            tie_val = None
        else:
            tie_val = str(tie_val).lower() if tie_val is not None else None

        if et == "rest":
            r = note.Rest(quarterLength=ql)
            m.insert(float(cursor), r)
        else:
            pitches_raw = ev.get("pitches")
            plist: list[Any] = []
            if isinstance(pitches_raw, list) and pitches_raw:
                for pr in pitches_raw:
                    if isinstance(pr, dict):
                        plist.append(_melody_pitch_from_payload(pr))
            if not plist:
                plist.append(_melody_pitch_from_payload({}))

            if len(plist) == 1:
                n = note.Note(plist[0], quarterLength=ql)
            else:
                n = m21chord.Chord(plist, quarterLength=ql)

            if tie_val == "start":
                n.tie = tie.Tie("start")
            elif tie_val == "stop":
                n.tie = tie.Tie("stop")

            m.insert(float(cursor), n)

        cursor += ql
        if cursor >= time_sig_ql - 1e-9:
            break

    if cursor < time_sig_ql - 1e-6:
        warnings.append(
            f"Compás incompleto: se añade silencio ({time_sig_ql - cursor:.3f} negras)."
        )
        m.insert(float(cursor), note.Rest(quarterLength=time_sig_ql - cursor))

    return m, warnings


def _normalize_measure_melodies(
    raw: Any, num_measures: int
) -> tuple[dict[int, list[dict[str, Any]]], list[str]]:
    """
    Acepta dict { "0": [...], "1": [...] } o lista alineada con compases expandidos.
    """
    warnings: list[str] = []
    out: dict[int, list[dict[str, Any]]] = {}
    if raw is None:
        return out, warnings
    if isinstance(raw, list):
        for i, item in enumerate(raw):
            if i >= num_measures:
                break
            if isinstance(item, list):
                out[i] = item  # type: ignore[assignment]
        return out, warnings
    if isinstance(raw, dict):
        for k, v in raw.items():
            try:
                ki = int(str(k))
            except (TypeError, ValueError):
                continue
            if 0 <= ki < num_measures and isinstance(v, list):
                out[ki] = [x for x in v if isinstance(x, dict)]
    return out, warnings


def _has_any_melody(mm: dict[int, list[dict[str, Any]]]) -> bool:
    for _k, events in mm.items():
        if events:
            return True
    return False


def _compose_build_score_bundle(
    progression: str,
    *,
    max_chords: int = DEFAULT_MAX_CHORDS,
    title: str = "ChordIA sketch",
    key_fifths: int = 0,
    key_mode: str = "major",
    measure_melodies: Any | None = None,
    scale_context: Any | None = None,
) -> dict[str, Any]:
    """
    Construye el stream.Score desde la lead sheet parseada.

    Si hay demasiados acordes, devuelve too_many=True y score=None.
    """
    from music21 import chord, clef, harmony, key, metadata, meter, note, stream

    ls = parse_lead_sheet(progression)
    measures_chords = ls["expanded"]
    tokens = [c for bar in measures_chords for c in bar]
    if len(tokens) > max_chords:
        return {
            "too_many": True,
            "score": None,
            "ls": ls,
            "chords": [],
            "errors": [
                {
                    "index": -1,
                    "token": "",
                    "message": f"Demasiados acordes (máx. {max_chords}).",
                }
            ],
            "enharmonic_conflicts": [],
            "melody_warnings": [],
        }

    errors: list[dict[str, Any]] = []
    valid_bars: list[list[tuple[str, Any]]] = []
    success_list: list[dict[str, Any]] = []
    flat_i = 0
    for bar in measures_chords:
        row: list[tuple[str, Any]] = []
        for tok in bar:
            try:
                fig = american_chord_to_music21_figure(tok)
                cs = harmony.ChordSymbol(fig)
                if not list(cs.pitches):
                    errors.append(
                        {
                            "index": flat_i,
                            "token": tok,
                            "message": "No se pudo interpretar el símbolo (sin alturas).",
                        }
                    )
                else:
                    row.append((tok, cs, flat_i))
                    success_list.append({"index": flat_i, "token": tok, "cs": cs})
            except Exception as e:
                errors.append({"index": flat_i, "token": tok, "message": str(e)})
            flat_i += 1
        valid_bars.append(row)

    enharmonic_conflicts = enharmonic_conflicts_from_parsed(success_list)

    any_valid = any(bool(row) for row in valid_bars)

    harmony_part = stream.Part()
    harmony_part.partName = 'Piano'
    chords_out: list[dict[str, Any]] = []
    melody_warnings: list[str] = []

    def _make_key_sig():
        ks = key.KeySignature(key_fifths)
        ks.mode = key_mode
        return ks

    if not measures_chords or not any_valid:
        num_measures = 1
        m0 = stream.Measure(number=1)
        m0.insert(0, _make_key_sig())
        m0.insert(0, meter.TimeSignature("4/4"))
        m0.insert(0, note.Rest(quarterLength=4.0))
        harmony_part.append(m0)
    else:
        num_measures = len(valid_bars)
        key_obj_analysis = _analysis_key(key_fifths, key_mode)
        for meas_num, parsed_bar in enumerate(valid_bars, start=1):
            m = stream.Measure(number=meas_num)
            if meas_num == 1:
                m.insert(0, _make_key_sig())
                m.insert(0, meter.TimeSignature("4/4"))

            if not parsed_bar:
                m.insert(0, note.Rest(quarterLength=4.0))
                harmony_part.append(m)
                continue

            k = len(parsed_bar)
            ql_each = 4.0 / k
            for j, (tok, cs, chord_flat_i) in enumerate(parsed_bar):
                offset = j * ql_each
                ps = sorted(_voicing_pitches(cs), key=lambda p: p.midi)
                ch = chord.Chord(ps)
                ch.quarterLength = ql_each
                m.insert(float(offset), cs)
                m.insert(float(offset), ch)

                root_p = cs.root()
                root_pc = root_p.pitchClass if root_p is not None else None
                ref_m = _degree_anchor_root_midi(ps, root_pc)
                treat_b9 = _token_implies_flat_ninth(tok)
                _inv_len = chord_inversion_cycle_length(tok)
                if _inv_len < 1:
                    _inv_len = len(ps)
                if _inv_len < 1:
                    _inv_len = 1
                chords_out.append(
                    {
                        "symbol": tok,
                        "flat_index": chord_flat_i,
                        "inversion_cycle_len": _inv_len,
                        "root": root_p.name if root_p is not None else "",
                        "kind": getattr(cs, "chordKind", "") or "",
                        "pitches": [p.nameWithOctave for p in ps],
                        "pitches_american": [pitch_american_with_octave(p) for p in ps],
                        "pitch_midis": [int(p.midi) for p in ps],
                        "root_pc": root_pc,
                        "root_ref_midi": ref_m,
                        "degree_treat_m2_as_b9": treat_b9,
                        "degrees": _degree_labels_for_voicing(
                            ps, root_pc, treat_m2_as_b9=treat_b9
                        ),
                        "measure": meas_num,
                        "beat": 1.0 + offset,
                        "roman_display": _roman_display_for_chord(ch, cs, key_obj_analysis),
                    }
                )

            harmony_part.append(m)

    mm_norm, _mw = _normalize_measure_melodies(measure_melodies, num_measures)
    melody_warnings.extend(_mw)

    score = stream.Score()
    md = metadata.Metadata()
    md.title = title
    score.metadata = md

    use_melody_stave = measure_melodies is not None and _has_any_melody(mm_norm)
    if use_melody_stave:
        melody_part = stream.Part()
        melody_part.partName = 'Melodía'
        for mi in range(int(num_measures)):
            raw_ev = mm_norm.get(mi)
            events_list: list[dict[str, Any]] = list(raw_ev) if raw_ev else []
            m_note, warns = _events_to_melody_measure(events_list, time_sig_ql=4.0)
            melody_warnings.extend(warns)
            m_note.number = mi + 1
            if mi == 0:
                m_note.insert(0, clef.TrebleClef())
                m_note.insert(0, _make_key_sig())
                m_note.insert(0, meter.TimeSignature("4/4"))
            melody_part.append(m_note)
        score.append(melody_part)

    score.append(harmony_part)

    out_bundle: dict[str, Any] = {
        "too_many": False,
        "score": score,
        "ls": ls,
        "chords": chords_out,
        "errors": errors,
        "enharmonic_conflicts": enharmonic_conflicts,
        "melody_warnings": melody_warnings,
        "measure_melodies": {str(k): v for k, v in sorted(mm_norm.items())},
    }
    if scale_context is not None and isinstance(scale_context, dict):
        out_bundle["scale_context"] = scale_context
    return out_bundle


def _sanitize_musicxml_for_osmd_harmonies(musicxml: str) -> tuple[str, list[str]]:
    """
    OpenSheetMusicDisplay suele dibujar **N.C.** cuando el archivo trae ``<kind>none</kind>``
    con un único grado ``add`` en la quinta (music21 exporta así ``C5`` / quintas lead sheet).

    Lo reexpresamos como triada mayor con la 3ª **substraída** (patrón MusicXML habitual)
    y ``text="5"`` para la etiqueta de quinta en visores que lo respetan.

    Si tras el saneo siguen bloques ``<kind>none</kind>``, se añade un aviso genérico.
    """
    import xml.etree.ElementTree as ET

    warns: list[str] = []

    try:
        root_el = ET.fromstring(musicxml)
    except ET.ParseError:
        return musicxml, [
            "No se pudo analizar MusicXML previo saneo OSMD "
            "(el visor podría mostrar cifrados incorrectos)."
        ]

    patched = 0

    def _fingerprints_power_none(h_el: ET.Element) -> bool:
        kind_el = h_el.find("kind")
        if kind_el is None or (kind_el.text or "").strip() != "none":
            return False
        ds = list(h_el.findall("degree"))
        if len(ds) != 1:
            return False
        d0 = ds[0]
        if (d0.findtext("degree-type") or "").strip() != "add":
            return False
        if (d0.findtext("degree-value") or "").strip() != "5":
            return False
        al = (d0.findtext("degree-alter") or "0").strip()
        if al not in ("0", ""):
            return False
        return True

    for h_el in root_el.iter("harmony"):
        if not _fingerprints_power_none(h_el):
            continue

        kind_el = h_el.find("kind")
        if kind_el is None:
            continue
        for d in list(h_el.findall("degree")):
            h_el.remove(d)

        kind_el.attrib.pop("symbol", None)
        kind_el.text = "major"
        kind_el.set("text", "5")

        sub_deg = ET.SubElement(h_el, "degree")
        ET.SubElement(sub_deg, "degree-value").text = "3"
        ET.SubElement(sub_deg, "degree-alter").text = "0"
        ET.SubElement(sub_deg, "degree-type").text = "subtract"

        patched += 1

    start_idx = musicxml.find("<score-partwise")
    prelude = musicxml[:start_idx] if start_idx != -1 else ""
    out = prelude + ET.tostring(root_el, encoding="unicode")

    if patched:
        warns.append(
            "Partitura: se reescribió el cifrado MusicXML de acorde tipo quinta (p. ej. «C5») "
            "porque algunos lectores muestran «N.C.» con la marca técnica anterior."
        )

    if "<kind>none</kind>" in out:
        warns.append(
            "Partitura: queda al menos una armonía con <kind>none</kind> en el MusicXML; "
            "el visor puede mostrar «N.C.» aunque las notas sean coherentes."
        )

    return out, warns


def progression_to_midi_bytes(
    progression: str,
    *,
    max_chords: int = DEFAULT_MAX_CHORDS,
    title: str = "ChordIA sketch",
    key_fifths: int = 0,
    key_mode: str = "major",
    measure_melodies: Any | None = None,
    scale_context: Any | None = None,
) -> tuple[bytes | None, str | None]:
    """Export a lead-sheet progression as MIDI bytes.

    Args:
        progression: Lead-sheet text (bars, American chord symbols).
        max_chords: Maximum flat chord tokens allowed.
        title: Score title metadata.
        key_fifths: Key signature fifths for the score.
        key_mode: ``"major"`` or ``"minor"``.
        measure_melodies: Optional per-measure melody payloads.
        scale_context: Optional symbolic scale context (echoed in MusicXML path).

    Returns:
        ``(midi_bytes, None)`` on success, or ``(None, error_code)`` where
        *error_code* is ``"too_many_or_empty"`` or an exception message string.
    """
    bundle = _compose_build_score_bundle(
        progression,
        max_chords=max_chords,
        title=title,
        key_fifths=key_fifths,
        key_mode=key_mode,
        measure_melodies=measure_melodies,
        scale_context=scale_context,
    )
    if bundle["too_many"] or bundle["score"] is None:
        return None, "too_many_or_empty"
    score = bundle["score"]
    from music21 import harmony as _harmony

    for cs in list(score.recurse().getElementsByClass(_harmony.ChordSymbol)):
        cs.activeSite.remove(cs)
    with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as tmp:
        mid_path = tmp.name
    try:
        score.write("midi", fp=mid_path)
        return pathlib.Path(mid_path).read_bytes(), None
    except Exception as e:
        return None, str(e)
    finally:
        pathlib.Path(mid_path).unlink(missing_ok=True)


def parse_progression_to_musicxml(
    progression: str,
    *,
    max_chords: int = DEFAULT_MAX_CHORDS,
    title: str = "ChordIA sketch",
    key_fifths: int = 0,
    key_mode: str = "major",
    measure_melodies: Any | None = None,
    scale_context: Any | None = None,
) -> dict[str, Any]:
    """Parse a lead-sheet progression and export MusicXML.

    Args:
        progression: Text with ``|`` bar lines and American/jazz chord symbols.
        max_chords: Maximum number of chord tokens allowed.
        title: Score title written into the export.
        key_fifths: Key signature (fifths) for the score.
        key_mode: ``"major"`` or ``"minor"``.
        measure_melodies: Optional melody events per measure index.
        scale_context: Optional dict echoed in the result (does not change key
            in music21); keys such as ``mode_family``, ``jazz_depth``.

    Returns:
        Dict with at least ``musicxml``, ``chords``, ``errors``, ``raw``,
        ``measures``, ``expanded``. May include ``enharmonic_conflicts``,
        ``render_warnings``, ``melody_warnings``, ``measure_melodies``,
        ``scale_context``, ``key_fifths``, ``key_mode``.
    """
    bundle = _compose_build_score_bundle(
        progression,
        max_chords=max_chords,
        title=title,
        key_fifths=key_fifths,
        key_mode=key_mode,
        measure_melodies=measure_melodies,
        scale_context=scale_context,
    )
    ls = bundle["ls"]
    if bundle["too_many"]:
        out_tm: dict[str, Any] = {
            "musicxml": "",
            "chords": [],
            "errors": bundle["errors"],
            "enharmonic_conflicts": [],
            "progression": progression,
            "raw": ls["raw"],
            "measures": ls["measures"],
            "expanded": ls["expanded"],
            "melody_warnings": bundle.get("melody_warnings", []),
            "render_warnings": [],
            "measure_melodies": {},
        }
        if scale_context is not None and isinstance(scale_context, dict):
            out_tm["scale_context"] = scale_context
        return out_tm

    score = bundle["score"]
    assert score is not None

    with tempfile.NamedTemporaryFile(
        suffix=".musicxml", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        tmp_path = tmp.name
    try:
        score.write("musicxml", fp=tmp_path)
        musicxml_raw = pathlib.Path(tmp_path).read_text(encoding="utf-8")
    finally:
        pathlib.Path(tmp_path).unlink(missing_ok=True)

    musicxml, rw = _sanitize_musicxml_for_osmd_harmonies(musicxml_raw)

    return {
        "musicxml": musicxml,
        "chords": bundle["chords"],
        "errors": bundle["errors"],
        "enharmonic_conflicts": bundle["enharmonic_conflicts"],
        "melody_warnings": bundle.get("melody_warnings", []),
        "render_warnings": rw,
        "measure_melodies": bundle.get("measure_melodies", {}),
        "progression": progression,
        "raw": ls["raw"],
        "measures": ls["measures"],
        "expanded": ls["expanded"],
        "key_fifths": key_fifths,
        "key_mode": key_mode,
        **(
            {"scale_context": bundle["scale_context"]}
            if bundle.get("scale_context") is not None
            else {}
        ),
    }


__all__ = [
    "DEFAULT_MAX_CHORDS",
    "american_chord_to_music21_figure",
    "normalize_progression",
    "strip_trailing_chord_dots",
    "split_measures_tokenized",
    "expand_lead_sheet_measures",
    "parse_lead_sheet",
    "measures_from_progression",
    "tokenize_progression",
    "pitch_american_no_octave",
    "pitch_american_with_octave",
    "analyze_chord_inversion_step",
    "advance_chord_inversion",
    "replace_chord_with_next_inversion_detail",
    "replace_chord_with_next_inversion",
    "chord_inversion_cycle_length",
    "build_inversion_tour_plan",
    "total_inversion_tour_steps",
    "enharmonic_conflicts_from_parsed",
    "apply_enharmonic_root_spelling",
    "progression_to_midi_bytes",
    "parse_progression_to_musicxml",
]
