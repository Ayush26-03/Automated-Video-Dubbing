import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any

# Intelligibility-preserving limits for atempo.
# 0.7 is about as slow as the speech stays comprehensible;
# 1.5 is about as fast before intelligibility collapses.
MIN_SPEED = 0.7
MAX_SPEED = 1.5


def align_batch(
    segments_subset: List[Dict[str, Any]],
    output_batch_file: Path,
    target_sample_rate: int = 48000
) -> Path:
    """
    Mix a batch of up to N segments into a temporary WAV file.
    Keeps command-line length safely under Windows limits.
    """
    filter_parts = []
    input_args = []

    for index, segment in enumerate(segments_subset):
        audio_file = Path(segment["audio_file"])
        start = float(segment["start"])
        target_duration = max(0.1, float(segment["end"]) - start)
        tts_duration = float(segment.get("tts_duration", target_duration))

        # Compute a speed multiplier that fits the synthesized clip into the
        # original time window without leaving a silence gap or crushing it.
        # - If TTS is ~equal to the target, play at 1.0 (natural pace).
        # - If TTS is shorter, slow down (down to MIN_SPEED) so it fills the slot.
        # - If TTS is longer, speed up (up to MAX_SPEED) so it doesn't overrun.
        if tts_duration <= 0:
            speed_factor = 1.0
        else:
            ratio = tts_duration / target_duration
            if 0.85 <= ratio <= 1.15:
                # Within ~15% of target duration: leave at natural pace.
                speed_factor = 1.0
            elif ratio < 0.85:
                # TTS is shorter than the original slot: slow it down so it
                # fills the gap (instead of leaving an audible silence before
                # the next segment starts).
                speed_factor = max(MIN_SPEED, ratio)
            else:
                # TTS is longer than the slot: speed it up so it doesn't
                # overrun into the next segment.
                speed_factor = min(MAX_SPEED, ratio)

        # Build FFmpeg atempo chain. atempo natively supports 0.5..2.0,
        # so chain filters if MIN/MAX push us outside that range.
        atempo_filters = []
        rem_speed = speed_factor
        while rem_speed > 2.0:
            atempo_filters.append("atempo=2.0")
            rem_speed /= 2.0
        while rem_speed < 0.5:
            atempo_filters.append("atempo=0.5")
            rem_speed /= 0.5
        atempo_filters.append(f"atempo={rem_speed:.4f}")
        tempo_str = ",".join(atempo_filters)

        # adelay accepts fractional milliseconds; preserve Whisper's precision.
        delay_ms = max(0.0, start) * 1000.0

        filter_expr = (
            f"[{index}:a]{tempo_str},"
            f"aformat=sample_fmts=fltp:sample_rates={target_sample_rate}:channel_layouts=stereo,"
            f"adelay={delay_ms}|{delay_ms}"
            f"[a{index}]"
        )
        filter_parts.append(filter_expr)
        input_args.extend(["-i", str(audio_file.resolve())])

    audio_labels = "".join(f"[a{i}]" for i in range(len(segments_subset)))
    filter_parts.append(
        f"{audio_labels}amix=inputs={len(segments_subset)}:duration=longest:normalize=0[mixed]"
    )

    filter_complex_content = ";".join(filter_parts)

    cmd = [
        "ffmpeg",
        "-y",
        *input_args,
        "-filter_complex", filter_complex_content,
        "-map", "[mixed]",
        "-c:a", "pcm_s16le",
        "-ar", str(target_sample_rate),
        "-ac", "2",
        str(output_batch_file.resolve())
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return output_batch_file


def create_aligned_audio(
    metadata_file: str,
    output_dir: str = "output",
    output_audio: str = "dubbed_audio.wav",
    target_sample_rate: int = 48000,
    batch_size: int = 20
) -> str:
    """
    Combine all synthesized TTS clips into a single timestamp-synchronized audio track.
    Batches inputs to avoid Windows command-line length limits.
    """
    print("\n[5/6] Aligning audio clips with timestamps...")

    meta_path = Path(metadata_file)
    if not meta_path.exists():
        raise FileNotFoundError(f"TTS metadata file not found: {meta_path}")

    with open(meta_path, "r", encoding="utf-8") as f:
        segments = json.load(f)

    if not segments:
        raise ValueError("No TTS segments found to align.")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    final_output_file = output_path / output_audio

    valid_segments = [seg for seg in segments if Path(seg["audio_file"]).exists()]
    if not valid_segments:
        raise ValueError("No valid audio files found among segments.")

    print(f"Mixing {len(valid_segments)} audio clips via chunked FFmpeg alignment...")

    # Always go through the batched path so cleanup is uniform (single try/finally).
    num_batches = (len(valid_segments) + batch_size - 1) // batch_size
    batch_files = []

    try:
        for b_idx in range(num_batches):
            subset = valid_segments[b_idx * batch_size : (b_idx + 1) * batch_size]
            batch_file = output_path / f"temp_align_batch_{b_idx:03d}.wav"
            print(f"  Mixing audio batch {b_idx + 1}/{num_batches} ({len(subset)} clips)...")
            align_batch(subset, batch_file, target_sample_rate)
            batch_files.append(batch_file)

        # Single segment case: skip the merge step — the batch file IS the final.
        if num_batches == 1:
            batch_files[0].replace(final_output_file)
            return str(final_output_file.resolve())

        # Merge all batch files into the master audio track.
        print(f"Finalizing master audio mix from {len(batch_files)} batches...")
        merge_inputs = []
        merge_labels = "".join(f"[{i}:a]" for i in range(len(batch_files)))
        for bf in batch_files:
            merge_inputs.extend(["-i", str(bf.resolve())])

        merge_filter = f"{merge_labels}amix=inputs={len(batch_files)}:duration=longest:normalize=0[mixed]"

        merge_cmd = [
            "ffmpeg",
            "-y",
            *merge_inputs,
            "-filter_complex", merge_filter,
            "-map", "[mixed]",
            "-c:a", "pcm_s16le",
            "-ar", str(target_sample_rate),
            "-ac", "2",
            str(final_output_file.resolve())
        ]
        subprocess.run(merge_cmd, check=True)

        print(f"Aligned dubbed audio created: {final_output_file}")
        return str(final_output_file.resolve())
    finally:
        # Always clean up temp batch files, including on failure.
        for bf in batch_files:
            try:
                if bf.exists():
                    bf.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    meta_in = input("Enter TTS metadata JSON path: ").strip()
    try:
        aligned = create_aligned_audio(meta_in)
        print(f"\nSuccess! Aligned audio: {aligned}")
    except Exception as e:
        print(f"\nAlignment failed: {e}")
