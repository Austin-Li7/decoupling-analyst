from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from mgt470_analyst.rag.primary_corpus.sources import SourceSpec, load_sources
from mgt470_analyst.rag.primary_corpus.util import slugify_text, write_markdown


@dataclass(frozen=True)
class TranscriptHarvestResult:
    written: list[Path]
    skipped: list[str]
    estimated_transcription_minutes: float = 0.0


def harvest_youtube_transcripts(
    *,
    output_dir: Path | str,
    sources_path: Path | str | None = None,
    timeout: float = 30.0,
) -> TranscriptHarvestResult:
    talks = load_sources(sources_path).talks
    out_path = Path(output_dir) / "talks"
    written: list[Path] = []
    skipped: list[str] = []
    estimated_minutes = 0.0

    for talk in talks:
        transcript = ""
        if talk.use_existing_captions:
            try:
                transcript = _caption_transcript(talk, timeout=timeout)
            except Exception as exc:
                skipped.append(f"{talk.url}: captions failed: {exc}")

        if not transcript:
            try:
                transcript, minutes = _whisper_transcript(talk)
                estimated_minutes += minutes
            except Exception as exc:
                skipped.append(f"{talk.url}: whisper failed: {exc}")

        if not transcript:
            continue

        path = out_path / f"{slugify_text(talk.title)}.md"
        write_markdown(path, title=talk.title, url=talk.url, source=talk.source, body=transcript)
        written.append(path)

    return TranscriptHarvestResult(
        written=written,
        skipped=skipped,
        estimated_transcription_minutes=estimated_minutes,
    )


def _caption_transcript(talk: SourceSpec, *, timeout: float) -> str:
    from yt_dlp import YoutubeDL

    with YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(talk.url, download=False)

    subtitles = info.get("subtitles") or {}
    auto_captions = info.get("automatic_captions") or {}
    for group in (subtitles, auto_captions):
        caption_url = _pick_caption_url(group)
        if caption_url:
            text = httpx.get(caption_url, follow_redirects=True, timeout=timeout).text
            return _vtt_to_text(text)
    return ""


def _pick_caption_url(caption_groups: dict) -> str:
    for lang in ("en", "en-US", "en-GB"):
        for entry in caption_groups.get(lang) or []:
            if entry.get("ext") in {"vtt", "srv3", "ttml"} and entry.get("url"):
                return str(entry["url"])
    return ""


def _vtt_to_text(text: str) -> str:
    lines: list[str] = []
    previous = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line == "WEBVTT" or "-->" in line or line.isdigit():
            continue
        if line.startswith(("Kind:", "Language:")):
            continue
        clean = " ".join(line.replace("<c>", "").replace("</c>", "").split())
        if clean and clean != previous:
            lines.append(clean)
            previous = clean
    return "\n".join(lines)


def _whisper_transcript(talk: SourceSpec) -> tuple[str, float]:
    from openai import OpenAI
    from yt_dlp import YoutubeDL

    with tempfile.TemporaryDirectory() as tmp:
        output_template = str(Path(tmp) / "audio.%(ext)s")
        with YoutubeDL(
            {
                "format": "bestaudio/best",
                "outtmpl": output_template,
                "quiet": True,
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
            }
        ) as ydl:
            info = ydl.extract_info(talk.url, download=True)
        audio_path = next(Path(tmp).glob("audio.*"))
        duration = float(info.get("duration") or 0)
        with audio_path.open("rb") as audio_file:
            transcript = OpenAI().audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
        return str(transcript.text), duration / 60
