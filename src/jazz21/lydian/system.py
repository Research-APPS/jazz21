"""Core LydianSystem class.

The Lydian System (LS) organises diatonic modes around a Lydian tonic using
the cycle of perfect fifths as the primary axis of pitch stability.  Modes
built on the five lower positions of the fifth-stack are usable; positions 6
and 7 are unstable "leading tones" that cannot anchor a stable modal area.

Fifth-stack positions (example: F Lydian)
  1=F  2=C  3=G  4=D  5=A  6=E  7=B
  most stable ───────────────► least stable
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Pitch helpers
# ---------------------------------------------------------------------------

# Canonical sharp spelling for each pitch class
_PC_TO_NAME: list[str] = [
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"
]

_NAME_TO_PC: dict[str, int] = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4, "F": 5, "E#": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11, "B#": 0,
}

# Preferred spelling for each tonic (avoids double-sharps/flats in the stack)
_TONIC_SPELLING: dict[int, str] = {
    0: "C", 1: "Db", 2: "D", 3: "Eb", 4: "E", 5: "F",
    6: "F#", 7: "G", 8: "Ab", 9: "A", 10: "Bb", 11: "B",
}

_PERFECT_FIFTH = 7  # semitones


# ---------------------------------------------------------------------------
# Module-level network functions (no tonic required)
# ---------------------------------------------------------------------------

def distance_in_fifths(note_a: str, note_b: str) -> int:
    """Return the clockwise fifth-stack distance from *note_a* to *note_b*.

    Measures ascending perfect fifths around the full chromatic cycle (0–11).
    Lower values = stronger tonal relationship.

    Args:
        note_a: Starting note (e.g. ``"C"``).
        note_b: Target note (e.g. ``"G"``).

    Returns:
        Integer in [0, 11].

    Example::

        distance_in_fifths("C", "G")   # 1
        distance_in_fifths("C", "F#")  # 6  — tritone
        distance_in_fifths("C", "F")   # 11 — one fifth backward
    """
    a_pc = _NAME_TO_PC.get(note_a.strip())
    b_pc = _NAME_TO_PC.get(note_b.strip())
    if a_pc is None:
        raise ValueError(f"Unknown note: {note_a!r}")
    if b_pc is None:
        raise ValueError(f"Unknown note: {note_b!r}")
    # Each step in fifth-stack = 7 semitones. Find how many steps to get from a to b.
    # (b_pc - a_pc) mod 12 in semitones; convert to fifths-steps mod 12.
    semitone_diff = (b_pc - a_pc) % 12
    # Multiply by inverse of 7 mod 12 = 7 (since 7*7=49≡1 mod 12)
    return (semitone_diff * 7) % 12


def parent_lydian(note: str) -> str:
    """Return the Lydian tonic whose fifth-stack contains *note* at position 1.

    In other words: given any note as a potential modal centre, which Lydian
    scale treats it as its tonic?  The answer is always the note itself —
    because any note can be treated as the root of a Lydian scale.

    More usefully: given a note and a desired fifth-stack *position*, return
    the Lydian tonic.  See :func:`lydian_for_position`.

    Args:
        note: Note name.

    Returns:
        Note name of the Lydian tonic (same as *note* — every note is the
        tonic of its own Lydian system).

    Example::

        parent_lydian("G")   # "G"  → G Lydian contains G at position 1
    """
    if note.strip() not in _NAME_TO_PC:
        raise ValueError(f"Unknown note: {note!r}")
    pc = _NAME_TO_PC[note.strip()]
    return _TONIC_SPELLING[pc]


def lydian_for_position(note: str, position: int) -> str:
    """Return the Lydian tonic that places *note* at fifth-stack *position*.

    Useful when you know a note's role in the system (e.g. "D is my Dorian
    centre, position 4") and want to find the parent Lydian tonic.

    Args:
        note: Note name of the regional centre.
        position: Desired fifth-stack position (1–7).

    Returns:
        Note name of the Lydian tonic.

    Example::

        # D is the Dorian centre (position 4) — what is the parent Lydian?
        lydian_for_position("D", 4)   # "F"  → F Lydian: F C G D A E B
        lydian_for_position("G", 3)   # "F"  → F Lydian: position 3 = G (Mixolydian)
    """
    if position < 1 or position > 7:
        raise ValueError(f"Position must be 1–7, got {position}")
    note_pc = _NAME_TO_PC.get(note.strip())
    if note_pc is None:
        raise ValueError(f"Unknown note: {note!r}")
    # Go back (position-1) fifths from note to reach the tonic
    tonic_pc = (note_pc - (position - 1) * _PERFECT_FIFTH) % 12
    return _TONIC_SPELLING[tonic_pc]


def _pc(note: str) -> int:
    """Return pitch class (0–11) for a note name."""
    n = note.strip()
    if n not in _NAME_TO_PC:
        raise ValueError(f"Unknown note name: {note!r}")
    return _NAME_TO_PC[n]


def _name(pc: int, prefer_flat: bool = False) -> str:
    """Return note name for a pitch class."""
    if prefer_flat:
        flat_map = {
            1: "Db", 3: "Eb", 6: "Gb", 8: "Ab", 10: "Bb"
        }
        return flat_map.get(pc % 12, _PC_TO_NAME[pc % 12])
    return _PC_TO_NAME[pc % 12]


# ---------------------------------------------------------------------------
# Mode metadata
# ---------------------------------------------------------------------------

# Keyed by fifth-stack position (1–7)
_MODE_DATA: dict[int, dict] = {
    1: {
        "name": "Lydian",
        "roman": "I",
        "rank": "primary",
        "cyclic_chords": ["sus2"],       # [027] from stack #1-3
        "tertian_chords": ["maj", "maj7", "maj9#11"],
    },
    2: {
        "name": "Ionian",
        "roman": "V",
        "rank": "weak",                  # "horizontal" per Russell; functions as V
        "cyclic_chords": ["sus2", "sus4"],
        "tertian_chords": ["maj", "maj7"],
    },
    3: {
        "name": "Mixolydian",
        "roman": "II",
        "rank": "strong",               # primary tonicizer of Lydian
        "cyclic_chords": ["quartal"],
        "tertian_chords": ["maj", "7"],
    },
    4: {
        "name": "Dorian",
        "roman": "vi",
        "rank": "primary_minor",        # "relative minor" of Lydian
        "cyclic_chords": ["so_what", "quartal", "sus4"],
        "tertian_chords": ["m", "m7"],
    },
    5: {
        "name": "Aeolian",
        "roman": "iii",
        "rank": "weak",
        "cyclic_chords": [],
        "tertian_chords": ["m"],        # triad only; leading tones limit extensions
    },
    6: {
        "name": None,                   # no stable mode available here
        "roman": "vii",
        "rank": "leading_tone",
        "cyclic_chords": [],
        "tertian_chords": [],
    },
    7: {
        "name": None,
        "roman": None,
        "rank": "leading_tone",
        "cyclic_chords": [],
        "tertian_chords": [],
    },
}

# Readable description of each cyclic chord type
_CYCLIC_CHORD_DESC: dict[str, str] = {
    "sus2": "sus2 [027] — root + major 2nd + perfect 5th (no third)",
    "sus4": "sus4 [027] — root + perfect 4th + perfect 5th (no third)",
    "quartal": "quartal [027] — stack of two perfect fourths",
    "so_what": "So What [02479] — quartal tetrachord + major 2nd on top (Bill Evans / Kind of Blue)",
}


# ---------------------------------------------------------------------------
# LydianSystem
# ---------------------------------------------------------------------------

class LydianSystem:
    """A Lydian System centred on *tonic*.

    Args:
        tonic: Note name for the Lydian tonic (e.g. ``"F"``, ``"C"``, ``"Bb"``).

    Example::

        ls = LydianSystem("C")
        ls.fifth_stack()
        # ['C', 'G', 'D', 'A', 'E', 'B', 'F#']

        ls.stability("F#")
        # 0.0   (least stable — the tritone / Lydian #4)

        ls.stability("C")
        # 1.0   (tonic)
    """

    def __init__(self, tonic: str) -> None:
        tonic = tonic.strip()
        if tonic not in _NAME_TO_PC:
            raise ValueError(f"Unknown tonic: {tonic!r}")
        self._tonic = tonic
        self._tonic_pc = _pc(tonic)
        self._stack = self._build_stack()
        self._pc_to_pos: dict[int, int] = {
            _pc(n): pos for pos, n in enumerate(self._stack, start=1)
        }

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def fifth_stack(self) -> list[str]:
        """Return the 7 pitches of the Lydian scale ordered as ascending perfect fifths.

        Position 1 is the tonic (most stable); position 7 is the tritone /
        Lydian #4 (least stable, functions as a leading tone).

        Returns:
            List of 7 note names, e.g. ``['C', 'G', 'D', 'A', 'E', 'B', 'F#']``.
        """
        return list(self._stack)

    def stability(self, note: str) -> float:
        """Return the pitch-stability score for *note* within this Lydian System.

        Stability decreases linearly with fifth-stack position:
        position 1 → 1.0, position 7 → 0.0.

        Args:
            note: Note name (e.g. ``"G"``, ``"Bb"``).

        Returns:
            Float in [0.0, 1.0].  Notes outside the system return ``None``.
        """
        pos = self._pc_to_pos.get(_pc(note))
        if pos is None:
            return None
        return round(1.0 - (pos - 1) / 6, 4)

    def modal_rank(self) -> list[dict]:
        """Return the 5 usable modes ordered by fifth-stack position.

        Each entry contains:
        - ``position``: int 1–5 (fifth-stack position of the mode's root)
        - ``mode``: mode name (e.g. ``"Lydian"``, ``"Dorian"``)
        - ``root``: note name of the mode's root in this system
        - ``roman``: Roman numeral role within the Lydian scale
        - ``rank``: ``"primary"``, ``"strong"``, ``"weak"``, or ``"primary_minor"``
        - ``cyclic_chords``: characteristic cyclic chord types
        - ``tertian_chords``: available tertian extensions

        Returns:
            List of 5 dicts (positions 1–5 only; positions 6–7 are excluded as
            they function only as leading tones).
        """
        result = []
        for pos in range(1, 6):
            data = _MODE_DATA[pos]
            result.append({
                "position": pos,
                "mode": data["name"],
                "root": self._stack[pos - 1],
                "roman": data["roman"],
                "rank": data["rank"],
                "cyclic_chords": list(data["cyclic_chords"]),
                "tertian_chords": list(data["tertian_chords"]),
            })
        return result

    def characteristic_chords(self, mode: str) -> list[dict]:
        """Return the characteristic cyclic chords for the named mode.

        Cyclic chords are [027] or [02479] sonorities built from adjacent
        segments of the Lydian fifth-stack.  They avoid the Lydian leading tones
        (positions 6–7) and maintain tonal ambiguity by omitting thirds.

        Args:
            mode: Mode name — one of ``"Lydian"``, ``"Ionian"``,
                  ``"Mixolydian"``, ``"Dorian"``, ``"Aeolian"``.

        Returns:
            List of dicts, each with ``type``, ``pitches``, and ``description``.

        Raises:
            ValueError: if *mode* is not part of this Lydian System.
        """
        pos = self._mode_position(mode)
        data = _MODE_DATA[pos]
        root_pc = _pc(self._stack[pos - 1])

        chords = []
        for chord_type in data["cyclic_chords"]:
            pitches = self._cyclic_chord_pitches(root_pc, chord_type, pos)
            chords.append({
                "type": chord_type,
                "pitches": pitches,
                "description": _CYCLIC_CHORD_DESC.get(chord_type, chord_type),
            })
        return chords

    def pedal_centers(self) -> list[dict]:
        """Return the three primary pedal substitution centers.

        Lydian, Mixolydian, and Dorian share the closest modal relationship
        within the LS and are freely interchangeable via pedal substitution —
        the technique Zappa exploits throughout *Joe's Garage* and elsewhere.

        Returns:
            List of 3 dicts with ``mode``, ``root``, and ``roman``.
        """
        primary_positions = [1, 3, 4]  # Lydian, Mixolydian, Dorian
        return [
            {
                "mode": _MODE_DATA[p]["name"],
                "root": self._stack[p - 1],
                "roman": _MODE_DATA[p]["roman"],
            }
            for p in primary_positions
        ]

    def regions(self) -> list[dict]:
        """Return the fifth-stack as navigable regions — no mode names, just notes and gravity.

        This is the guitar-native view of the Lydian System: the tonic is the
        gravitational centre; every other note is described by how far it sits
        from that centre along the cycle of fifths.

        Each region is either ``"stable"`` (positions 1–5, usable as a pedal
        centre), ``"leading_tone"`` (positions 6–7, pull back toward stable
        notes), or ``"outside"`` (not in this system).

        Returns:
            List of 7 dicts ordered by descending stability::

                [
                    {"note": "C", "position": 1, "stability": 1.0,  "region": "stable"},
                    {"note": "G", "position": 2, "stability": 0.833, "region": "stable"},
                    ...
                    {"note": "F#", "position": 7, "stability": 0.0, "region": "leading_tone"},
                ]
        """
        result = []
        for pos, note in enumerate(self._stack, start=1):
            stability = round(1.0 - (pos - 1) / 6, 4)
            region = "stable" if pos <= 5 else "leading_tone"
            result.append({
                "note": note,
                "position": pos,
                "stability": stability,
                "region": region,
            })
        return result

    def mode_for_note(self, note: str) -> dict | None:
        """Return the modal context for *note* as a pedal/tonal centre.

        Args:
            note: Note name.

        Returns:
            Mode dict (same shape as :meth:`modal_rank` entries) or ``None``
            if the note is a leading tone (positions 6–7) or outside the system.
        """
        pos = self._pc_to_pos.get(_pc(note))
        if pos is None or pos > 5:
            return None
        data = _MODE_DATA[pos]
        return {
            "position": pos,
            "mode": data["name"],
            "root": self._stack[pos - 1],
            "roman": data["roman"],
            "rank": data["rank"],
            "cyclic_chords": list(data["cyclic_chords"]),
            "tertian_chords": list(data["tertian_chords"]),
        }

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"LydianSystem('{self._tonic}')"

    def __str__(self) -> str:
        stack = " → ".join(f"{n}({i})" for i, n in enumerate(self._stack, 1))
        return f"LydianSystem '{self._tonic}': {stack}"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Fifth-network helpers (also available as module-level functions)
    # ------------------------------------------------------------------

    def distance_in_fifths(self, note_a: str, note_b: str) -> int:
        """Return the clockwise fifth-stack distance from *note_a* to *note_b*.

        Measures how many ascending perfect fifths separate two notes around
        the cycle (0–11).  Smaller values = closer relationship = stronger
        tonal affinity.

        Args:
            note_a: Starting note.
            note_b: Target note.

        Returns:
            Integer in [0, 11].

        Example::

            ls = LydianSystem("C")
            ls.distance_in_fifths("C", "G")   # 1  — one fifth
            ls.distance_in_fifths("C", "F#")  # 6  — tritone / least stable
        """
        return distance_in_fifths(note_a, note_b)

    def _build_stack(self) -> list[str]:
        """Build the seven-note fifth-stack with sensible enharmonic spellings."""
        prefer_flat = self._tonic_pc in {1, 3, 8, 10}  # Db Eb Ab Bb tonics
        stack = []
        pc = self._tonic_pc
        for _ in range(7):
            stack.append(_name(pc, prefer_flat=prefer_flat))
            pc = (pc + _PERFECT_FIFTH) % 12
        return stack

    def _mode_position(self, mode: str) -> int:
        """Return the fifth-stack position for a mode name."""
        mode_lower = mode.strip().lower()
        for pos, data in _MODE_DATA.items():
            if data["name"] and data["name"].lower() == mode_lower:
                if _pc(self._stack[pos - 1]) in self._pc_to_pos:
                    return pos
        raise ValueError(
            f"Mode {mode!r} is not available in LydianSystem('{self._tonic}'). "
            f"Available modes: {[d['name'] for d in _MODE_DATA.values() if d['name']]}"
        )

    def _cyclic_chord_pitches(
        self, root_pc: int, chord_type: str, stack_pos: int
    ) -> list[str]:
        """Return the pitches of a cyclic chord from the Lydian fifth-stack."""
        prefer_flat = self._tonic_pc in {1, 3, 8, 10}

        if chord_type == "sus2":
            # [027]: root + M2 + P5 (pitches at stack positions p, p+1, p+2)
            return [
                _name(root_pc, prefer_flat),
                _name((root_pc + 2) % 12, prefer_flat),
                _name((root_pc + 7) % 12, prefer_flat),
            ]

        if chord_type == "sus4":
            # [027]: root + P4 + P5 (voiced as stack of fourths from position p+2)
            return [
                _name(root_pc, prefer_flat),
                _name((root_pc + 5) % 12, prefer_flat),
                _name((root_pc + 7) % 12, prefer_flat),
            ]

        if chord_type == "quartal":
            # [027]: voiced as two stacked perfect fourths (A-D-G style)
            # Built from the root going down by a fourth, then up by a fourth
            p4 = 5  # perfect fourth = 5 semitones
            return [
                _name((root_pc - p4) % 12, prefer_flat),  # a fourth below root
                _name(root_pc, prefer_flat),
                _name((root_pc + p4) % 12, prefer_flat),
            ]

        if chord_type == "so_what":
            # [02479]: pentatonic set = pitches at stack positions p through p+4
            # (Bill Evans / Kind of Blue "So What" voicing concept)
            positions = [stack_pos - 1 + i for i in range(5)]
            return [
                _name(_pc(self._stack[p % 7]), prefer_flat)
                for p in positions
                if p < 7
            ]

        return []
