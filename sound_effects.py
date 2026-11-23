"""Actual shot-local sound effects mixed into MP4 audio with FFmpeg.

Every SFX has an explicit audio path, cue time, gain and owner/licensing
confirmation. Audio is mixed AFTER video/voice normalization but BEFORE the
episode's scene transitions, preserving live-editor arrangement. No fake
sound effect placeholders; no paid APIs.
"""
from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

import studio_quality as quality


def _finite(raw, label: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Invalid SFX " + label + ": choose a numeric value") from exc
    if not math.isfinite(value):
        raise ValueError("SFX " + label + " must be finite")
    return value


def validated_effects(scene: dict, scene_duration: float) -> list[dict]:
    source = scene.get("sound_effects") or []
    if not isinstance(source, list):
        raise ValueError("Sound effects must be a list of audio cues")
    selected = []
    for index, raw in enumerate(source, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"SFX cue {index} needs a path, timing, gain and rights")
        path = quality.normalized_path(raw.get("path"))
        if not path or path.suffix.lower() not in quality.AUDIO_EXTENSIONS or not path.is_file():
            raise ValueError(f"SFX {index} audio file is missing or unsupported")
        if raw.get("rights_confirmed") is not True:
            raise ValueError(f"SFX {index} requires usage-rights confirmation")
        offset = _finite(raw.get("at_seconds", 0), "offset")
        gain = _finite(raw.get("gain", 0.30), "gain")
        if not 0 <= offset < scene_duration or scene_duration-offset < 0.05:
            raise ValueError(f"SFX {index} needs at least 0.05 seconds of room inside the trimmed shot")
        if not 0 <= gain <= 1.0:
            raise ValueError(f"SFX {index} gain must be between 0 and 1")
        info = quality.media_info(path)
        if not info["has_audio"] or info["duration"] < 0.05:
            raise ValueError(f"SFX {index} contains no usable audio")
        selected.append({
            "path": path, "at_seconds": offset, "gain": gain,
            "original_duration": info["duration"],
            "play_seconds": min(info["duration"], scene_duration-offset),
            "tail_trimmed": info["duration"] > scene_duration-offset + .02
        })
    return selected


def mix_scene_effects(source: Path, scene: dict, duration: float, output: Path) -> dict:
    """Write a distinct video stream with audio effects, never mutate source."""
    effects = validated_effects(scene, duration)
    if not effects:
        return {"mixed": False, "effects": 0, "tail_trimmed": 0}
    if source.resolve() == output.resolve():
        raise ValueError("Sound effect output must differ from its input")
    ffmpeg_args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source)]
    for effect in effects:
        ffmpeg_args += ["-i", str(effect["path"])]
    chains = ["[0:a:0]aresample=48000,apad[base]"]
    for index, item in enumerate(effects, 1):
        delay = round(item["at_seconds"] * 1000)
        length = item["play_seconds"]
        fade_duration = min(0.16, length / 3) if item["tail_trimmed"] else 0.0
        transform = (
            f"[{index}:a:0]aresample=48000,volume={item['gain']:.6f},"
            f"atrim=duration={length:.6f},asetpts=PTS-STARTPTS"
            + (f",afade=t=out:st={max(0,length-fade_duration):.6f}:d={fade_duration:.6f}"
               if fade_duration else "")
            + f",adelay={delay}:all=1,apad,atrim=duration={duration:.6f}[fx{index}]"
        )
        chains.append(transform)
    mix_sources = "[base]" + "".join(f"[fx{i}]" for i in range(1, len(effects)+1))
    chains.append(f"{mix_sources}amix=inputs={len(effects)+1}:duration=first:"
                  "normalize=0,alimiter=limit=0.95[mixed]")
    ffmpeg_args += [
        "-filter_complex", ";".join(chains), "-map", "0:v:0", "-map", "[mixed]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
        "-t", f"{duration:.6f}", "-movflags", "+faststart", str(output)
    ]
    result = subprocess.run(ffmpeg_args, capture_output=True, text=True, timeout=3600)
    if result.returncode:
        raise RuntimeError("Scene SFX mix failed: " + (result.stderr or result.stdout)[-1600:])
    return {
        "mixed": True, "effects": len(effects),
        "tail_trimmed": sum(item["tail_trimmed"] for item in effects)
    }
