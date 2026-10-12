import subprocess
from pathlib import Path
from typing import Optional


def create_final_video(
    video_path: str,
    dubbed_audio_path: str,
    output_path: str = "output/final_dubbed_video.mp4",
    subtitle_path: Optional[str] = None,
    run_dir: Optional[Path] = None,
) -> str:
    """Replace original video audio with the dubbed audio track.

    Optionally embed soft subtitles. `run_dir`, when provided, restricts the
    subtitle path to that directory so an HTTP-supplied path can't be used
    to embed an arbitrary file into the output.
    """
    print("\n[6/6] Creating final dubbed video...")

    video = Path(video_path)
    audio = Path(dubbed_audio_path)
    output = Path(output_path)

    output.parent.mkdir(parents=True, exist_ok=True)

    if not video.exists():
        raise FileNotFoundError(f"Original video not found: {video}")
    if not audio.exists():
        raise FileNotFoundError(f"Dubbed audio not found: {audio}")

    # If caller provides a run_dir, restrict the subtitle path to it.
    safe_subtitle: Optional[Path] = None
    if subtitle_path:
        subtitle_path_obj = Path(subtitle_path)
        if not subtitle_path_obj.exists():
            print(f"Warning: subtitle file does not exist, skipping: {subtitle_path}")
        elif run_dir is not None:
            try:
                subtitle_path_obj.resolve().relative_to(run_dir.resolve())
                safe_subtitle = subtitle_path_obj
            except ValueError:
                raise ValueError(
                    f"Subtitle path is outside the run directory: {subtitle_path_obj}. "
                    f"Allowed root: {run_dir}"
                )
        else:
            safe_subtitle = subtitle_path_obj

    command = [
        "ffmpeg",
        "-y",
        "-i", str(video.resolve()),
        "-i", str(audio.resolve()),
    ]

    if safe_subtitle is not None:
        command.extend(["-i", str(safe_subtitle.resolve())])
        command.extend([
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-map", "2:s:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-c:s", "mov_text" if output.suffix.lower() == ".mp4" else "srt",
            "-shortest",
            str(output.resolve())
        ])
    else:
        command.extend([
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output.resolve())
        ])

    print(f"Multiplexing audio into video:\nVideo: {video.name}\nAudio: {audio.name}\nOutput: {output}")

    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise FileNotFoundError(
            "ffmpeg executable not found. Install ffmpeg and ensure it's on your PATH."
        ) from e

    if result.returncode != 0:
        # Last 800 chars of stderr — usually points to the real codec/format issue.
        stderr_tail = (result.stderr or "")[-800:]
        raise RuntimeError(
            f"ffmpeg failed (exit {result.returncode}) while muxing the final video. "
            f"Stderr tail:\n{stderr_tail}"
        )

    if not output.exists():
        raise RuntimeError(f"ffmpeg reported success but {output} was not created.")

    print(f"\nFinal dubbed video successfully created:\n{output.resolve()}")
    return str(output.resolve())


if __name__ == "__main__":
    v_in = input("Enter original video path: ").strip()
    a_in = input("Enter dubbed audio path: ").strip()
    s_in = input("Enter subtitle path (optional, press Enter to skip): ").strip() or None

    try:
        res = create_final_video(v_in, a_in, subtitle_path=s_in)
        print(f"\nCompleted: {res}")
    except Exception as e:
        print(f"\nFailed: {e}")
