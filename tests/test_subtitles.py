"""Smoke tests for subtitle export."""

from src.subtitles import export_srt, export_vtt, format_timestamp_srt, format_timestamp_vtt


def test_format_timestamp_srt_basic():
    assert format_timestamp_srt(0) == "00:00:00,000"
    assert format_timestamp_srt(1.5) == "00:00:01,500"
    assert format_timestamp_srt(65.25) == "00:01:05,250"
    assert format_timestamp_srt(3661.123) == "01:01:01,123"


def test_format_timestamp_vtt_basic():
    assert format_timestamp_vtt(0) == "00:00:00.000"
    assert format_timestamp_vtt(2.5) == "00:00:02.500"


def test_export_srt_writes_segments(tmp_path):
    segs = [
        {"start": 0.0, "end": 1.0, "translated_text": "Hello world"},
        {"start": 1.5, "end": 2.5, "translated_text": "Second line"},
    ]
    out = tmp_path / "test.srt"
    export_srt(segs, str(out))

    content = out.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:01,000" in content
    assert "Hello world" in content
    assert "00:00:01,500 --> 00:00:02,500" in content
    assert "Second line" in content


def test_export_vtt_has_webvtt_header(tmp_path):
    segs = [{"start": 0.0, "end": 1.0, "translated_text": "Line"}]
    out = tmp_path / "test.vtt"
    export_vtt(segs, str(out))

    content = out.read_text(encoding="utf-8")
    assert content.startswith("WEBVTT")
    # Cue times use a dot separator, not a comma.
    assert "00:00:00.000 --> 00:00:01.000" in content


def test_export_skips_empty_segments(tmp_path):
    segs = [
        {"start": 0.0, "end": 1.0, "translated_text": "Real"},
        {"start": 1.0, "end": 2.0, "translated_text": "   "},  # whitespace only
    ]
    out = tmp_path / "x.srt"
    export_srt(segs, str(out))
    body = out.read_text(encoding="utf-8")
    # Only one cue should appear.
    assert body.count("-->") == 1
    assert "Real" in body
