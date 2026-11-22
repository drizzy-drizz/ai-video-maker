"""Real, non-destructive editorial timeline for imported or AI-generated footage.

The timeline stores ONLY edit decisions in each scene; it never rewrites the
original source clip or licensed assets. ffprobe is the authority for durations.
Consecutive cuts are concatenated efficiently. Optional video xfade transitions
are paired with matching audio acrossfades and exact timeline offsets.

Manual captions stay shot-relative; outgoing and incoming half-transition
regions are reserved for one caption lane, rather than showing both simultaneously.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Any

import studio_quality as quality

TRANSITIONS = {"cut", "fade", "wipeleft", "slideleft"}
MIN_SHOT_SECONDS = 0.35
MIN_TRANSITION = 0.10
MAX_TRANSITION = 1.50


def finite(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} must be a number of seconds") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def source_window(scene: dict, source_duration: float) -> tuple[float, float]:
    if source_duration < MIN_SHOT_SECONDS:
        raise ValueError("Source video is shorter than a usable shot")
    raw_start = scene.get("trim_start_seconds")
    raw_end = scene.get("trim_end_seconds")
    start = 0.0 if raw_start in (None, "") else finite(raw_start, "Trim in")
    end = source_duration if raw_end in (None, "") else finite(raw_end, "Trim out")
    if start < 0 or end > source_duration + 0.035:
        raise ValueError(f"Trim interval {start:.2f}–{end:.2f}s exceeds source (0–{source_duration:.2f}s)")
    end = min(source_duration, end)
    if end - start < MIN_SHOT_SECONDS:
        raise ValueError(f"Trimmed shot must be at least {MIN_SHOT_SECONDS:.2f}s")
    return start, end


def transition_data(scene: dict, outgoing: float, incoming: float) -> tuple[str, float]:
    effect = str(scene.get("transition_to_next") or "cut")
    if effect not in TRANSITIONS:
        raise ValueError("Transition must be cut, fade, wipeleft or slideleft")
    if effect == "cut":
        return "cut", 0.0
    duration = finite(scene.get("transition_duration_seconds") or 0.35, "Transition duration")
    if not MIN_TRANSITION <= duration <= MAX_TRANSITION:
        raise ValueError(f"Crossfade must be {MIN_TRANSITION:.2f}–{MAX_TRANSITION:.2f}s")
    if duration > min(outgoing, incoming) * 0.45:
        raise ValueError("Crossfade exceeds 45% of an adjacent trimmed shot")
    return effect, duration


def with_durations(entries: list[dict], durations: list[float]) -> dict:
    """Resolve exact episode starts and caption windows from REAL encoded durations."""
    if len(entries) != len(durations):
        raise ValueError("Timeline media count mismatch")
    resolved = [dict(item) for item in entries]
    for index, duration in enumerate(durations):
        if not math.isfinite(duration) or duration < MIN_SHOT_SECONDS - 0.025:
            raise ValueError(f"Encoded scene {index+1} has invalid duration")
        resolved[index]["duration"] = float(duration)
    boundaries = []
    for index in range(len(resolved)-1):
        effect, overlap = transition_data(
            resolved[index], resolved[index]["duration"], resolved[index+1]["duration"])
        resolved[index]["transition_to_next"] = effect
        resolved[index]["transition_duration_seconds"] = overlap
        boundaries.append({"type": effect, "duration": overlap,
                           "from_scene": resolved[index]["scene_id"],
                           "to_scene": resolved[index+1]["scene_id"]})
    if resolved:
        resolved[-1]["transition_to_next"] = "cut"
        resolved[-1]["transition_duration_seconds"] = 0.0
    cursor = 0.0
    for index, item in enumerate(resolved):
        incoming = boundaries[index-1]["duration"] if index else 0.0
        outgoing = boundaries[index]["duration"] if index < len(boundaries) else 0.0
        item["start"] = round(cursor, 6)
        item["end"] = round(cursor + item["duration"], 6)
        item["previous_overlap"] = incoming
        item["next_overlap"] = outgoing
        item["caption_min"] = incoming / 2
        item["caption_max"] = item["duration"] - outgoing / 2
        if item["caption_max"] <= item["caption_min"] + 0.08:
            raise ValueError("Transition leaves no usable subtitle window")
        cursor += item["duration"] - outgoing
    return {"entries": resolved, "boundaries": boundaries, "total_seconds": round(cursor, 6),
            "crossfades": sum(b["type"] != "cut" for b in boundaries),
            "note": "Editor decisions are non-destructive; frames and sound use FFmpeg at export"}


def plan_episode(series: dict, episode: dict) -> dict:
    scenes = episode.get("scenes") or []
    if not scenes:
        raise ValueError("Cannot edit an episode with no shots")
    entries = []
    durations = []
    for index, scene in enumerate(scenes, 1):
        source = quality.normalized_path(scene.get("clip"))
        if not source or not source.is_file() or source.suffix.lower() not in quality.VIDEO_EXTENSIONS:
            raise ValueError(f"Shot {index}: missing supported source MP4/MOV/MKV/WebM")
        try:
            info = quality.media_info(source)
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            raise ValueError(f"Shot {index}: invalid video: {str(exc)[:180]}") from exc
        if not info["has_video"]:
            raise ValueError(f"Shot {index}: source has no real video frames")
        trim_start, trim_end = source_window(scene, info["duration"])
        duration = trim_end-trim_start
        entries.append({
            "scene_id": scene.get("id") or f"shot-{index}", "number": index, "clip": str(source),
            "source_duration": info["duration"], "source_start": round(trim_start, 6),
            "source_end": round(trim_end, 6),
            "transition_to_next": scene.get("transition_to_next") or "cut",
            "transition_duration_seconds": scene.get("transition_duration_seconds") or 0.35,
            "source_audio": info["has_audio"],
        })
        durations.append(duration)
    result = with_durations(entries, durations)
    # Dialogue is never allowed to spill into a transition; delay incoming
    # narration until the crossfade completes so its leading words are audible.
    for index, (item, scene) in enumerate(zip(result["entries"], scenes), 1):
        from caption_engine import validate_manual_cues
        voice = quality.normalized_path(scene.get("narration"))
        if voice:
            if not voice.is_file() or voice.suffix.lower() not in quality.AUDIO_EXTENSIONS:
                raise ValueError(f"Shot {index}: narration file is missing/unsupported")
            info = quality.media_info(voice)
            if not info["has_audio"]:
                raise ValueError(f"Shot {index}: narration has no valid audio")
            capacity = (item["duration"]-item["previous_overlap"]-item["next_overlap"])
            if info["duration"] > capacity+0.06:
                raise ValueError(
                    f"Shot {index}: {info['duration']:.2f}s narration cannot fit in "
                    f"{capacity:.2f}s of dialogue-safe time. Shorten voice, extend trim, or remove transition.")
            item["narration_duration"] = info["duration"]
        cues = scene.get("caption_cues") or []
        if cues:
            for cue in validate_manual_cues(cues, item["duration"]):
                if (cue["start"] < item["caption_min"]-0.001 or
                        cue["end"] > item["caption_max"]+0.001):
                    raise ValueError(
                        f"Shot {index}: a manually timed subtitle extends into a transition. "
                        "Move the caption to the solo region or shorten the transition.")
    result["format"] = series.get("format") or "9:16"
    return result


def concat_cuts(paths: list[Path], dest: Path) -> Path:
    if not paths:
        raise ValueError("No footage to join")
    if len(paths) == 1:
        import shutil
        shutil.copy2(paths[0], dest)
        return dest
    manifest = dest.with_suffix(".txt")
    # All names are normalized, owned and simple (ASCII-generated) within work dir.
    if any(path.parent != dest.parent or "'" in path.name for path in paths):
        raise ValueError("Normalized video paths must live in same safe render directory")
    manifest.write_text("".join(f"file '{path.name}'\n" for path in paths), encoding="utf-8")
    run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(manifest),
                "-c", "copy", "-movflags", "+faststart", str(dest)])
    return dest


def run_ffmpeg(args: list[str]) -> None:
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"] + args
    result = subprocess.run(command, text=True, capture_output=True, timeout=3600)
    if result.returncode:
        raise RuntimeError("Timeline FFmpeg failed: " + (result.stderr or result.stdout)[-2000:])


def assemble_segments(files: list[Path], plan: dict, folder: Path) -> Path:
    """Full frame/video AND audio transition pipeline with bounded intermediates."""
    if len(files) != len(plan["entries"]):
        raise ValueError("Timeline segment count mismatch")
    boundaries = plan["boundaries"]
    groups: list[list[Path]] = [[files[0]]]
    effects: list[dict] = []
    for i, edge in enumerate(boundaries):
        if edge["type"] == "cut":
            groups[-1].append(files[i+1])
        else:
            effects.append(edge)
            groups.append([files[i+1]])
    result_groups = []
    for index, group in enumerate(groups):
        output = folder / f"timeline-group-{index:05d}.mp4"
        result_groups.append(concat_cuts(group, output))
    left = result_groups[0]
    if not effects:
        return left
    for index, (edge, right) in enumerate(zip(effects, result_groups[1:])):
        overlap = edge["duration"]
        left_duration = quality.media_info(left)["duration"]
        right_duration = quality.media_info(right)["duration"]
        if left_duration <= overlap or right_duration <= overlap:
            raise ValueError("FFmpeg crossfade duration exceeds encoded media duration")
        offset = left_duration - overlap
        dest = folder / f"timeline-crossfade-{index:05d}.mp4"
        vf = (
            "[0:v:0]settb=AVTB,setpts=PTS-STARTPTS,fps=24,format=yuv420p[v0];"
            "[1:v:0]settb=AVTB,setpts=PTS-STARTPTS,fps=24,format=yuv420p[v1];"
            f"[v0][v1]xfade=transition={edge['type']}:duration={overlap:.6f}:"
            f"offset={offset:.6f},format=yuv420p[v]"
        )
        af = (f"[0:a:0]aresample=48000,asetpts=PTS-STARTPTS[a0];"
              f"[1:a:0]aresample=48000,asetpts=PTS-STARTPTS[a1];"
              f"[a0][a1]acrossfade=d={overlap:.6f}:c1=tri:c2=tri[a]")
        run_ffmpeg(["-i", str(left), "-i", str(right),
                    "-filter_complex", vf + ";" + af,
                    "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "21", "-preset", "veryfast",
                    "-pix_fmt", "yuv420p", "-r", "24",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
                    "-movflags", "+faststart", str(dest)])
        left = dest
    return left
