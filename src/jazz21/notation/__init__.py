"""
Lead-sheet parsing and American/jazz chord notation → music21.

Public API is defined in :mod:`jazz21.notation.compose_engine`.
"""

from jazz21.notation.compose_engine import (
    DEFAULT_MAX_CHORDS,
    advance_chord_inversion,
    american_chord_to_music21_figure,
    analyze_chord_inversion_step,
    apply_enharmonic_root_spelling,
    build_inversion_tour_plan,
    chord_inversion_cycle_length,
    enharmonic_conflicts_from_parsed,
    expand_lead_sheet_measures,
    measures_from_progression,
    normalize_progression,
    parse_lead_sheet,
    parse_progression_to_musicxml,
    pitch_american_no_octave,
    pitch_american_with_octave,
    progression_to_midi_bytes,
    replace_chord_with_next_inversion,
    replace_chord_with_next_inversion_detail,
    split_measures_tokenized,
    strip_trailing_chord_dots,
    tokenize_progression,
    total_inversion_tour_steps,
)

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
