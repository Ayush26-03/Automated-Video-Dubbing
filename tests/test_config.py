"""Smoke tests for src.config — language code lookups."""

from src.config import (
    LANGUAGE_CATALOG,
    get_default_voice,
    get_nllb_code,
    is_supported_language,
)


def test_nllb_code_lookup_known():
    assert get_nllb_code("en") == "eng_Latn"
    assert get_nllb_code("hi") == "hin_Deva"
    assert get_nllb_code("ja") == "jpn_Jpan"


def test_nllb_code_lookup_normalizes_case_and_prefix():
    assert get_nllb_code("EN") == "eng_Latn"
    assert get_nllb_code("hi-IN") == "hin_Deva"


def test_nllb_code_lookup_passthrough():
    """Codes already in NLLB form should pass through unchanged."""
    assert get_nllb_code("eng_Latn") == "eng_Latn"


def test_nllb_code_lookup_unknown_returns_none():
    assert get_nllb_code("zz") is None
    assert get_nllb_code("notalanguage_xyz") is None


def test_default_voice_returns_canonical():
    female = get_default_voice("es", gender="female")
    male = get_default_voice("es", gender="male")
    assert female == "es-ES-ElviraNeural"
    assert male == "es-ES-AlvaroNeural"


def test_default_voice_female_default():
    # gender defaults to female
    voice = get_default_voice("fr")
    assert voice.endswith("Neural")


def test_is_supported_language():
    assert is_supported_language("en")
    assert is_supported_language("EN")
    assert not is_supported_language("xx")


def test_catalog_consistency():
    """Every language in the catalog must have both female and male voices."""
    for code, info in LANGUAGE_CATALOG.items():
        assert "name" in info
        assert "nllb" in info
        assert "voice_female" in info
        assert "voice_male" in info, f"{code} missing male voice"
        assert info["voice_female"].endswith("Neural"), f"{code} voice_female not Neural"
        assert info["voice_male"].endswith("Neural"), f"{code} voice_male not Neural"
