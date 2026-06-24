"""
Normalizador de cifrado americano para acorde → forma canónica + metadatos.

Acepta variantes habituales (ø,º,maj7,Δ,min,ambigüedades tipo «mb57» como m+b5+7 sin leer «b57» literal)
y devuelve un diccionario con canonical, música MusicXML-ish, intervalos relativos al bajo/fundamental.

No sustituye a jazz21.notation; debe usarse *antes* o para análisis/depuración.
"""

from __future__ import annotations

import re
from typing import Any

# Raíz igual que compose_engine (grupo 3 = sufijo)
_ROOT_RE = re.compile(
    r"^([A-Ga-g])(bb|##|b|\u266d|#|\u266f|x)?(.*)$",
    re.UNICODE,
)


def _interval_label_for_degree(pc_above_root: int, chord_kind_lower: str) -> str:
    """Etiqueta intervalica; en acordes disminuidos de 7ª usa bb7 para el 9 st si aplica."""
    d = pc_above_root % 12
    if "diminished" in chord_kind_lower and d == 9 and "seventh" in chord_kind_lower:
        return "bb7"
    return _pitch_class_interval_label(d)


def _pitch_class_interval_label(pc_above_root: int) -> str:
    """Etiqueta intervalica simple sobre fundamental (altura 12-TET)."""
    # 5 st sobre raíz = 4ª justa («4» en sus/sus4); «11» reservado a tensión alta (17 st ≈ pc 10 en contexto alto).
    m = {
        0: "1",
        1: "b9",
        2: "9",
        3: "b3",
        4: "3",
        5: "4",
        6: "b5",
        7: "5",
        8: "#5",
        9: "13",
        10: "b7",
        11: "7",
    }
    return m.get(pc_above_root % 12, "?")


def _unicode_for_chord(s: str) -> str:
    """Normaliza símbolos típicos (º,°,dim, ♭ ♯ Δ)."""
    r = (
        str(s)
        .replace("\u266d", "b")  # ♭
        .replace("\u266f", "#")  # ♯
    )
    # Disminución: orden masculino ordinal, grado símbolo alternativos → dim
    for ch in ("\u00b0", "\u00ba", "\u25cb", "\u25ef"):
        r = r.replace(ch, "dim")
    # Semidisminuido
    r = r.replace("Ø", "o").replace("ø", "o")
    # Maj7 triángulo / delta
    r = r.replace("△", "maj").replace("Δ", "maj")
    return r


def _collapse_suffix_whitespace(suffix: str) -> str:
    return "".join(suffix.split())


def _normalize_suffix(suffix: str) -> str:
    """
    Convierte el sufijo (sin raíz) a una forma más cercana a lo que music21 acepta bien.
    Orden: reglas largas → cortas; **mb57** → m7b5 (no interpretar b57 como un solo alterador).
    """
    t = _collapse_suffix_whitespace(suffix)
    if not t:
        return t
    t = _unicode_for_chord(t)

    # Jazz: C- = menor, C-7 = m7
    if re.match(r"^-7$", t):
        return "m7"
    if re.match(r"^-$", t):
        return "m"

    # --- Regla clave: mb57 = m + b5 + 7 (semidisminuido 7) ---
    if re.match(r"^mb57$", t, re.IGNORECASE):
        return "m7b5"
    # Variantes con separación eliminada arriba
    if re.match(r"^m(b5|5b)7$", t, re.IGNORECASE):
        return "m7b5"
    if re.match(r"^min7b5$", t, re.IGNORECASE):
        return "m7b5"
    if re.match(r"^m7b5$", t, re.IGNORECASE):
        return "m7b5"

    # ø7 / o7 (tras reemplazo de ø) → half-dim 7
    t = re.sub(r"^o7$", "m7b5", t, flags=re.IGNORECASE)
    t = re.sub(r"^o$", "m7b5", t, flags=re.IGNORECASE)

    # Δ / maj para maj7 (ya parcialmente unicode → maj)
    t = re.sub(r"(?i)maj\s*7\b", "maj7", t)
    t = re.sub(r"(?i)\bmaj7\b", "maj7", t)
    t = re.sub(r"(?i)^M7$", "maj7", t)
    # CM triada mayor explícita: “M” al final típico Maj (C triada)
    if re.match(r"^M$", t):
        return "M"

    # Menor compacto estándar
    t = re.sub(r"(?i)^min7$", "m7", t)
    t = re.sub(r"(?i)^min$", "m", t)

    # Disminución triada vs dim7 — “dim”, “º” ya → dim cadena literal
    t = re.sub(r"(?i)^dim7$", "dim7", t)
    t = re.sub(r"(?i)^dim$", "dim", t)

    # Aumentado
    t = re.sub(r"(?i)^aug$", "aug", t)
    t = re.sub(r"^\+$", "aug", t)

    # Suspended
    if re.match(r"(?i)^(sus2|sus4|sus)$", t):
        tl = t.lower()
        return "sus2" if "2" in tl else "sus4"

    # Dominante 7 solo número
    if re.match(r"^7$", t):
        return "7"

    return t


def _assemble(root_letter: str, acc_char: str, suffix: str) -> str:
    acc = acc_char or ""
    return root_letter.upper() + acc + suffix


def split_slash(symbol: str) -> tuple[str, str | None]:
    """Split a chord symbol into head and slash-bass if present.

    Returns:
        ``(head, bass)`` when ``/`` is present; ``(symbol, None)`` otherwise.
    """
    s = symbol.strip()
    if "/" not in s:
        return s, None
    i = s.index("/")
    head, bass = s[:i].strip(), s[i + 1 :].strip()
    if not head:
        return s, None
    return head, bass or None


def preprocess_chord_symbol(symbol: str) -> str:
    """Return the most canonical chord spelling for a symbol.

    Uses :func:`normalize_chord_symbol` when possible; otherwise returns *symbol*
    stripped. Useful before :func:`american_chord_to_music21_figure`.
    """
    res = normalize_chord_symbol(symbol)
    if res is None:
        return symbol.strip()
    return res["canonical"]


def normalize_chord_symbol(symbol: str) -> dict[str, Any] | None:
    """Normalize one chord token to canonical form and harmonic metadata.

    Args:
        symbol: Single chord token (e.g. ``"Amb57"``, ``"Aø7"``, ``"Cmaj7/E"``).

    Returns:
        Dict with ``input``, ``canonical``, ``musicxml_kind``, ``quality``,
        ``intervals``, ``pitches``, ``chord_kind_m21``. ``None`` if the root
        is not recognized or music21 cannot parse the result.
    """
    raw = symbol.strip()
    if not raw:
        return None

    head, bass_note = split_slash(raw)
    m = _ROOT_RE.match(head)
    if not m:
        return None
    letter = m.group(1).upper()
    acc = m.group(2) or ""
    rest = m.group(3) or ""

    suffix_norm = _normalize_suffix(rest)
    canonical_core = _assemble(letter, acc, suffix_norm)
    if bass_note is not None:
        canonical = canonical_core + "/" + bass_note.strip()
    else:
        canonical = canonical_core

    out: dict[str, Any] = {
        "input": raw,
        "canonical": canonical,
        "musicxml_kind": None,
        "quality": None,  # texto tipo «half-diminished-seventh»
        "intervals": [],
        "pitches": [],
        "chord_kind_m21": None,
    }

    try:
        from music21 import harmony

        from jazz21.notation.compose_engine import american_chord_to_music21_figure

        fig = american_chord_to_music21_figure(canonical)
        cs = harmony.ChordSymbol(fig)
        if not list(cs.pitches):
            return None

        m21_kind = getattr(cs, "chordKind", None) or getattr(cs, "ChordKind", None)
        out["chord_kind_m21"] = m21_kind
        kind_s_for_iv = str(m21_kind or "").lower()

        root_p = cs.root()
        if root_p is None:
            ps = list(cs.pitches)
        else:
            ps = list(cs.pitches)

        out["pitches"] = [p.name for p in ps]

        if root_p is not None:
            rpc = root_p.pitchClass
            uniq_pc = sorted({(p.pitchClass - rpc) % 12 for p in ps})
            seen: list[str] = []
            for d in uniq_pc:
                lab = _interval_label_for_degree(d, kind_s_for_iv)
                seen.append(lab)
            out["intervals"] = seen

        xml_k = _musicxml_kind_from_chord_symbol(cs)
        # music21 suele clasificar ø / m7b5 como «minor-seventh»; MusicXML «half-diminished»
        if re.search(r"(?i)m7b5(\b|$)", canonical.split("/")[0]):
            xml_k = "half-diminished"
        out["musicxml_kind"] = xml_k
        out["quality"] = _quality_human_label(out.get("intervals") or [], xml_k)
    except Exception:
        # Sin music21 o figura inválida: devolvemos lo preprocesado + vacíos
        pass

    return out


def _quality_human_label(intervals: list[str], music_xml_k: str | None) -> str | None:
    """Calidad legible (similar a los ejemplos del spec: half-diminished-seventh, diminished, …)."""
    iv = ",".join(intervals)
    if iv == "1,b3,b5,b7" and music_xml_k == "half-diminished":
        return "half-diminished-seventh"
    if iv == "1,b3,b5,bb7":
        return "diminished-seventh"
    if iv == "1,b3,b5":
        return "diminished"
    if music_xml_k == "major-seventh":
        return "major-seventh"
    if music_xml_k == "minor-seventh":
        return "minor-seventh"
    if music_xml_k == "major":
        return "major-triad"
    if music_xml_k == "minor":
        return "minor-triad"
    if music_xml_k == "dominant":
        return "dominant-seventh"
    if music_xml_k == "augmented":
        return "augmented-triad"
    if music_xml_k == "suspended-fourth":
        return "suspended-fourth"
    return music_xml_k


def _musicxml_kind_from_chord_symbol(cs: Any) -> str | None:
    """
    Aproximación a valores «kind» estilo MusicXML 4 (major, minor, dominant, diminished, half-diminished…).
    """
    k = getattr(cs, "chordKind", None) or getattr(cs, "ChordKind", None)
    if k is None:
        return None
    kl = str(k).lower().replace("_", "-").replace(" ", "-")

    # Preferir cadena larga antes que substring (p. ej. «minor-seventh» antes que «minor»).
    precedence = (
        ("half-diminished-seventh", "half-diminished"),
        ("half-diminished", "half-diminished"),
        ("diminished-seventh", "diminished"),
        ("minor-seventh", "minor-seventh"),
        ("major-seventh", "major-seventh"),
        ("major", "major"),
        ("minor", "minor"),
        ("diminished", "diminished"),
        ("dominant-seventh", "dominant"),
        ("augmented-seventh", "augmented"),
        ("dominant", "dominant"),
        ("augmented", "augmented"),
        ("suspended-fourth", "suspended-fourth"),
    )
    for needle, xm in precedence:
        if needle in kl:
            return xm

    if "half" in kl and "dim" in kl:
        return "half-diminished"
    if kl == "diminished" or "fully-diminished" in kl:
        return "diminished"
    return kl.split("-")[0] if kl else None


__all__ = [
    "normalize_chord_symbol",
    "preprocess_chord_symbol",
    "split_slash",
]
