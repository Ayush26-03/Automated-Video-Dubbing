# 🎙️ Automated Video Dubbing Pipeline 🎬

An end-to-end AI-powered video translation and dubbing system that transcribes speech, translates it into 25+ target languages, synthesizes high-fidelity neural speech, and synchronizes the audio back into the video with millisecond accuracy.

---

## 🌟 Key Features

- **Multi-Source Ingestion**: Works with YouTube URLs or local video files (`.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`).
- **State-of-the-Art Transcription**: Powered by **OpenAI Whisper** with automatic language detection and timestamp segmentation.
- **Multilingual Neural Translation**: Powered by **Meta's NLLB-200** (No Language Left Behind) supporting 25+ languages.
- **Realistic Voice Synthesis**: High quality neural voices using **Microsoft Edge-TTS** with male/female voice selection.
- **Smart Audio Alignment**: Dynamic tempo/speed adjustment and millisecond delay positioning for natural speech timing.
- **Subtitle Export**: Generates synchronized `.srt` and `.vtt` subtitles (original and translated) and optional soft subtitle embedding.
- **Dual Interface**: Interactive CLI menu or non-interactive command-line arguments for automated scripting and batch processing.

---

## 🏗️ Architecture Pipeline

```
[Input Video / YouTube URL]
           │
           ▼
   [1. Video Downloader] ────> Downloads / Resolves local video
           │
           ▼
   [2. Whisper Transcriber] ─> Generates timestamped segments & original SRT
           │
           ▼
   [3. NLLB-200 Translator] ─> Translates segment text into target language
           │
           ▼
   [4. Edge-TTS Synthesizer] ─> Generates neural voice audio clips
           │
           ▼
   [5. FFmpeg Audio Aligner] ─> Stretches/speeds clips & creates synced dubbed audio
           │
           ▼
   [6. Final Video Remixer] ──> Muxes video + dubbed audio + optional subtitles
           │
           ▼
[Dubbed Video Output (.mp4) & Subtitles (.srt / .vtt)]
```

---

## 🚀 Quick Start

### 1. Prerequisites

- **Python 3.10+**
- **FFmpeg**: Ensure `ffmpeg` and `ffprobe` are installed and available on your system `PATH`.

### 2. Installation

Clone or navigate to the repository directory:

```bash
# Activate virtual environment
.\venv\Scripts\activate   # On Windows
# source venv/bin/activate # On Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

---

## 💻 Usage

### 1. Modern Web Application (Recommended)

Start the local web studio:

```bash
python app.py
```

Then open your browser at **`http://localhost:8080`**.

The Web Studio includes:
- 🎬 Dual input support: YouTube URL or drag-and-drop local video files.
- 🌐 Interactive 25+ language selector grid with female/male neural voice picker.
- ⚙️ Real-time 6-step progress pipeline visualizer and live terminal log stream.
- 📺 Built-in video player for instant preview of the dubbed result.
- ⬇️ One-click export center for Dubbed Video (`.mp4`), Dubbed Audio (`.wav`), Subtitles (`.srt`, `.vtt`), and Transcript JSON.
- 📜 History drawer to inspect past dubbing sessions.

---

### 2. Interactive CLI Mode


Run without arguments for an interactive guide:

```bash
python main.py
```

You will be prompted to:
1. Provide a YouTube URL or local video path.
2. Select your target language (e.g., English, Spanish, Hindi, French, German, Japanese, etc.).
3. Choose voice gender (Female / Male).
4. Select the Whisper model size (`tiny`, `base`, `small`, `medium`, `large`).

---

### 2. Command Line (CLI) Mode

Run directly with command-line flags:

```bash
# Dub a YouTube video into Spanish
python main.py -u "https://www.youtube.com/watch?v=EXAMPLE" -t es

# Dub a local video into Hindi with a male voice using 'small' Whisper model
python main.py -i sample.mp4 -t hi -g male -m small

# Dub a video into Japanese and embed soft subtitles
python main.py -i input.mp4 -t ja --embed-subtitles
```

#### CLI Options:
| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--input` | `-i` | Path to local video file or URL | None |
| `--url` | `-u` | YouTube or online video URL | None |
| `--target-lang` | `-t` | Target language code (`en`, `es`, `hi`, `fr`, `de`, `ja`, etc.) | `en` |
| `--gender` | `-g` | TTS voice gender (`female` / `male`) | `female` |
| `--model` | `-m` | Whisper model size (`tiny`, `base`, `small`, `medium`, `large`) | `base` |
| `--voice` | `-v` | Custom Edge-TTS voice identifier | Auto |
| `--embed-subtitles` | | Embed soft subtitles into output MP4 | `False` |

---

## 🌐 Supported Languages & Voices

| Code | Language | Female Voice | Male Voice |
|------|----------|--------------|------------|
| `en` | English | `en-US-AriaNeural` | `en-US-GuyNeural` |
| `es` | Spanish | `es-ES-ElviraNeural` | `es-ES-AlvaroNeural` |
| `hi` | Hindi | `hi-IN-SwaraNeural` | `hi-IN-MadhurNeural` |
| `fr` | French | `fr-FR-DeniseNeural` | `fr-FR-HenriNeural` |
| `de` | German | `de-DE-KatjaNeural` | `de-DE-ConradNeural` |
| `ja` | Japanese | `ja-JP-NanamiNeural` | `ja-JP-KeitaNeural` |
| `zh` | Chinese (Simplified) | `zh-CN-XiaoxiaoNeural` | `zh-CN-YunxiNeural` |
| `pt` | Portuguese | `pt-BR-FranciscaNeural` | `pt-BR-AntonioNeural` |
| `it` | Italian | `it-IT-ElsaNeural` | `it-IT-DiegoNeural` |
| `ru` | Russian | `ru-RU-SvetlanaNeural` | `ru-RU-DmitryNeural` |
| `ko` | Korean | `ko-KR-SunHiNeural` | `ko-KR-InJoonNeural` |
| `ar` | Arabic | `ar-SA-ZariyahNeural` | `ar-SA-HamedNeural` |
| `bn` | Bengali | `bn-IN-TanishaaNeural` | `bn-IN-BashkarNeural` |
| `mr` | Marathi | `mr-IN-AarohiNeural` | `mr-IN-ManoharNeural` |
| `ta` | Tamil | `ta-IN-PallaviNeural` | `ta-IN-ValluvarNeural` |
| `te` | Telugu | `te-IN-ShrutiNeural` | `te-IN-MohanNeural` |
| `tr` | Turkish | `tr-TR-EmelNeural` | `tr-TR-AhmetNeural` |
| `id` | Indonesian | `id-ID-GadisNeural` | `id-ID-ArdiNeural` |
| `nl` | Dutch | `nl-NL-ColetteNeural` | `nl-NL-FennaNeural` |
| `vi` | Vietnamese | `vi-VN-HoaiMyNeural` | `vi-VN-NamMinhNeural` |

---

## 📂 Project Structure

```
automated-video-dubbing/
├── main.py                 # Main CLI and interactive entrypoint
├── requirements.txt        # Python dependencies
├── README.md               # Documentation
├── src/
│   ├── __init__.py
│   ├── config.py           # Language mappings and voice presets
│   ├── downloader.py       # Handles local files and YouTube downloads
│   ├── transcriber.py      # Whisper speech recognition
│   ├── translator.py       # NLLB-200 multi-language translation
│   ├── tts.py              # Edge-TTS speech generation
│   ├── audio_aligner.py    # FFmpeg timestamp alignment and pacing
│   ├── final_remixer.py    # Merges video + audio + subtitles
│   └── subtitles.py        # Generates SRT & VTT subtitle files
└── outputs/                # Timestamped run sessions with all artifacts
    └── <RUN_ID>/
        ├── downloads/
        ├── transcripts/
        ├── translations/
        ├── subtitles/
        ├── audio_segments/
        └── output/
```

---

## 🐳 Docker & Cloud Deployment (Hugging Face Spaces)

### Running with Docker Locally

Build and start the container with `ffmpeg` and all neural models bundled:

```bash
docker build -t dubstudio-ai .
docker run -p 7860:7860 dubstudio-ai
```

Open **`http://localhost:7860`** in your browser.

---

### Deploying to Hugging Face Spaces (Free Cloud Hosting)

1. Create a free account on [Hugging Face](https://huggingface.co).
2. Go to **New Space** → Name it (e.g. `dubstudio-ai`).
3. Select **Docker** (Blank template) with the free 16 GB RAM + 2 vCPU tier.
4. Clone your Space repository or push this repository directly:
   ```bash
   git remote add space https://huggingface.co/spaces/<your-username>/dubstudio-ai
   git push space main
   ```
5. Hugging Face will automatically build the `Dockerfile` and launch your live studio at:
   `https://huggingface.co/spaces/<your-username>/dubstudio-ai`

---

## 📄 License
This project is open-source under the MIT License.
