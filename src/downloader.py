import re
import shutil
import time
from pathlib import Path
try:
    import yt_dlp
except ImportError:
    yt_dlp = None


def is_url(source: str) -> bool:
    """Check if the given string looks like a web/YouTube URL."""
    url_pattern = re.compile(
        r'^(?:http|ftp)s?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return bool(url_pattern.match(source.strip())) or "youtu" in source.lower()


def download_video(source: str, output_dir: str = "downloads") -> str:
    """
    Accept either a YouTube URL or a local video file path.
    If URL: download the video to output_dir using yt-dlp.
    If local file: validate existence and return absolute/resolved path.
    """
    source_clean = source.strip().strip('"').strip("'")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Check if local file exists
    local_file = Path(source_clean)
    if local_file.is_file():
        print(f"\n[1/6] Using local video file: {local_file.resolve()}")
        dest_file = output_path / local_file.name
        if not dest_file.exists() and local_file.resolve() != dest_file.resolve():
            shutil.copy2(local_file, dest_file)
            print(f"Copied to workspace: {dest_file}")
            return str(dest_file.resolve())
        return str(local_file.resolve())

    # Otherwise treat as URL
    if not is_url(source_clean):
        raise FileNotFoundError(f"Source '{source_clean}' is neither a valid URL nor an existing local file.")

    if yt_dlp is None:
        raise RuntimeError("yt-dlp is not installed. Please install it with: pip install yt-dlp")

    # Optimized yt-dlp options for Windows stability and avoiding WinError 32 file locks
    ydl_opts = {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "outtmpl": str(output_path / "source_video.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": False,
        "windowsfilenames": True,
        "restrictfilenames": True,
        "overwrites": True,
        "retries": 3,
        "fragment_retries": 3,
    }

    cookie_file = Path("cookies.txt")
    if cookie_file.exists():
        ydl_opts["cookiefile"] = str(cookie_file.resolve())

    print("\n[1/6] Downloading video via yt-dlp...")

    # Retry wrapper to handle transient Windows antivirus / indexer file locks
    max_retries = 3
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(source_clean, download=True)
                downloaded_file = ydl.prepare_filename(info)

            downloaded_path = Path(downloaded_file)
            if downloaded_path.suffix != ".mp4":
                possible_mp4 = downloaded_path.with_suffix(".mp4")
                if possible_mp4.exists():
                    downloaded_path = possible_mp4

            if downloaded_path.exists():
                # Ensure it's not a video-only format file
                if not re.search(r'\.f\d+', downloaded_path.name):
                    print(f"Video ready: {downloaded_path.resolve()}")
                    return _finalize_and_verify(downloaded_path, output_path)

        except Exception as e:
            last_err = e
            print(f"Download attempt {attempt}/{max_retries} notice: {e}")
            time.sleep(1.5)

            # Check if source_video.temp.mp4 was created by ffmpeg merger but failed rename due to WinError 32
            temp_mp4 = output_path / "source_video.temp.mp4"
            target_mp4 = output_path / "source_video.mp4"
            if temp_mp4.exists() and temp_mp4.stat().st_size > 1024:
                print("Detected merged temp file. Resolving file lock and renaming...")
                for _ in range(10):
                    try:
                        if target_mp4.exists():
                            target_mp4.unlink(missing_ok=True)
                        temp_mp4.rename(target_mp4)
                        print(f"Successfully finalized: {target_mp4.resolve()}")
                        return _finalize_and_verify(target_mp4, output_path)
                    except Exception:
                        time.sleep(1.0)
                # If rename still blocked, use the temp file directly as it has full audio/video
                return _finalize_and_verify(temp_mp4, output_path)

            if target_mp4.exists() and target_mp4.stat().st_size > 1024:
                return _finalize_and_verify(target_mp4, output_path)

    # Check for split format files left by yt-dlp and manually mux with ffmpeg
    final_video = _recover_and_mux_split_files(output_path)
    if final_video:
        return str(final_video.resolve())

    raise RuntimeError(f"Failed to download video after {max_retries} attempts: {last_err}")


def _finalize_and_verify(video_file: Path, output_path: Path) -> str:
    """Ensure video file has audio; if missing, look for audio stream in folder and merge."""
    if _has_audio(video_file):
        return str(video_file.resolve())

    print(f"Warning: {video_file.name} does not contain an audio stream. Checking for audio files...")
    # Look for audio files in output directory
    audio_candidates = [
        f for f in output_path.iterdir()
        if f.is_file() and f.suffix.lower() in [".m4a", ".mp3", ".wav", ".aac", ".opus", ".webm"]
        and not f.name.endswith(".temp.mp4") and f.resolve() != video_file.resolve()
    ]
    if audio_candidates:
        audio_file = audio_candidates[0]
        merged_file = output_path / "source_video_merged.mp4"
        print(f"Muxing video ({video_file.name}) and audio ({audio_file.name}) using FFmpeg...")
        import subprocess
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_file),
            "-i", str(audio_file),
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(merged_file)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and merged_file.exists():
            print(f"Muxing complete: {merged_file}")
            return str(merged_file.resolve())

    return str(video_file.resolve())


def _has_audio(file_path: Path) -> bool:
    """Check if media file has at least one audio stream using ffprobe."""
    import subprocess
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(file_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return "audio" in res.stdout.lower()
    except Exception:
        return True


def _recover_and_mux_split_files(output_path: Path) -> Path:
    """If yt-dlp left separate video (.f*.mp4) and audio (.f*.m4a), combine them."""
    import subprocess
    video_files = [f for f in output_path.glob("*.mp4") if not f.name.endswith(".temp.mp4")]
    audio_files = [f for f in output_path.iterdir() if f.is_file() and f.suffix.lower() in [".m4a", ".webm", ".opus", ".aac"]]

    if not video_files:
        temp_file = output_path / "source_video.temp.mp4"
        if temp_file.exists():
            return temp_file

    best_video = max(video_files, key=lambda f: f.stat().st_size) if video_files else None
    best_audio = max(audio_files, key=lambda f: f.stat().st_size) if audio_files else None

    if best_video and _has_audio(best_video):
        return best_video

    if best_video and best_audio:
        target = output_path / "source_video.mp4"
        print(f"Recovering: muxing {best_video.name} with {best_audio.name}...")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(best_video),
            "-i", str(best_audio),
            "-c:v", "copy",
            "-c:a", "aac",
            str(target)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and target.exists():
            return target

    return best_video


if __name__ == "__main__":
    src_input = input("Enter YouTube URL or local video path: ").strip()
    try:
        video_path = download_video(src_input)
        print("\nSuccess!")
        print(f"Saved at: {video_path}")
    except Exception as e:
        print(f"\nFailed: {e}")