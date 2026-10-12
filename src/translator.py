import json
import re
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

try:
    import torch
except ImportError:
    torch = None

try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
except ImportError:
    AutoTokenizer, AutoModelForSeq2SeqLM = None, None
from src.config import get_nllb_code, DEFAULT_TRANSLATION_MODEL, LANGUAGE_CATALOG


# --- Translator cache -----------------------------------------------------
# NLLB-200 loads cost ~1–2 GB of RAM and ~20–60 seconds. We memoise per
# (src_nllb, tgt_nllb, model_name) so back-to-back jobs reuse the model
# rather than reload it every time.
_TRANSLATOR_CACHE: Dict[Tuple[str, str, str], "NLLBTranslator"] = {}
_TRANSLATOR_LOCK = threading.Lock()


def _get_translator(source_language: str, target_language: str, model_name: str) -> "NLLBTranslator":
    key = (source_language.lower(), target_language.lower(), model_name)
    with _TRANSLATOR_LOCK:
        if key not in _TRANSLATOR_CACHE:
            _TRANSLATOR_CACHE[key] = NLLBTranslator(
                source_language=source_language,
                target_language=target_language,
                model_name=model_name,
            )
        return _TRANSLATOR_CACHE[key]


def clear_translator_cache() -> None:
    """Drop cached translators (useful for tests / memory pressure)."""
    with _TRANSLATOR_LOCK:
        _TRANSLATOR_CACHE.clear()


def truncate_ngram_loops(text: str) -> str:
    """
    Post-generation deduplication guard to truncate text if any 3-word phrase repeats consecutively,
    or if any repetitive n-gram loop is detected.
    """
    if not text:
        return text
    words = text.split()
    if len(words) < 2:
        return text

    # Guard 1: Truncate text if any 3-word phrase repeats consecutively
    for i in range(len(words) - 5):
        phrase = words[i:i + 3]
        if words[i + 3:i + 6] == phrase:
            return " ".join(words[:i + 3])

    # Guard 2: Truncate if any 1-word or 2-word loop repeats consecutively more than 2 times
    for n in (1, 2):
        for i in range(len(words) - 2 * n):
            ngram = words[i:i + n]
            repeats = 1
            while (i + (repeats + 1) * n <= len(words) and 
                   words[i + repeats * n:i + (repeats + 1) * n] == ngram):
                repeats += 1
                if repeats > 2:
                    return " ".join(words[:i + n])

    return text


class NLLBTranslator:
    def __init__(
        self,
        source_language: str,
        target_language: str = "en",
        model_name: str = DEFAULT_TRANSLATION_MODEL
    ):
        self.src_nllb = get_nllb_code(source_language)
        self.tgt_nllb = get_nllb_code(target_language)

        if not self.src_nllb:
            raise ValueError(
                f"Unsupported source language: '{source_language}'. "
                f"Supported codes: {', '.join(LANGUAGE_CATALOG.keys())}"
            )
        if not self.tgt_nllb:
            raise ValueError(
                f"Unsupported target language: '{target_language}'. "
                f"Supported codes: {', '.join(LANGUAGE_CATALOG.keys())}"
            )

        self.source_language = source_language
        self.target_language = target_language
        self.model_name = model_name

        if AutoTokenizer is None or AutoModelForSeq2SeqLM is None or torch is None:
            raise RuntimeError(
                "transformers and torch are required for translation. "
                "Please install them with: pip install transformers torch"
            )

        self.device = torch.device("cuda" if (torch is not None and torch.cuda.is_available()) else "cpu")

        print(f"\n[3/6] Loading translation model: {self.model_name}")
        print(f"Source language : {source_language} ({self.src_nllb})")
        print(f"Target language : {target_language} ({self.tgt_nllb})")
        print(f"Compute device  : {self.device}")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            src_lang=self.src_nllb,
            tgt_lang=self.tgt_nllb
        )

        self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()

        print("Translation model ready.")

    def translate_texts(self, texts: List[str], batch_size: int = 8) -> List[str]:
        if not texts:
            return []

        # Input cleaning: strip repeated consecutive words
        cleaned_inputs = [
            re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', text) for text in texts
        ]

        translated_texts = []
        target_token_id = self.tokenizer.convert_tokens_to_ids(self.tgt_nllb)

        for start in range(0, len(cleaned_inputs), batch_size):
            batch = cleaned_inputs[start:start + batch_size]
            print(f"Translating segments {start + 1}-{start + len(batch)} of {len(cleaned_inputs)}...")

            inputs = self.tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )

            inputs = {key: value.to(self.device) for key, value in inputs.items()}

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    forced_bos_token_id=target_token_id,
                    max_length=256,
                    num_beams=4,
                    repetition_penalty=1.2,
                    no_repeat_ngram_size=3,
                    early_stopping=True
                )

            translations = self.tokenizer.batch_decode(
                outputs,
                skip_special_tokens=True
            )

            for t in translations:
                cleaned_output = truncate_ngram_loops(t.strip())
                translated_texts.append(cleaned_output)

        return translated_texts


def translate_segments(
    segments: List[Dict[str, Any]],
    source_language: str,
    target_language: str = "en",
    model_name: str = DEFAULT_TRANSLATION_MODEL
) -> List[Dict[str, Any]]:
    """
    Translate timestamped segments from source_language to target_language.
    """
    print(f"\n[3/6] Translating {len(segments)} segments to target language '{target_language}'...")

    # If source and target are the same language, skip translation
    src_clean = source_language.lower().split("-")[0]
    tgt_clean = target_language.lower().split("-")[0]

    if src_clean == tgt_clean:
        print(f"Source and target languages are both '{src_clean}'. Skipping translation.")
        return [
            {
                "start": float(seg["start"]),
                "end": float(seg["end"]),
                "original_text": seg.get("text", "").strip(),
                "translated_text": seg.get("text", "").strip()
            }
            for seg in segments
            if seg.get("text", "").strip()
        ]

    translator = _get_translator(
        source_language=source_language,
        target_language=target_language,
        model_name=model_name
    )

    valid_segments = [seg for seg in segments if seg.get("text", "").strip()]
    original_texts = [seg.get("text", "").strip() for seg in valid_segments]

    translated_texts = translator.translate_texts(original_texts)

    translated_segments = []
    for seg, trans_text in zip(valid_segments, translated_texts):
        translated_segment = {
            "start": float(seg["start"]),
            "end": float(seg["end"]),
            "original_text": seg.get("text", "").strip(),
            "translated_text": trans_text
        }
        translated_segments.append(translated_segment)

    print(f"\nTranslation finished: {len(translated_segments)} segments translated.")
    return translated_segments


def save_translated_segments(
    segments: List[Dict[str, Any]],
    output_dir: str = "translations"
) -> str:
    """Save translated segments to JSON."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    output_file = output_path / "translated_segments.json"

    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(segments, file, ensure_ascii=False, indent=2)

    print(f"Translated segments saved to: {output_file}")
    return str(output_file)


if __name__ == "__main__":
    print("NLLB Multi-Language Translation")
    transcript_file = input("Enter transcript JSON path: ").strip()
    target_lang = input("Enter target language code (e.g., en, es, hi, fr, de, ja): ").strip() or "en"

    try:
        with open(transcript_file, "r", encoding="utf-8") as file:
            transcript = json.load(file)

        source_lang = transcript.get("language", "en")
        segments = transcript.get("segments", [])

        translated_segments = translate_segments(segments, source_lang, target_lang)
        save_translated_segments(translated_segments)
        print("\nTranslation stage completed successfully.")
    except Exception as e:
        print(f"\nTranslation failed: {e}")