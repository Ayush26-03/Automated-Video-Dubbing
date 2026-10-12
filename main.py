import argparse
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.config import (
    LANGUAGE_CATALOG,
    DEFAULT_TARGET_LANG,
    DEFAULT_WHISPER_MODEL,
    is_supported_language,
)
from src.pipeline import run_pipeline


def format_time(seconds: float) -> str:
    """Convert seconds into a readable time format."""
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    return f"{minutes}m {seconds}s"


def print_banner():
    print("\n" + "=" * 65)
    print("      🎙️  AI-POWERED AUTOMATED VIDEO DUBBING PIPELINE  🎥")
    print("=" * 65)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Automated Video Dubbing System: Translate and dub videos into any language."
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        help="Path to a local video file (e.g., input.mp4) or YouTube URL."
    )
    parser.add_argument(
        "-u", "--url",
        type=str,
        help="YouTube or online video URL (alias for --input)."
    )
    parser.add_argument(
        "-t", "--target-lang",
        type=str,
        default=None,
        help=f"Target language code (e.g. en, es, hi, fr, de, ja, zh, etc.). Default: {DEFAULT_TARGET_LANG}"
    )
    parser.add_argument(
        "-m", "--model",
        type=str,
        default=DEFAULT_WHISPER_MODEL,
        choices=["tiny", "base", "small", "medium", "large"],
        help=f"Whisper transcription model size. Default: {DEFAULT_WHISPER_MODEL}"
    )
    parser.add_argument(
        "-v", "--voice",
        type=str,
        default=None,
        help="Custom Edge-TTS voice name (e.g., en-US-AriaNeural, es-ES-ElviraNeural)."
    )
    parser.add_argument(
        "-g", "--gender",
        type=str,
        default="female",
        choices=["female", "male"],
        help="TTS voice gender preference (female/male). Default: female"
    )
    parser.add_argument(
        "--embed-subtitles",
        action="store_true",
        help="Embed soft subtitles into the final dubbed video."
    )
    return parser.parse_args()


def interactive_prompt() -> dict:
    print_banner()
    print("Enter a YouTube URL or a local video file path (e.g. video.mp4):")
    source_input = input("👉 Source input: ").strip()

    if not source_input:
        print("Error: Input source cannot be empty.")
        sys.exit(1)

    print("\nAvailable Popular Target Languages:")
    popular_langs = ["en", "es", "hi", "fr", "de", "ja", "zh", "pt", "it", "ru", "ar"]
    for idx, code in enumerate(popular_langs, start=1):
        name = LANGUAGE_CATALOG[code]["name"]
        print(f"  [{idx:2d}] {code:<4} - {name}")

    user_lang = input(f"\nEnter target language code or number (Default: {DEFAULT_TARGET_LANG}): ").strip()
    if not user_lang:
        target_lang = DEFAULT_TARGET_LANG
    elif user_lang.isdigit() and 1 <= int(user_lang) <= len(popular_langs):
        target_lang = popular_langs[int(user_lang) - 1]
    else:
        target_lang = user_lang.lower()
        if not is_supported_language(target_lang):
            print(
                f"Warning: '{target_lang}' is not in the predefined catalog. "
                "Translation will fall back to English TTS if no voice is available."
            )

    print("\nVoice Gender Preference:")
    print("  [1] Female (Default)")
    print("  [2] Male")
    gender_choice = input("👉 Choose gender [1/2]: ").strip()
    gender = "male" if gender_choice == "2" else "female"

    print(f"\nWhisper Model Size [tiny / base / small / medium / large] (Default: {DEFAULT_WHISPER_MODEL}):")
    model_choice = input("👉 Model: ").strip()
    model = model_choice if model_choice in ["tiny", "base", "small", "medium", "large"] else DEFAULT_WHISPER_MODEL

    return {
        "source_input": source_input,
        "target_lang": target_lang,
        "gender": gender,
        "model": model,
        "voice": None,
        "embed_subtitles": False,
    }


def main():
    args = parse_arguments()

    if args.input or args.url:
        source_input = args.input or args.url
        target_lang = args.target_lang or DEFAULT_TARGET_LANG
        gender = args.gender
        model = args.model
        voice = args.voice
        embed_subs = args.embed_subtitles
        print_banner()
    else:
        params = interactive_prompt()
        source_input = params["source_input"]
        target_lang = params["target_lang"]
        gender = params["gender"]
        model = params["model"]
        voice = params["voice"]
        embed_subs = params["embed_subtitles"]

    print(f"\n[RUN SESSION] Target Language: {target_lang}")
    print(f"[RUN SESSION] Whisper Model:   {model}")
    print(f"[RUN SESSION] Voice Gender:   {gender}")

    total_start = time.perf_counter()
    try:
        result = run_pipeline(
            source_input=source_input,
            target_lang=target_lang,
            gender=gender,
            model_name=model,
            voice=voice,
            embed_subs=embed_subs,
        )
    except KeyboardInterrupt:
        print("\n\nDubbing process interrupted by user.")
        return
    except Exception as e:
        print("\n" + "=" * 65)
        print("❌ ERROR OCCURRED")
        print("=" * 65)
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return

    if result.get("cancelled"):
        print("\nDubbing was cancelled before completion.")
        return

    total_time = time.perf_counter() - total_start

    print("\n" + "=" * 65)
    print("                  🎉 DUBBING COMPLETE! 🎉")
    print("=" * 65)
    print(f"Run Session ID    : {result['run_id']}")
    print(f"Source Language   : {result['source_language']}")
    print(f"Target Language   : {target_lang}")
    print(f"Total Segments    : {result['segments_count']}")
    print("-" * 65)
    print(f"📁 Downloaded Video: {result['video_path']}")
    print(f"📁 Raw Transcript  : {result['transcript_path']}")
    print(f"📁 Translation JSON: {result['translated_path']}")
    print(f"📁 Dubbed Subtitles: {result['translated_srt_path']}")
    print(f"📁 Dubbed Audio    : {result['dubbed_audio_path']}")
    print(f"🎬 FINAL VIDEO     : {result['final_video_path']}")
    print("-" * 65)
    print(f"  ⭐ TOTAL TIME     : {format_time(total_time)}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
