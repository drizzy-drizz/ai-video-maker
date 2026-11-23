"""Editable captions with exact scene-relative cues and optional MP4 burn-in.

Manual cues are honored exactly as entered, and the SAME SRT is burned into
the final MP4 and offered as download. Estimated cues remain explicitly
marked as approximate, never claimed to be force-aligned to speech.
"""
from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

import studio_quality as quality

ALLOWED_MODES = {"sidecar", "burned"}
MAX_CUES_PER_SCENE = 500
MAX_TEXT_CHARS = 400
VIDEO_MARGIN = 0.07


def _sec(value, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"Invalid caption {name}; enter a number of seconds") from exc
    if not math.isfinite(result):
        raise ValueError(f"Caption {name} must be a finite number")
    return result


def validate_manual_cues(cues: list, scene_duration: float) -> list[dict]:
    """Never silently fix bad cue timings; prevent overlapping captions/cut-off."""
    if not isinstance(cues, list) or len(cues) > MAX_CUES_PER_SCENE:
        raise ValueError(f"Manual caption cues must be a list of at most {MAX_CUES_PER_SCENE}")
    parsed = []
    last_end = -1.0
    for index, raw in enumerate(cues, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"Caption {index} must have start/end/text")
        start = _sec(raw.get("start"), "start")
        end = _sec(raw.get("end"), "end")
        text = str(raw.get("text") or "").strip()
        if not text or len(text) > MAX_TEXT_CHARS:
            raise ValueError(f"Caption {index} must have 1-{MAX_TEXT_CHARS} characters")
        if start < 0 or end <= start or start < last_end - 0.0005:
            raise ValueError(f"Caption {index} has overlapping or invalid times")
        if end > scene_duration + VIDEO_MARGIN:
            raise ValueError(f"Caption {index} ends beyond its shot ({scene_duration:.2f}s)")
        if end - start < 0.05:
            raise ValueError(f"Caption {index} duration must be at least 0.05s")
        parsed.append({"start": start, "end": end, "text": text})
        last_end = end
    return parsed


def parse_cue_lines(source: str) -> list[dict]:
    """Editor syntax, each line: 0.00 --> 2.00 | Spoken words.

    Per-scene seconds, never absolute episode clock. Use empty text area to
    revert to estimates. The UI can round trip this deterministic grammar.
    """
    if len(source) > 80_000:
        raise ValueError("Caption editor input too large")
    cues = []
    for number, line in enumerate(source.splitlines(), 1):
        value = line.strip()
        if not value:
            continue
        if "-->" not in value or "|" not in value:
            raise ValueError(f"Line {number}: use start --> end | caption text")
        timing, text = value.split("|", 1)
        start, end = timing.split("-->", 1)
        cues.append({"start": _sec(start.strip(), "start"), "end": _sec(end.strip(), "end"),
                     "text": text.strip()})
    return cues


def cues_as_lines(cues: list[dict]) -> str:
    return "\n".join(f"{float(cue['start']):.2f} --> {float(cue['end']):.2f} | "
                     f"{str(cue.get('text') or '')}" for cue in cues)


def build_srt(scenes: list[dict], durations: list[float],
              timeline: list[dict] | None = None) -> tuple[str, dict]:
    """Compose matching manual/estimated SRT for hard cuts OR overlapping transitions.

    Timeline entries contain global starts and per-shot reserved caption windows.
    The overlap midpoint is the subtitle handoff; no simultaneous SRT captions.
    """
    if len(scenes) != len(durations) or (timeline is not None and len(timeline) != len(scenes)):
        raise ValueError("Scene, duration and timeline lengths differ")
    cues = []
    elapsed = 0.0
    manual_count = 0
    estimated_count = 0
    for index, (scene, duration) in enumerate(zip(scenes, durations)):
        duration = _sec(duration, "scene duration")
        if duration <= 0:
            raise ValueError("Caption scene duration must be positive")
        entry = timeline[index] if timeline is not None else {}
        offset = float(entry.get("start", elapsed))
        caption_min = float(entry.get("caption_min", 0.0))
        caption_max = float(entry.get("caption_max", duration))
        user_cues = scene.get("caption_cues") or []
        if user_cues:
            entries = validate_manual_cues(user_cues, duration)
            for manual in entries:
                if (manual["start"] < caption_min - 0.001 or
                        manual["end"] > caption_max + 0.001):
                    raise ValueError(
                        f"Shot {index+1}: manual subtitle extends into a transition; "
                        "move the timing inside the unoverlapped caption window")
            manual_count += len(entries)
        else:
            # Match the actual chosen spoken words, not silent screenplay directions.
            # Timing remains approximate unless the user sets manual cue intervals.
            text = ("" if scene.get("voice_mode") == "silent" else
                    str(scene.get("voice_script") or scene.get("script") or "").strip())
            words = text.split()
            blocks = [" ".join(words[i:i+7]) for i in range(0, len(words), 7)]
            entries = []
            if blocks:
                word_total = len(words)
                at = caption_min
                usable = caption_max-caption_min
                if usable < 0.05:
                    raise ValueError(f"Shot {index+1}: transition leaves no readable caption interval")
                for chunk in blocks:
                    span = usable * len(chunk.split()) / word_total
                    entries.append({"start": at, "end": at+span, "text": chunk})
                    at += span
                estimated_count += len(entries)
        for cue in entries:
            start = quality.srt_timestamp(offset + cue["start"])
            end = quality.srt_timestamp(offset + min(duration, cue["end"]))
            cues.append(f"{len(cues)+1}\n{start} --> {end}\n{cue['text']}\n")
        elapsed = offset + duration
    mode = "manual" if manual_count and not estimated_count else (
        "mixed_manual_and_estimated" if manual_count else "estimated")
    return "\n".join(cues) + ("\n" if cues else ""), {
        "caption_timing_mode": mode, "manual_cues": manual_count,
        "estimated_cues": estimated_count,
        "timeline_aware": timeline is not None
    }


def validate_caption_project(scenes: list[dict], durations: list[float]) -> None:
    if len(scenes) != len(durations):
        raise ValueError("Caption scene and duration counts differ")
    for scene, duration in zip(scenes, durations):
        if scene.get("caption_cues"):
            validate_manual_cues(scene["caption_cues"], duration)


def subtitle_filter_available() -> bool:
    try:
        result = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                                capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and any(
        line.split()[1:2] == ["subtitles"]
        for line in result.stdout.splitlines() if line.strip()
    )


def apply_caption_mode(source: Path, srt: Path, target: Path, mode: str, *,
                       height: int) -> dict:
    """Export to a new file. Caller performs QA then atomically replaces final MP4.

    Working directory is the SRT folder, with safe filename under our control.
    This avoids Windows filtergraph escaping around drive-colon & spaces.
    """
    if mode not in ALLOWED_MODES:
        raise ValueError("Caption display mode must be sidecar or burned")
    if not source.is_file() or not srt.is_file():
        raise ValueError("Missing MP4 or subtitle file")
    if source.resolve() == target.resolve():
        raise ValueError("Caption export target must be different from source")
    if mode == "sidecar" or not srt.read_text(encoding="utf-8-sig").strip():
        shutil.copy2(source, target)
        return {"mode": "sidecar" if mode == "sidecar" else "burned_no_cues",
                "caption_filter": None}
    if not subtitle_filter_available():
        raise RuntimeError("This FFmpeg build lacks the libass 'subtitles' filter. Install an FFmpeg build with --enable-libass or use sidecar captions.")
    font_size = 22 if height >= 960 else 19
    margin_v = 95 if height >= 960 else 56
    # ASS force_style: constant, controlled palette. Font availability varies by OS;
    # final MP4 preview shows exactly what was burned; no independent CSS imitation.
    style = (f"FontName=Arial,FontSize={font_size},PrimaryColour=&H00FFFFFF,"
             f"OutlineColour=&H00000000,Outline=3,Shadow=0,"
             f"Alignment=2,MarginV={margin_v}")
    subtitle_name = srt.name
    if not subtitle_name.replace("-", "").replace("_", "").replace(".", "").isalnum():
        raise ValueError("Subtitle filename must be ASCII-safe")
    filter_spec = f"subtitles=filename={subtitle_name}:force_style='{style}'"
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
         "-vf", filter_spec, "-map", "0:v:0", "-map", "0:a:0",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
         "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(target)],
        cwd=str(srt.parent), capture_output=True, text=True, timeout=3600
    )
    if result.returncode:
        raise RuntimeError("Caption burn-in failed: " + (result.stderr or "")[-1600:])
    return {"mode": "burned", "caption_filter": "FFmpeg libass subtitles"}
