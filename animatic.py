"""Complete CPU-capable *motion storyboard* export pipeline.

This is NOT diffusion-generated video: every shot moves an approved existing
image with a deterministic Ken Burns camera move. Finished MP4 contains an audio
stream, optional complete narration, optional user-licensed music, SRT captions,
a technical QA JSON and explicit animatic provenance. Real AI-video files and
shot edit data remain untouched.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from pathlib import Path

import asset_library
import studio_quality as quality
import caption_engine
import sound_effects

MOTIONS = {"zoom_in", "zoom_out", "pan_left", "pan_right", "still"}
FPS = 24


def run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args,
                            capture_output=True, text=True, timeout=3600)
    if result.returncode:
        raise RuntimeError("FFmpeg storyboard failure: " + (result.stderr or result.stdout)[-1600:])


def _motion_filter(width: int, height: int, frames: int, motion: str) -> str:
    if motion not in MOTIONS:
        raise ValueError("Invalid storyboard camera motion: " + motion)
    # Uniform overscan avoids letterboxing on aspect-mismatched reference images.
    # zoompan handles the 1-frame input and outputs precisely 'frames' frames.
    canvas_w = math.ceil(width * 1.18 / 2) * 2
    canvas_h = math.ceil(height * 1.18 / 2) * 2
    base = (f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=increase,"
            f"crop={canvas_w}:{canvas_h},setsar=1,")
    count = max(1, frames - 1)
    if motion == "zoom_in":
        zoom = f"1+0.10*on/{count}"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "zoom_out":
        zoom = f"1.10-0.10*on/{count}"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "pan_left":
        zoom = "1.13"
        x = f"(iw-iw/zoom)*(1-on/{count})"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "pan_right":
        zoom = "1.13"
        x = f"(iw-iw/zoom)*on/{count}"
        y = "ih/2-(ih/zoom/2)"
    else:
        zoom = "1.0"
        x = "0"
        y = "0"
    return (base + f"zoompan=z='{zoom}':x='{x}':y='{y}':d={frames}:"
            f"s={width}x{height}:fps={FPS},format=yuv420p")


def _validated_narration(scene: dict) -> tuple[Path | None, float]:
    if scene.get("voice_mode") == "silent":
        return None, 0.0
    path = quality.normalized_path(scene.get("narration"))
    if path is None:
        return None, 0.0
    if path.suffix.lower() not in quality.AUDIO_EXTENSIONS or not path.is_file():
        raise ValueError("Missing or unsupported narration file: " + str(path))
    info = quality.media_info(path)
    if not info["has_audio"] or info["duration"] <= 0:
        raise ValueError("Narration file has no decodable audio: " + str(path))
    return path, info["duration"]


def validated_music(episode: dict) -> Path | None:
    path = quality.normalized_path(episode.get("soundtrack"))
    if not path:
        return None
    if path.suffix.lower() not in quality.AUDIO_EXTENSIONS or not path.is_file():
        raise ValueError("Music path missing or unsupported")
    info = quality.media_info(path)
    if not info["has_audio"] or info["duration"] < 0.2:
        raise ValueError("Music file does not contain usable audio")
    if not episode.get("soundtrack_rights_confirmed"):
        raise ValueError("Confirm you own or have permission to use this music before export")
    soundtrack_settings(episode, info["duration"])
    return path


def soundtrack_settings(episode: dict, music_duration: float) -> dict:
    """User-controlled start position, gain, looping and fades with strict bounds."""
    def numeric(field: str, default: float) -> float:
        raw = episode.get(field)
        try:
            value = float(default if raw in (None, "") else raw)
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError("Soundtrack " + field + " must be a number") from exc
        if not math.isfinite(value):
            raise ValueError("Soundtrack " + field + " must be finite")
        return value
    start = numeric("soundtrack_start_seconds", 0.0)
    gain = numeric("soundtrack_gain", 0.12)
    fade_in = numeric("soundtrack_fade_in_seconds", 0.0)
    fade_out = numeric("soundtrack_fade_out_seconds", 1.0)
    if start < 0 or start >= music_duration:
        raise ValueError(
            "Soundtrack start must be within the actual music file duration")
    if not 0 <= gain <= 1:
        raise ValueError("Soundtrack gain must be between 0 (muted) and 1")
    if min(fade_in, fade_out) < 0 or max(fade_in, fade_out) > 30:
        raise ValueError("Soundtrack fades must be 0–30 seconds")
    return {
        "start_seconds": start, "gain": gain, "fade_in": fade_in,
        "fade_out": fade_out, "loop": episode.get("soundtrack_loop") is not False
    }


def apply_soundtrack(assembled: Path, music: Path, duration: float, output: Path,
                     *, settings: dict | None = None) -> None:
    """Mix licensed music from the chosen song point under real audio.

    Same FFmpeg mix is used for actual footage and motion storyboards; presets
    are saved per episode and do not require rebuilding a static 'recipe'.
    """
    if duration <= 0 or not math.isfinite(duration):
        raise ValueError("Soundtrack render duration must be positive and finite")
    info = quality.media_info(music)
    if not info["has_audio"]:
        raise ValueError("Soundtrack file has no playable audio")
    options = soundtrack_settings(settings or {}, info["duration"])
    fade_in = min(options["fade_in"], duration)
    fade_out = min(options["fade_out"], max(0, duration-fade_in))
    filter_parts = [
        "[0:a:0]aresample=48000,apad[voice]",
        f"[1:a:0]aresample=48000,volume={options['gain']:.6f},"
        f"atrim=duration={duration:.6f},apad"
        + (f",afade=t=in:st=0:d={fade_in:.6f}" if fade_in else "")
        + (f",afade=t=out:st={max(0,duration-fade_out):.6f}:d={fade_out:.6f}" if fade_out else "")
        + "[music]",
        "[voice][music]amix=inputs=2:duration=first:normalize=0,"
        "alimiter=limit=0.95[mixed]"
    ]
    command = ["-i", str(assembled)]
    if options["loop"]:
        command += ["-stream_loop", "-1"]
    if options["start_seconds"]:
        command += ["-ss", f"{options['start_seconds']:.6f}"]
    command += ["-i", str(music)]
    run_ffmpeg(command + [
        "-filter_complex", ";".join(filter_parts),
        "-map", "0:v:0", "-map", "[mixed]", "-c:v", "copy",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-t", f"{duration:.6f}", "-movflags", "+faststart", str(output)
    ])


def preflight_animatic(series: dict, episode: dict) -> dict:
    issues = []
    expected = 0.0
    if not episode.get("scenes"):
        issues.append({"scene": None, "message": "Episode contains no scenes"})
    caption_mode = episode.get("caption_mode") or "sidecar"
    if caption_mode not in caption_engine.ALLOWED_MODES:
        issues.append({"scene": None, "message": "Invalid caption display mode"})
    elif caption_mode == "burned" and not caption_engine.subtitle_filter_available():
        issues.append({"scene": None, "message": "FFmpeg libass subtitles filter is required for burned captions"})
    for i, scene in enumerate(episode.get("scenes") or [], 1):
        try:
            selected = asset_library.resolve_image(series, scene)
            if selected is None:
                raise ValueError("Select a character/reference image for this scene")
            quality.validate_image(selected)
            voice, audio_length = _validated_narration(scene)
            duration = max(2.0, float(scene.get("duration_hint_seconds") or 6),
                           audio_length + 0.45 if voice else 0)
            if not math.isfinite(duration) or duration > 3600:
                raise ValueError("Scene duration must be finite and at most 60 minutes")
            if scene.get("animatic_motion") and scene["animatic_motion"] not in MOTIONS:
                raise ValueError("Invalid camera motion")
            caption_engine.validate_manual_cues(scene.get("caption_cues") or [],
                                                math.ceil(duration * FPS) / FPS)
            sound_effects.validated_effects(scene, math.ceil(duration * FPS) / FPS)
            expected += math.ceil(duration * FPS) / FPS
        except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
            issues.append({"scene": i, "message": str(exc)})
    try:
        validated_music(episode)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        issues.append({"scene": None, "message": str(exc)})
    return {"can_render": not issues, "status": "ready_for_motion_storyboard" if not issues else "blocked",
            "missing": issues, "duration_estimate_seconds": round(expected, 2),
            "mode": "motion_storyboard_NOT_diffusion_AI_video",
            "note": "Generated from approved still images via FFmpeg camera motion. No motion diffusion model is used."}


def _scene_segment(series: dict, scene: dict, filename: Path, width: int, height: int,
                   number: int) -> float:
    image = asset_library.resolve_image(series, scene)
    if image is None:
        raise ValueError(f"Scene {number} has no image")
    quality.validate_image(image)
    voice, voice_duration = _validated_narration(scene)
    secs = max(2.0, float(scene.get("duration_hint_seconds") or 6),
               voice_duration + 0.45 if voice else 0)
    frames = math.ceil(secs * FPS)
    duration = frames / FPS
    filter_string = _motion_filter(width, height, frames, scene.get("animatic_motion") or "zoom_in")
    silent_video = filename.with_name(filename.stem + "-video.mp4")
    try:
        run_ffmpeg(["-i", str(image), "-vf", filter_string, "-frames:v", str(frames),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                    "-pix_fmt", "yuv420p", "-an", str(silent_video)])
        inputs = ["-i", str(silent_video)]
        if voice:
            inputs += ["-i", str(voice)]
        else:
            inputs += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        # apad protects narration tails and ensures an audio stream for every segment.
        run_ffmpeg(inputs + ["-map", "0:v:0", "-map", "1:a:0", "-af", "aresample=48000,apad",
                             "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-ac", "2",
                             "-b:a", "160k", "-t", f"{duration:.6f}", str(filename)])
        if scene.get("sound_effects"):
            effects_file = filename.with_name(filename.stem + "-effects.mp4")
            sound_effects.mix_scene_effects(filename, scene, duration, effects_file)
            os.replace(effects_file, filename)
        return quality.media_info(filename)["duration"]
    finally:
        silent_video.unlink(missing_ok=True)


def render_animatic(series: dict, episode: dict, data_root: Path) -> dict:
    """Render complete standalone animatic without mutating original clip assignments."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("Install FFmpeg and FFprobe first")
    preflight = preflight_animatic(series, episode)
    if not preflight["can_render"]:
        raise ValueError("Animatic blocked: " +
                         "; ".join(f"scene {f['scene']}: {f['message']}" for f in preflight["missing"]))
    project_id, episode_id = series["id"], episode["id"]
    width, height = (540, 960) if series.get("format") == "9:16" else (960, 540)
    folder = data_root / "animatic" / project_id / episode_id
    folder.mkdir(parents=True, exist_ok=True)
    clips, durations = [], []
    for i, scene in enumerate(episode["scenes"], 1):
        target = folder / f"scene-{i:05d}.mp4"
        lengths = _scene_segment(series, scene, target, width, height, i)
        clips.append(target)
        durations.append(lengths)
    manifest = folder / "concat.txt"
    manifest.write_text("".join(f"file '{p.name}'\n" for p in clips), encoding="utf-8")
    export_dir = data_root / "exports" / project_id
    export_dir.mkdir(parents=True, exist_ok=True)
    assembled = folder / "assembled.mp4"
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(manifest),
                "-c", "copy", "-movflags", "+faststart", str(assembled)])
    final = export_dir / (episode_id + "-animatic.mp4")
    staging = folder / "final-staging.mp4"
    prepared = folder / "pre-caption.mp4"
    soundtrack = validated_music(episode)
    if soundtrack:
        apply_soundtrack(assembled, soundtrack, sum(durations), prepared, settings=episode)
    else:
        shutil.copy2(assembled, prepared)
    srt = export_dir / (episode_id + "-animatic.srt")
    subtitle_text, caption_stats = caption_engine.build_srt(episode["scenes"], durations)
    srt.write_text(subtitle_text, encoding="utf-8-sig")
    caption_output = caption_engine.apply_caption_mode(
        prepared, srt, staging, episode.get("caption_mode") or "sidecar", height=height)
    qa = quality.quality_report_export(staging, sum(durations))
    qa.update(caption_stats)
    qa["caption_export"] = caption_output["mode"]
    qa.update({
        "provenance": "FFmpeg motion storyboard built from approved still images — NOT AI-generated moving footage",
        "mode": "animatic",
        "estimated_subtitle_timing": caption_stats["estimated_cues"] > 0,
        "scene_count": len(clips),
        "music_included": bool(soundtrack),
        "scene_sfx_count": sum(len(scene.get("sound_effects") or []) for scene in episode["scenes"]),
        "soundtrack_settings": (
            soundtrack_settings(episode, quality.media_info(soundtrack)["duration"])
            if soundtrack else None),
        "narration_scene_count": sum(bool(scene.get("narration")) for scene in episode["scenes"])
    })
    qa_path = export_dir / (episode_id + "-animatic-quality.json")
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    if qa["issues"]:
        raise RuntimeError("Animatic QC failure: " + "; ".join(qa["issues"]))
    # Replace the published MP4 only after complete codec/audio/duration QA.
    os.replace(staging, final)
    return {"video": str(final), "srt": str(srt), "quality": str(qa_path),
            "mode": "motion_storyboard_NOT_AI_generated_video"}
