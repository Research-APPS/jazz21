"""Tests for jazz21.manifest harmonic analysis."""

from __future__ import annotations

from jazz21.manifest import (
    analizar_en_tonalidad,
    analizar_progresion,
    detectar_patron_progresion,
)


def _tipo(tonalidad: str, simbolo: str, modo: str = "ionian", **kw) -> dict:
    return analizar_en_tonalidad(tonalidad, simbolo, modo, **kw)


class TestSecondaryDominant:
    def test_v_of_minor_uses_lowercase(self) -> None:
        r = _tipo("C", "A7")
        assert r["funcion"] == "V/ii"
        assert r["tipo_funcion"] == "dominante_secundaria"

    def test_v_of_major_stays_uppercase(self) -> None:
        r = _tipo("C", "D7")
        assert r["funcion"] == "V/V"

    def test_triad_not_secondary_dominant(self) -> None:
        r = _tipo("A", "G", "phrygian")
        assert r["funcion"] is None
        assert r["tipo_funcion"] != "dominante_secundaria"

    def test_maj7_not_secondary_dominant(self) -> None:
        r = _tipo("B", "Fmaj7")
        assert r["funcion"] is None


class TestTritoneSubstitution:
    def test_db7_in_c_static(self) -> None:
        r = _tipo("C", "Db7")
        assert r["funcion"] == "SubV"
        assert r["tipo_funcion"] == "tritone_substitution"

    def test_db7_to_cmaj7_contextual(self) -> None:
        r = _tipo("C", "Db7", siguiente="Cmaj7")
        assert r["funcion"] == "SubV"
        assert r["confianza"] == "alta"


class TestBackdoor:
    def test_bb7_in_c_static(self) -> None:
        r = _tipo("C", "Bb7")
        assert r["funcion"] == "Backdoor"
        assert r["tipo_funcion"] == "backdoor_dominant"

    def test_bb7_to_cmaj7_contextual(self) -> None:
        r = _tipo("C", "Bb7", siguiente="Cmaj7")
        assert r["funcion"] == "Backdoor"
        assert r["confianza"] == "alta"


class TestMelodicMinorTonic:
    def test_amm7_in_aeolian(self) -> None:
        r = _tipo("A", "AmM7", "aeolian")
        assert r["funcion"] == "Tónica"
        assert r["tipo_funcion"] == "tonal"
        assert r["diatonico"] is False


class TestCambioTonal:
    def test_eb7_static_axis(self) -> None:
        r = _tipo("C", "Eb7")
        assert r["tipo_funcion"] == "cambio_tonal"
        assert r["funcion"] is None

    def test_eb7_to_abmaj7_contextual(self) -> None:
        r = _tipo("C", "Eb7", siguiente="Abmaj7")
        assert r["tipo_funcion"] == "cambio_tonal"
        assert r["confianza"] == "alta"


class TestContextualResolution:
    def test_a7_to_dm7(self) -> None:
        r = _tipo("C", "A7", siguiente="Dm7")
        assert r["funcion"] == "V/ii"
        assert r["confianza"] == "alta"

    def test_fsharp7_chromatic_chain(self) -> None:
        r = _tipo("C", "F#7", siguiente="F7")
        assert r["funcion"] is None
        assert r["tipo_funcion"] is None

    def test_fsharp7_not_v_of_vii_in_progression(self) -> None:
        prog = analizar_progresion(
            "C",
            ["Cmaj7", "F#7", "F7", "E7", "Eb7", "D7", "Db7", "Cmaj7"],
        )
        fsharp = prog["acordes"][1]
        assert fsharp["funcion"] is None


class TestColtranePattern:
    def test_detects_coltrane_changes(self) -> None:
        acordes = ["Cmaj7", "Eb7", "Abmaj7", "B7", "Emaj7", "G7", "Cmaj7"]
        assert detectar_patron_progresion("C", acordes) == "coltrane_cycle"

    def test_coltrane_progression_has_patron(self) -> None:
        acordes = ["Cmaj7", "Eb7", "Abmaj7", "B7", "Emaj7", "G7", "Cmaj7"]
        prog = analizar_progresion("C", acordes)
        assert prog["patron"] == "coltrane_cycle"

    def test_ii_v_i_not_coltrane(self) -> None:
        assert detectar_patron_progresion("C", ["Dm7", "G7", "Cmaj7"]) is None


class TestSugerenciasContextuales:
    def test_f_position_includes_fm(self) -> None:
        from jazz21.manifest import sugerencias_contextuales

        acordes = ["C", "E7", "F", "Fm"]
        sugs = sugerencias_contextuales("C", acordes, 2)
        simbolos = {s["simbolo"] for s in sugs}
        assert "Fm" in simbolos
        assert "Am" in simbolos

    def test_progresion_para_ui_shape(self) -> None:
        from jazz21.manifest import progresion_para_ui

        p = progresion_para_ui("C", ["Dm7", "G7", "Cmaj7"], "ionian", "ii-V-I")
        assert p["nombre"] == "ii-V-I"
        assert len(p["acordes"]) == 3
        assert p["acordes"][0]["notas"]
