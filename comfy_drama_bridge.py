"""Local speech-driven video and continuity-frame handoff for ComfyUI.

ComfyUI's standard server has /upload/image but not a reliable generic
/upload/audio endpoint across versions. Audio is therefore copied into a
USER-CONFIGURED local ComfyUI input directory for LoadAudio filenames. This
cannot run on remote cloud ComfyUI; absence of a shared input dir fails
clearly rather than pretending to attach speech.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

import studio_quality as quality


def digest(source: Path) -> str:
    sha = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def configured_input_folder() -> Path:
    raw = os.environ.get("AIVM_COMFY_INPUT_DIR", "").strip()
    if not raw:
        raise ValueError(
            "Speech-to-video needs AIVM_COMFY_INPUT_DIR pointing to the input "
            "folder of the locally installed ComfyUI instance. "
            "Remote ComfyUI audio upload is not assumed to work.")
    folder = Path(raw).expanduser().resolve()
    if not folder.is_dir() or not os.access(folder, os.W_OK):
        raise ValueError("AIVM_COMFY_INPUT_DIR must be an existing writable local ComfyUI input folder")
    return folder


def speech_script_digest(scene: dict) -> str:
    """Track whether a local TTS WAV still matches its associated text."""
    expected = str(scene.get("voice_script") or "").strip() or str(scene.get("script") or "").strip()
    return hashlib.sha256(expected.encode("utf-8")).hexdigest()


def speech_matches_scene(scene: dict) -> bool:
    provenance = scene.get("voice_provenance") or {}
    recorded = provenance.get("spoken_text_sha256")
    return not recorded or recorded == speech_script_digest(scene)


def stage_dialogue_audio(scene: dict) -> tuple[str, Path, dict]:
    if scene.get("voice_mode") == "silent":
        raise ValueError("Silent-action shot cannot condition a speech-driven video model")
    if not scene.get("dialogue_audio_rights_confirmed"):
        raise ValueError(
            "Confirm voice-model, speaker/likeness, and audio use rights before "
            "using scene narration to drive talking-video generation")
    if not speech_matches_scene(scene):
        raise ValueError(
            "Attached synthetic voice was generated from older spoken text. "
            "Regenerate/replace narration before using speech-to-video.")
    raw = quality.normalized_path(scene.get("narration"))
    if not raw or not raw.is_file() or raw.suffix.lower() not in quality.AUDIO_EXTENSIONS:
        raise ValueError("Speech-to-video requires an existing WAV/MP3/M4A/FLAC/OGG/OPUS/AAC narration file")
    info = quality.media_info(raw)
    if not info["has_audio"] or not math.isfinite(info["duration"]) or not 0.2 < info["duration"] <= 900:
        raise ValueError("Dialogue recording must contain 0.2–900 seconds of decodable audio")
    if raw.stat().st_size > 300 * 1024 * 1024:
        raise ValueError("Dialogue audio must be under 300MB for local model handoff")
    folder = configured_input_folder()
    filename = "aivm_dialogue_" + uuid.uuid4().hex[:16] + raw.suffix.lower()
    target = folder / filename
    intermediate = folder / (filename + ".part")
    try:
        with raw.open("rb") as src, intermediate.open("xb") as dest:
            shutil.copyfileobj(src, dest, length=1024*1024)
        if digest(intermediate) != digest(raw):
            raise ValueError("Copied voice hash mismatch; no speech was sent to ComfyUI")
        os.replace(intermediate, target)
        return filename, target, {
            "source_wav": str(raw), "duration_seconds": round(info["duration"], 3),
            "sha256": digest(raw), "copied_to_local_comfy_input": True,
            "speech_reference_rights_confirmed": True,
        }
    except Exception:
        intermediate.unlink(missing_ok=True)
        target.unlink(missing_ok=True)
        raise


def previous_approved_frame(series: dict, episode: dict, scene_id: str,
                            working_dir: Path) -> tuple[Path, dict]:
    """Extract actual frame before shot from approved preceding footage.

    The last source image is not hallucinated by a text prompt. The timeline's
    source-clock trim end is authoritative, and output is a disposable PNG.
    """
    scenes = episode.get("scenes") or []
    index = next((i for i, shot in enumerate(scenes) if shot.get("id") == scene_id), -1)
    if index < 0:
        raise ValueError("Current shot is not part of this episode")
    if index == 0:
        raise ValueError(
            "First shot has no previous frame. Use an approved image reference "
            "or choose a workflow without {{PREVIOUS_FRAME}} for the opening shot")
    previous = scenes[index-1]
    selected_id = str(previous.get("selected_take_id") or "")
    take = next((item for item in previous.get("takes") or []
                 if item.get("id") == selected_id), None)
    if take and take.get("rights") == "generated_unverified" and not take.get("approved_for_use"):
        raise ValueError("Previous generated-video take must be reviewed and approved before continuity conditioning")
    source = quality.normalized_path(previous.get("clip"))
    if not source or not source.is_file() or source.suffix.lower() not in quality.VIDEO_EXTENSIONS:
        raise ValueError("Previous scene must have playable source footage for last-frame continuity")
    info = quality.media_info(source)
    if not info["has_video"]:
        raise ValueError("Previous scene source has no video frames")
    # Source-clock trim end may be an explicitly edited value, not source EOF.
    import timeline_engine
    start, finish = timeline_engine.source_window(previous, info["duration"])
    timecode = max(start, finish - min(.125, (finish-start)/2))
    working_dir.mkdir(parents=True, exist_ok=True)
    target = working_dir / ("continuity_" + uuid.uuid4().hex[:12] + ".png")
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-ss", f"{timecode:.6f}", "-i", str(source), "-frames:v", "1", str(target)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if result.returncode or not target.is_file():
        target.unlink(missing_ok=True)
        raise RuntimeError(
            "FFmpeg could not extract a previous-shot continuity frame: " +
            (result.stderr or "")[-600:])
    quality.validate_image(target)
    return target, {
        "source_scene_id": previous.get("id"), "source_clip": str(source),
        "source_time_seconds": round(timecode, 4), "requires_human_identity_review": True,
    }


def previous_visual_reference(series: dict, episode: dict, scene_id: str,
                              working_dir: Path) -> tuple[Path, dict, bool]:
    """Use previous approved moving frame, or previous pinned still if no video.

    Returns path, provenance, and whether the caller should delete that path.
    No synthetic image is generated by this fallback: the actual approved
    series ingredient is passed to a real image-conditioning node.
    """
    try:
        path, provenance = previous_approved_frame(
            series, episode, scene_id, working_dir)
        return path, provenance, True
    except ValueError as exc:
        # Only fallback for a previous shot lacking video. Do not bypass
        # missing approvals, damaged media or other hard validation failures.
        if "Previous scene must have playable source footage" not in str(exc):
            raise
        scenes = episode.get("scenes") or []
        index = next((i for i, shot in enumerate(scenes)
                      if shot.get("id") == scene_id), -1)
        if index < 1:
            raise
        previous = scenes[index-1]
        ref = quality.reference_image_for_scene(series, previous)
        if not ref:
            raise ValueError(
                "Previous scene has neither approved reference still nor moving footage")
        quality.validate_image(ref)
        return ref, {
            "source_scene_id": previous.get("id"),
            "source_asset": str(ref),
            "kind": "approved_previous_still",
            "requires_human_identity_review": True
        }, False
