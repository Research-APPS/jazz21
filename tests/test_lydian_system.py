"""Tests for jazz21.lydian.LydianSystem.

Based on Brett Clement's Lydian System theory (Music Theory Spectrum 36, 2014).
"""

import pytest
from jazz21.lydian import LydianSystem, distance_in_fifths, lydian_for_position, parent_lydian


# ---------------------------------------------------------------------------
# fifth_stack
# ---------------------------------------------------------------------------

class TestFifthStack:
    def test_f_lydian_classic(self):
        # From the paper: F=1 C=2 G=3 D=4 A=5 E=6 B=7
        ls = LydianSystem("F")
        assert ls.fifth_stack() == ["F", "C", "G", "D", "A", "E", "B"]

    def test_c_lydian(self):
        ls = LydianSystem("C")
        assert ls.fifth_stack() == ["C", "G", "D", "A", "E", "B", "F#"]

    def test_stack_has_seven_pitches(self):
        for tonic in ["C", "D", "E", "F", "G", "A", "B", "F#", "Bb", "Eb"]:
            ls = LydianSystem(tonic)
            assert len(ls.fifth_stack()) == 7

    def test_g_lydian(self):
        ls = LydianSystem("G")
        assert ls.fifth_stack() == ["G", "D", "A", "E", "B", "F#", "C#"]

    def test_bb_lydian(self):
        ls = LydianSystem("Bb")
        stack = ls.fifth_stack()
        assert stack[0] == "Bb"
        assert len(stack) == 7


# ---------------------------------------------------------------------------
# stability
# ---------------------------------------------------------------------------

class TestStability:
    def test_tonic_is_most_stable(self):
        ls = LydianSystem("C")
        assert ls.stability("C") == 1.0

    def test_tritone_is_least_stable(self):
        # F# is position 7 in C Lydian (the #4 / Lydian leading tone)
        ls = LydianSystem("C")
        assert ls.stability("F#") == 0.0

    def test_decreasing_order(self):
        ls = LydianSystem("F")
        stack = ls.fifth_stack()
        scores = [ls.stability(n) for n in stack]
        assert scores == sorted(scores, reverse=True)

    def test_note_outside_system_returns_none(self):
        ls = LydianSystem("C")
        # Bb is not in C Lydian
        assert ls.stability("Bb") is None

    def test_enharmonic_equivalence(self):
        ls = LydianSystem("C")
        # F# and Gb are the same pitch class (position 7 in C Lydian)
        assert ls.stability("F#") == ls.stability("Gb")


# ---------------------------------------------------------------------------
# modal_rank
# ---------------------------------------------------------------------------

class TestModalRank:
    def test_returns_five_modes(self):
        ls = LydianSystem("C")
        modes = ls.modal_rank()
        assert len(modes) == 5

    def test_first_mode_is_lydian(self):
        ls = LydianSystem("C")
        modes = ls.modal_rank()
        assert modes[0]["mode"] == "Lydian"
        assert modes[0]["root"] == "C"
        assert modes[0]["roman"] == "I"

    def test_third_mode_is_mixolydian(self):
        # In F Lydian, position 3 is G (Mixolydian)
        ls = LydianSystem("F")
        modes = ls.modal_rank()
        assert modes[2]["mode"] == "Mixolydian"
        assert modes[2]["root"] == "G"
        assert modes[2]["roman"] == "II"

    def test_fourth_mode_is_dorian(self):
        ls = LydianSystem("F")
        modes = ls.modal_rank()
        assert modes[3]["mode"] == "Dorian"
        assert modes[3]["root"] == "D"
        assert modes[3]["roman"] == "vi"

    def test_positions_are_sequential(self):
        ls = LydianSystem("C")
        positions = [m["position"] for m in ls.modal_rank()]
        assert positions == [1, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# characteristic_chords
# ---------------------------------------------------------------------------

class TestCharacteristicChords:
    def test_lydian_has_sus2(self):
        ls = LydianSystem("C")
        chords = ls.characteristic_chords("Lydian")
        types = [c["type"] for c in chords]
        assert "sus2" in types

    def test_mixolydian_has_quartal(self):
        ls = LydianSystem("F")
        chords = ls.characteristic_chords("Mixolydian")
        types = [c["type"] for c in chords]
        assert "quartal" in types

    def test_dorian_has_so_what(self):
        ls = LydianSystem("F")
        chords = ls.characteristic_chords("Dorian")
        types = [c["type"] for c in chords]
        assert "so_what" in types

    def test_unknown_mode_raises(self):
        ls = LydianSystem("C")
        with pytest.raises(ValueError):
            ls.characteristic_chords("Phrygian")

    def test_lydian_sus2_pitches_c(self):
        ls = LydianSystem("C")
        chords = ls.characteristic_chords("Lydian")
        sus2 = next(c for c in chords if c["type"] == "sus2")
        # Csus2 = C D G
        assert set(sus2["pitches"]) == {"C", "D", "G"}


# ---------------------------------------------------------------------------
# pedal_centers
# ---------------------------------------------------------------------------

class TestPedalCenters:
    def test_returns_three_centers(self):
        ls = LydianSystem("C")
        centers = ls.pedal_centers()
        assert len(centers) == 3

    def test_includes_lydian_dorian_mixolydian(self):
        ls = LydianSystem("C")
        modes = {c["mode"] for c in ls.pedal_centers()}
        assert modes == {"Lydian", "Mixolydian", "Dorian"}

    def test_f_lydian_pedal_roots(self):
        ls = LydianSystem("F")
        roots = {c["root"] for c in ls.pedal_centers()}
        # F (Lydian), G (Mixolydian), D (Dorian)
        assert roots == {"F", "G", "D"}


# ---------------------------------------------------------------------------
# mode_for_note
# ---------------------------------------------------------------------------

class TestModeForNote:
    def test_tonic_returns_lydian(self):
        ls = LydianSystem("C")
        result = ls.mode_for_note("C")
        assert result["mode"] == "Lydian"

    def test_leading_tone_returns_none(self):
        # Position 7 in C Lydian is F# — a leading tone, no stable mode
        ls = LydianSystem("C")
        assert ls.mode_for_note("F#") is None

    def test_note_outside_system_returns_none(self):
        ls = LydianSystem("C")
        assert ls.mode_for_note("Bb") is None


# ---------------------------------------------------------------------------
# repr / str
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# regions() — guitar-native view
# ---------------------------------------------------------------------------

class TestRegions:
    def test_returns_seven_regions(self):
        ls = LydianSystem("C")
        assert len(ls.regions()) == 7

    def test_first_region_is_tonic_stable(self):
        ls = LydianSystem("C")
        r = ls.regions()[0]
        assert r["note"] == "C"
        assert r["stability"] == 1.0
        assert r["region"] == "stable"

    def test_last_region_is_leading_tone(self):
        ls = LydianSystem("C")
        r = ls.regions()[-1]
        assert r["stability"] == 0.0
        assert r["region"] == "leading_tone"

    def test_positions_6_7_are_leading_tones(self):
        ls = LydianSystem("F")
        regions = ls.regions()
        for r in regions:
            if r["position"] in (6, 7):
                assert r["region"] == "leading_tone"
            else:
                assert r["region"] == "stable"

    def test_no_mode_names_in_regions(self):
        ls = LydianSystem("C")
        for r in ls.regions():
            assert "mode" not in r
            assert "roman" not in r

    def test_stability_decreasing(self):
        ls = LydianSystem("G")
        stabilities = [r["stability"] for r in ls.regions()]
        assert stabilities == sorted(stabilities, reverse=True)


# ---------------------------------------------------------------------------
# distance_in_fifths
# ---------------------------------------------------------------------------

class TestDistanceInFifths:
    def test_same_note_is_zero(self):
        assert distance_in_fifths("C", "C") == 0

    def test_one_fifth_up(self):
        assert distance_in_fifths("C", "G") == 1

    def test_two_fifths(self):
        assert distance_in_fifths("C", "D") == 2

    def test_tritone_is_six(self):
        # F# is 6 fifths from C
        assert distance_in_fifths("C", "F#") == 6

    def test_enharmonic_equivalence(self):
        assert distance_in_fifths("C", "F#") == distance_in_fifths("C", "Gb")

    def test_f_to_c_is_one(self):
        # C is one fifth above F
        assert distance_in_fifths("F", "C") == 1


# ---------------------------------------------------------------------------
# lydian_for_position
# ---------------------------------------------------------------------------

class TestLydianForPosition:
    def test_d_at_position_4_gives_f(self):
        # F Lydian: F C G D A E B — D is at position 4
        assert lydian_for_position("D", 4) == "F"

    def test_g_at_position_3_gives_f(self):
        # F Lydian: G is at position 3 (Mixolydian centre)
        assert lydian_for_position("G", 3) == "F"

    def test_position_1_returns_same_note(self):
        # Any note at position 1 is its own Lydian tonic
        assert lydian_for_position("C", 1) == "C"
        assert lydian_for_position("G", 1) == "G"

    def test_invalid_position_raises(self):
        with pytest.raises(ValueError):
            lydian_for_position("C", 0)
        with pytest.raises(ValueError):
            lydian_for_position("C", 8)


# ---------------------------------------------------------------------------
# parent_lydian
# ---------------------------------------------------------------------------

class TestParentLydian:
    def test_returns_same_note_normalized(self):
        assert parent_lydian("G") == "G"
        assert parent_lydian("Bb") == "Bb"

    def test_enharmonic_normalization(self):
        # Db and C# are the same pitch class
        assert parent_lydian("C#") == parent_lydian("Db")


class TestRepr:
    def test_repr(self):
        assert repr(LydianSystem("C")) == "LydianSystem('C')"

    def test_str_contains_tonic(self):
        s = str(LydianSystem("F"))
        assert "F(1)" in s
