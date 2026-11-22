"""Production checks, canonical shot prompts and estimated SRT timing.

The module has no hosted APIs or third-party Python dependencies. Reports are
technical heuristics; they are not evidence of audience-ready storytelling.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac"}


def normalized_path(raw: Any) -> Path | None:
    value = str(raw or "").strip()
    return Path(value).expanduser().resolve() if value else None


def media_info(path: Path) -> dict:
    """Real ffprobe duration and video/audio properties (no guess from metadata filename)."""
    response = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=False, capture_output=True, text=True, timeout=35,
    )
    if response.returncode:
        raise ValueError("FFprobe failed: " + (response.stderr or "")[-350:])
    try:
        data = json.loads(response.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("FFprobe returned invalid metadata") from exc
    streams = data.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    duration = float((data.get("format") or {}).get("duration") or
                     (video or audio or {}).get("duration") or 0)
    return {"duration": max(0.0, duration), "has_video": bool(video), "has_audio": bool(audio),
            "width": int((video or {}).get("width") or 0),
            "height": int((video or {}).get("height") or 0),
            "video_codec": (video or {}).get("codec_name", ""),
            "audio_codec": (audio or {}).get("codec_name", "")}


def referenced_characters(series: dict, scene: dict) -> list[dict]:
    """Use explicit character names or whole-word screenplay mentions; never assign all cast."""
    catalog = (series.get("bible") or {}).get("characters") or []
    names = {str(value).casefold() for value in scene.get("character_ids", [])}
    script = str(scene.get("script") or "")
    directed = str(scene.get("prompt") or "")
    results = []
    for item in catalog:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        match = bool(re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)",
                               script + "\n" + directed, re.IGNORECASE))
        if name.casefold() in names or match:
            results.append(item)
    return results



IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def reference_image_for_scene(series: dict, scene: dict) -> Path | None:
    """Use immutable approved asset IDs if assigned, else legacy local-image paths.

    Import locally to avoid an import cycle: asset_library uses validate_image.
    """
    from asset_library import resolve_image
    return resolve_image(series, scene)


def validate_image(path: Path) -> None:
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError("Reference image must be a PNG, JPEG or WebP file")
    if not path.is_file():
        raise ValueError("Reference image does not exist: " + str(path))
    size = path.stat().st_size
    if not 0 < size <= 25 * 1024 * 1024:
        raise ValueError("Reference image must be between 1B and 25MB")
    with open(path, "rb") as source:
        first = source.read(16)
    recognized = (first.startswith(b"\x89PNG\r\n\x1a\n") or
                  first.startswith(b"\xff\xd8\xff") or
                  (first[:4] == b"RIFF" and first[8:12] == b"WEBP"))
    if not recognized:
        raise ValueError("Reference image has a mismatched/invalid file header")


def compose_canonical_prompt(series: dict, episode: dict, scene: dict) -> dict:
    """Generate text-direction with explicit subject/wardrobe canon.

    Prompt text only: reference-image conditioning must be provided by a model
    adapter separately. This cannot guarantee visible identity consistency.
    """
    bible = series.get("bible") or {}
    parts = [
        "Make one continuous cinematic moving shot, with readable subject action and coherent spatial continuity.",
        f"Series: {str(series.get('title') or '')[:150]}",
        f"Genre: {str(series.get('genre') or 'General')[:120]}",
        f"Episode: {str(episode.get('title') or '')[:150]}",
    ]
    for field, label in [("world", "Established world"), ("style", "Required visual style"),
                         ("canon", "Never contradict continuity")]:
        value = str(bible.get(field) or "").strip()
        if value:
            parts.append(f"{label}: {value[:1200]}")
    characters = referenced_characters(series, scene)
    for person in characters:
        props = ["appearance", "wardrobe", "voice", "continuity"]
        details = [f"{prop}={str(person[prop])[:320]}" for prop in props if person.get(prop)]
        parts.append("Keep recurring character " + str(person["name"])[:100] +
                     " consistent: " + ("; ".join(details) or "retain their saved identity"))
    locations = bible.get("locations") or []
    source = str(scene.get("script") or "") + " " + str(scene.get("prompt") or "")
    for location in locations:
        if isinstance(location, dict):
            name = str(location.get("name") or "").strip()
            if name and re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", source, re.I):
                parts.append("Keep established location " + name[:100] + ": " +
                             str(location.get("description") or "")[:400])
    parts.extend([
        f"Source story beat (preserve meaning): {str(scene.get('script') or '')[:2000]}",
        f"Shot director instruction: {str(scene.get('prompt') or '')[:2500]}",
        "No invented cast, contradictory wardrobe changes, unrelated scenes, or on-screen writing.",
    ])
    return {"prompt": "\n".join(parts), "negative_prompt": str(scene.get("negative_prompt") or ""),
            "characters": [person["name"] for person in characters],
            "note": "Textual canon conditioning only; image-reference/identity fidelity is unverified."}


def episode_preflight(series: dict, episode: dict) -> dict:
    """Detect blocked or poor-quality inputs without replacing missing footage."""
    scenes = episode.get("scenes") or []
    findings: list[dict] = []
    clip_durations: list[float] = []
    seen = set()

    def add(level: str, code: str, message: str, scene_num: int | None = None):
        item: dict = {"level": level, "code": code, "message": message}
        if scene_num is not None:
            item["scene"] = scene_num
        findings.append(item)

    if not scenes:
        add("blocker", "no_scenes", "Episode has no shots")
    import caption_engine
    caption_mode = episode.get("caption_mode") or "sidecar"
    if caption_mode not in caption_engine.ALLOWED_MODES:
        add("blocker", "caption_mode_invalid", "Caption mode must be sidecar or burned")
    elif caption_mode == "burned" and not caption_engine.subtitle_filter_available():
        add("blocker", "caption_burn_unavailable", "FFmpeg is missing libass subtitles filter for burned MP4 captions")
    if not ((series.get("bible") or {}).get("characters") or []):
        add("advisory", "no_characters", "No recurring character records; identity continuity is not pinned")
    if not str((series.get("bible") or {}).get("style") or "").strip():
        add("advisory", "no_style", "No established visual style; shots may drift across the series")
    if not str((series.get("bible") or {}).get("canon") or "").strip():
        add("advisory", "no_canon", "No continuity rules defined yet")
    if not any(s.get("narration") for s in scenes):
        add("advisory", "no_narration", "No scene narration audio supplied; text captions are timing estimates")
    soundtrack = normalized_path(episode.get("soundtrack"))
    if soundtrack:
        if not episode.get("soundtrack_rights_confirmed"):
            add("blocker", "music_rights", "Confirm that you own or have permission to use this soundtrack")
        if not soundtrack.is_file() or soundtrack.suffix.lower() not in AUDIO_EXTENSIONS:
            add("blocker", "missing_soundtrack", "Soundtrack is missing or has an unsupported file type")
        else:
            try:
                sound = media_info(soundtrack)
                if not sound["has_audio"] or sound["duration"] < 0.2:
                    add("blocker", "invalid_soundtrack", "Soundtrack contains no usable audio stream")
            except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
                add("blocker", "invalid_soundtrack", str(exc)[:260])

    for i, scene in enumerate(scenes, 1):
        num = scene.get("number") or i
        clip = normalized_path(scene.get("clip"))
        if not clip or not clip.is_file():
            add("blocker", "missing_video", "Attach a real moving-video file", num)
            clip_durations.append(0.0)
            continue
        if clip.suffix.lower() not in VIDEO_EXTENSIONS:
            add("blocker", "unsupported_video", "Video extension is unsupported", num)
            clip_durations.append(0.0)
            continue
        if str(clip).casefold() in seen:
            add("advisory", "reused_clip", "Same video file is used in another scene", num)
        seen.add(str(clip).casefold())
        try:
            info = media_info(clip)
        except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
            add("blocker", "unreadable_video", str(exc)[:260], num)
            clip_durations.append(0.0)
            continue
        if not info["has_video"] or info["duration"] < 0.15:
            add("blocker", "invalid_video", "No decodable video or duration under 0.15 seconds", num)
            clip_durations.append(0.0)
            continue
        duration = info["duration"]
        clip_durations.append(duration)
        if scene.get("caption_cues"):
            try:
                caption_engine.validate_manual_cues(scene["caption_cues"], duration)
            except (ValueError, TypeError) as exc:
                add("blocker", "invalid_caption_timing", str(exc), num)
        if duration < 2.0:
            add("advisory", "very_short", "Moving shot is under 2 seconds", num)
        target_aspect = 9 / 16 if series.get("format") == "9:16" else 16 / 9
        if info["height"] and abs(info["width"] / info["height"] - target_aspect) > 0.45:
            add("advisory", "aspect_mismatch", "Source framing differs from export aspect; letterboxing expected", num)
        words = len(str(scene.get("script") or "").split())
        if words and words / duration > 3.5:
            add("advisory", "too_many_words", f"{words} script words / {duration:.1f}s may be too fast for readable captions or narration", num)
        reference = reference_image_for_scene(series, scene)
        if reference:
            try:
                validate_image(reference)
            except (OSError, ValueError) as exc:
                add("blocker", "reference_invalid", str(exc)[:260], num)
        cast = referenced_characters(series, scene)
        if len(cast) > 1 and not normalized_path(scene.get("reference_image")):
            if any(c.get("reference_image") for c in cast):
                add("advisory", "multi_cast_reference", "Multiple characters: only the first matching character image can feed a single-reference workflow", num)
        narration = normalized_path(scene.get("narration"))
        if narration:
            if not narration.is_file() or narration.suffix.lower() not in AUDIO_EXTENSIONS:
                add("blocker", "missing_narration", "Narration path is missing or unsupported", num)
            else:
                try:
                    voice = media_info(narration)
                    if not voice["has_audio"]:
                        add("blocker", "unreadable_narration", "No valid audio stream", num)
                    elif voice["duration"] > duration + 0.12:
                        add("blocker", "voice_longer_than_clip",
                            f"Voice is {voice['duration']:.2f}s but video is {duration:.2f}s. Extend or replace clip; narration will NOT be truncated.", num)
                except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
                    add("blocker", "unreadable_narration", str(exc)[:260], num)
    return {
        "status": "blocked" if any(f["level"] == "blocker" for f in findings) else "ready_for_assembly",
        "can_render": not any(f["level"] == "blocker" for f in findings),
        "findings": findings, "scene_count": len(scenes),
        "duration_estimate_seconds": round(sum(clip_durations), 2),
        "timing_note": "Subtitles are estimated from script+video lengths; there is no speech-to-word forced alignment."
    }


def srt_timestamp(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    seconds, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def make_subtitles(scenes: list[dict], durations: list[float], words_per_caption: int = 7) -> str:
    """Proportional scene-local subtitle estimates, not ASR/forced-alignment timestamps."""
    if len(scenes) != len(durations):
        raise ValueError("Scene count does not match rendered segment duration count")
    cues: list[str] = []
    elapsed = 0.0
    for scene, duration in zip(scenes, durations):
        words = str(scene.get("script") or "").split()
        if words and duration > 0:
            phrases = [" ".join(words[i:i + words_per_caption])
                       for i in range(0, len(words), words_per_caption)]
            total_words = sum(len(s.split()) for s in phrases)
            offset = 0.0
            for phrase in phrases:
                phrase_duration = duration * len(phrase.split()) / total_words
                start, end = elapsed + offset, elapsed + offset + phrase_duration
                cues.append(f"{len(cues) + 1}\n{srt_timestamp(start)} --> {srt_timestamp(end)}\n{phrase}\n")
                offset += phrase_duration
        elapsed += duration
    return "\n".join(cues) + ("\n" if cues else "")


def quality_report_export(path: Path, expected_duration: float) -> dict:
    """Mechanical post-export validation, NOT human perceptual QA."""
    info = media_info(path)
    issues = []
    if not info["has_video"]:
        issues.append("No video stream")
    if not info["has_audio"]:
        issues.append("No audio stream")
    if abs(info["duration"] - expected_duration) > max(0.75, expected_duration * 0.025):
        issues.append(f"Export duration {info['duration']:.2f}s differs from expected {expected_duration:.2f}s")
    if info["width"] <= 0 or info["height"] <= 0:
        issues.append("Invalid frame dimensions")
    return {
        "status": "technical_checks_passed" if not issues else "technical_checks_failed",
        "duration_seconds": round(info["duration"], 3),
        "expected_seconds": round(expected_duration, 3),
        "width": info["width"], "height": info["height"],
        "video_codec": info["video_codec"], "audio_codec": info["audio_codec"],
        "issues": issues,
        "note": "This checks codec/size/duration only; it cannot measure cinematic quality, speaker clarity, character drift or full caption timing."
    }
