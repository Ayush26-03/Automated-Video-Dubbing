"""
Configuration and language definitions for Automated Video Dubbing.
Maps ISO language codes to NLLB translation codes and Edge-TTS neural voices.
"""

from typing import Dict, List, Optional, Tuple

# Comprehensive mapping of Whisper ISO codes -> NLLB-200 Language Codes
WHISPER_TO_NLLB: Dict[str, str] = {
    "en": "eng_Latn",
    "es": "spa_Latn",
    "hi": "hin_Deva",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "ja": "jpn_Jpan",
    "zh": "zho_Hans",
    "pt": "por_Latn",
    "it": "ita_Latn",
    "ru": "rus_Cyrl",
    "ko": "kor_Hang",
    "ar": "arb_Arab",
    "bn": "ben_Beng",
    "mr": "mar_Deva",
    "ta": "tam_Taml",
    "te": "tel_Telu",
    "gu": "guj_Gujr",
    "kn": "kan_Knda",
    "ml": "mal_Mlym",
    "ur": "urd_Arab",
    "pa": "pan_Guru",
    "ne": "npi_Deva",
    "tr": "tur_Latn",
    "id": "ind_Latn",
    "pl": "pol_Latn",
    "nl": "nld_Latn",
    "vi": "vie_Latn",
    "th": "tha_Thai",
    "uk": "ukr_Cyrl",
    "cs": "ces_Latn",
    "el": "ell_Grek",
    "ro": "ron_Latn",
    "hu": "hun_Latn",
    "sv": "swe_Latn",
    "da": "dan_Latn",
    "fi": "fin_Latn",
    "he": "heb_Hebr",
    "bg": "bul_Cyrl",
    "sr": "srp_Cyrl",
    "sk": "slk_Latn",
    "sl": "slv_Latn",
    "hr": "hrv_Latn",
    "lt": "lit_Latn",
    "lv": "lvs_Latn",
    "et": "est_Latn",
    "tl": "tgl_Latn",
    "ms": "zsm_Latn",
    "fa": "pes_Arab",
    "af": "afr_Latn",
    "am": "amh_Ethi",
    "as": "asm_Beng",
    "az": "azj_Latn",
    "ba": "bak_Cyrl",
    "be": "bel_Cyrl",
    "bs": "bos_Latn",
    "ca": "cat_Latn",
    "cy": "cym_Latn",
    "eu": "eus_Latn",
    "gl": "glg_Latn",
    "ha": "hau_Latn",
    "hy": "hye_Armn",
    "is": "isl_Latn",
    "jv": "jav_Latn",
    "ka": "kat_Geor",
    "kk": "kaz_Cyrl",
    "km": "khm_Khmr",
    "ky": "kir_Cyrl",
    "la": "lat_Latn",
    "lb": "ltz_Latn",
    "ln": "lin_Latn",
    "lo": "lao_Laoo",
    "mg": "plt_Latn",
    "mi": "mri_Latn",
    "mk": "mkd_Cyrl",
    "mn": "khk_Cyrl",
    "my": "mya_Mymr",
    "nn": "nno_Latn",
    "no": "nob_Latn",
    "oc": "oci_Latn",
    "or": "ory_Orya",
    "ps": "pbt_Arab",
    "sa": "san_Deva",
    "sd": "snd_Arab",
    "si": "sin_Sinh",
    "sn": "sna_Latn",
    "so": "som_Latn",
    "sq": "sqi_Latn",
    "su": "sun_Latn",
    "sw": "swh_Latn",
    "tg": "tgk_Cyrl",
    "tk": "tuk_Latn",
    "tt": "tat_Cyrl",
    "uz": "uzn_Latn",
    "yi": "ydd_Hebr",
    "yo": "yor_Latn",
}

# Catalog for user selection and Edge-TTS voice assignment
LANGUAGE_CATALOG: Dict[str, Dict[str, str]] = {
    "en": {
        "name": "English",
        "nllb": "eng_Latn",
        "voice_female": "en-US-AriaNeural",
        "voice_male": "en-US-GuyNeural",
    },
    "es": {
        "name": "Spanish",
        "nllb": "spa_Latn",
        "voice_female": "es-ES-ElviraNeural",
        "voice_male": "es-ES-AlvaroNeural",
    },
    "hi": {
        "name": "Hindi",
        "nllb": "hin_Deva",
        "voice_female": "hi-IN-SwaraNeural",
        "voice_male": "hi-IN-MadhurNeural",
    },
    "pa": {
        "name": "Punjabi",
        "nllb": "pan_Guru",
        "voice_female": "pa-IN-VaaniNeural",
        "voice_male": "pa-IN-OjasNeural",
    },
    "fr": {
        "name": "French",
        "nllb": "fra_Latn",
        "voice_female": "fr-FR-DeniseNeural",
        "voice_male": "fr-FR-HenriNeural",
    },
    "de": {
        "name": "German",
        "nllb": "deu_Latn",
        "voice_female": "de-DE-KatjaNeural",
        "voice_male": "de-DE-ConradNeural",
    },
    "ja": {
        "name": "Japanese",
        "nllb": "jpn_Jpan",
        "voice_female": "ja-JP-NanamiNeural",
        "voice_male": "ja-JP-KeitaNeural",
    },
    "zh": {
        "name": "Chinese (Simplified)",
        "nllb": "zho_Hans",
        "voice_female": "zh-CN-XiaoxiaoNeural",
        "voice_male": "zh-CN-YunxiNeural",
    },
    "pt": {
        "name": "Portuguese",
        "nllb": "por_Latn",
        "voice_female": "pt-BR-FranciscaNeural",
        "voice_male": "pt-BR-AntonioNeural",
    },
    "it": {
        "name": "Italian",
        "nllb": "ita_Latn",
        "voice_female": "it-IT-ElsaNeural",
        "voice_male": "it-IT-DiegoNeural",
    },
    "ru": {
        "name": "Russian",
        "nllb": "rus_Cyrl",
        "voice_female": "ru-RU-SvetlanaNeural",
        "voice_male": "ru-RU-DmitryNeural",
    },
    "ko": {
        "name": "Korean",
        "nllb": "kor_Hang",
        "voice_female": "ko-KR-SunHiNeural",
        "voice_male": "ko-KR-InJoonNeural",
    },
    "ar": {
        "name": "Arabic",
        "nllb": "arb_Arab",
        "voice_female": "ar-SA-ZariyahNeural",
        "voice_male": "ar-SA-HamedNeural",
    },
    "bn": {
        "name": "Bengali",
        "nllb": "ben_Beng",
        "voice_female": "bn-IN-TanishaaNeural",
        "voice_male": "bn-IN-BashkarNeural",
    },
    "mr": {
        "name": "Marathi",
        "nllb": "mar_Deva",
        "voice_female": "mr-IN-AarohiNeural",
        "voice_male": "mr-IN-ManoharNeural",
    },
    "ta": {
        "name": "Tamil",
        "nllb": "tam_Taml",
        "voice_female": "ta-IN-PallaviNeural",
        "voice_male": "ta-IN-ValluvarNeural",
    },
    "te": {
        "name": "Telugu",
        "nllb": "tel_Telu",
        "voice_female": "te-IN-ShrutiNeural",
        "voice_male": "te-IN-MohanNeural",
    },
    "gu": {
        "name": "Gujarati",
        "nllb": "guj_Gujr",
        "voice_female": "gu-IN-DhwaniNeural",
        "voice_male": "gu-IN-NiranjanNeural",
    },
    "kn": {
        "name": "Kannada",
        "nllb": "kan_Knda",
        "voice_female": "kn-IN-SapnaNeural",
        "voice_male": "kn-IN-GaganNeural",
    },
    "ml": {
        "name": "Malayalam",
        "nllb": "mal_Mlym",
        "voice_female": "ml-IN-SobhanaNeural",
        "voice_male": "ml-IN-MidhunNeural",
    },
    "ur": {
        "name": "Urdu",
        "nllb": "urd_Arab",
        "voice_female": "ur-PK-UzmaNeural",
        "voice_male": "ur-PK-AsadNeural",
    },
    "ne": {
        "name": "Nepali",
        "nllb": "npi_Deva",
        "voice_female": "ne-NP-HemkalaNeural",
        "voice_male": "ne-NP-SagarNeural",
    },
    "tr": {
        "name": "Turkish",
        "nllb": "tur_Latn",
        "voice_female": "tr-TR-EmelNeural",
        "voice_male": "tr-TR-AhmetNeural",
    },
    "id": {
        "name": "Indonesian",
        "nllb": "ind_Latn",
        "voice_female": "id-ID-GadisNeural",
        "voice_male": "id-ID-ArdiNeural",
    },
    "pl": {
        "name": "Polish",
        "nllb": "pol_Latn",
        "voice_female": "pl-PL-AgnieszkaNeural",
        "voice_male": "pl-PL-MarekNeural",
    },
    "nl": {
        "name": "Dutch",
        "nllb": "nld_Latn",
        "voice_female": "nl-NL-ColetteNeural",
        "voice_male": "nl-NL-MaartenNeural",
    },
    "vi": {
        "name": "Vietnamese",
        "nllb": "vie_Latn",
        "voice_female": "vi-VN-HoaiMyNeural",
        "voice_male": "vi-VN-NamMinhNeural",
    },
    "th": {
        "name": "Thai",
        "nllb": "tha_Thai",
        "voice_female": "th-TH-PremwadeeNeural",
        "voice_male": "th-TH-NiwatNeural",
    },
    "uk": {
        "name": "Ukrainian",
        "nllb": "ukr_Cyrl",
        "voice_female": "uk-UA-PolinaNeural",
        "voice_male": "uk-UA-OstapNeural",
    },
    "cs": {
        "name": "Czech",
        "nllb": "ces_Latn",
        "voice_female": "cs-CZ-VlastaNeural",
        "voice_male": "cs-CZ-AntoninNeural",
    },
    "el": {
        "name": "Greek",
        "nllb": "ell_Grek",
        "voice_female": "el-GR-AthinaNeural",
        "voice_male": "el-GR-NestorasNeural",
    },
    "sv": {
        "name": "Swedish",
        "nllb": "swe_Latn",
        "voice_female": "sv-SE-SofieNeural",
        "voice_male": "sv-SE-MattiasNeural",
    },
    "da": {
        "name": "Danish",
        "nllb": "dan_Latn",
        "voice_female": "da-DK-ChristelNeural",
        "voice_male": "da-DK-JeppeNeural",
    },
    "fi": {
        "name": "Finnish",
        "nllb": "fin_Latn",
        "voice_female": "fi-FI-NooraNeural",
        "voice_male": "fi-FI-HarriNeural",
    },
    "he": {
        "name": "Hebrew",
        "nllb": "heb_Hebr",
        "voice_female": "he-IL-HilaNeural",
        "voice_male": "he-IL-AvriNeural",
    },
    "ro": {
        "name": "Romanian",
        "nllb": "ron_Latn",
        "voice_female": "ro-RO-AlinaNeural",
        "voice_male": "ro-RO-EmilNeural",
    },
    "hu": {
        "name": "Hungarian",
        "nllb": "hun_Latn",
        "voice_female": "hu-HU-NoemiNeural",
        "voice_male": "hu-HU-TamasNeural",
    },
    "sw": {
        "name": "Swahili",
        "nllb": "swh_Latn",
        "voice_female": "sw-KE-ZuriNeural",
        "voice_male": "sw-KE-RafikiNeural",
    },
    "tl": {
        "name": "Filipino / Tagalog",
        "nllb": "tgl_Latn",
        "voice_female": "fil-PH-BlessicaNeural",
        "voice_male": "fil-PH-AngeloNeural",
    },
    "ms": {
        "name": "Malay",
        "nllb": "zsm_Latn",
        "voice_female": "ms-MY-YasminNeural",
        "voice_male": "ms-MY-OsmanNeural",
    },
}

DEFAULT_SOURCE_LANG = "auto"
DEFAULT_TARGET_LANG = "en"
DEFAULT_WHISPER_MODEL = "small"
DEFAULT_TRANSLATION_MODEL = "facebook/nllb-200-distilled-600M"


def get_nllb_code(lang_code: str) -> Optional[str]:
    """
    Retrieve NLLB language code from standard Whisper or ISO code.
    Supports 2-letter, 3-letter, or already formatted NLLB codes.
    """
    code = lang_code.lower().strip()
    
    # 1. Check direct lookup in Whisper to NLLB mapping
    if code in WHISPER_TO_NLLB:
        return WHISPER_TO_NLLB[code]
    
    # 2. Check in LANGUAGE_CATALOG
    if code in LANGUAGE_CATALOG:
        return LANGUAGE_CATALOG[code]["nllb"]

    # 3. Check if already in NLLB format (e.g., 'eng_Latn', 'pan_Guru')
    for nllb in WHISPER_TO_NLLB.values():
        if nllb.lower() == code:
            return nllb

    # 4. Check matching prefix (e.g., 'en-US' -> 'en')
    prefix = code.split("-")[0].split("_")[0]
    if prefix in WHISPER_TO_NLLB:
        return WHISPER_TO_NLLB[prefix]

    return None


def get_default_voice(lang_code: str, gender: str = "female") -> str:
    """Retrieve default Edge-TTS voice for given language code."""
    code = lang_code.lower().split("-")[0]
    info = LANGUAGE_CATALOG.get(code)
    if info:
        if gender.lower() == "male":
            return info.get("voice_male", info["voice_female"])
        return info["voice_female"]
    return "en-US-AriaNeural"


def is_supported_language(lang_code: str) -> bool:
    """Check whether a language code can be translated with NLLB."""
    return get_nllb_code(lang_code) is not None
