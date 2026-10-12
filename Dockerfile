# ==============================================================================
# DubStudio AI — Container Image for Hugging Face Spaces & Cloud Hosting
# ==============================================================================
FROM python:3.10-slim

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install ffmpeg and system dependencies required for audio/video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs under UID 1000 by default
RUN useradd -m -u 1000 user
ENV HOME=/home/user
ENV PATH=/home/user/.local/bin:$PATH

WORKDIR /app

# Ensure cache and working directories are writable by non-root user
RUN mkdir -p /app/outputs /app/downloads /app/cache /app/audio_segments /app/transcripts /app/translations \
    && chown -R user:user /app

# Copy dependency definition first for Docker layer caching
COPY --chown=user:user requirements.txt .

# Install dependencies as user
USER user
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application source code
COPY --chown=user:user . .

# Hugging Face Spaces expects port 7860
EXPOSE 7860
EXPOSE 8080

# Default to port 7860 (overridable via PORT environment variable or CLI argument)
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "7860"]
