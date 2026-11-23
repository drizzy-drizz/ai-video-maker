"""Shot-edit operations: non-destructive duplicate, precise split, archive and restore.

All operations mutate a COPY of the caller's project; callers save atomically
only after validation. Original source story, real footage, approved image assets,
generated audio and take history never get deleted by these edits.
"""
from __future__ import annotations

import copy
import math
import uuid
from datetime import datetime, timezone

import studio_quality as quality
import caption_engine
import timeline_engine


def clock() -> str:
    return datetime.now(timezone.utc).isoformat()


def ident() -> str:
    return uuid.uuid4().hex[:12]


def scene_at(episode: dict, scene_id: str) -> tuple[int, dict]:
    for index, scene in enumerate(episode.get("scenes") or []):
        if scene.get("id") == scene_id:
            return index, scene
    raise ValueError("Shot ID not found in episode")


def renumber(episode: dict) -> None:
    for i, scene in enumerate(episode.get("scenes") or [], 1):
        scene["number"] = i


def invalidate(episode: dict) -> None:
    # Keep last playable render_path for user comparison/recovery; make its
    # staleness explicit and never claim that it matches current decisions.
    episode["status"] = "edited_needs_new_render"
    episode["last_edit_at"] = clock()


def duplicate(episode: dict, scene_id: str) -> dict:
    index, current = scene_at(episode, scene_id)
    clone = copy.deepcopy(current)
    clone["id"] = ident()
    clone["edit_note"] = "Duplicated shot — independent edit decisions"
    # Clip/take path is a read-only reference to original media; editing the
    # clone only changes its own decisions. Neither asset is overwritten.
    episode["scenes"].insert(index + 1, clone)
    renumber(episode)
    invalidate(episode)
    return {"operation": "duplicate", "new_scene_id": clone["id"],
            "scene_count": len(episode["scenes"])}


def split(episode: dict, scene_id: str, *, at_seconds: float,
          after_word: int) -> dict:
    index, original = scene_at(episode, scene_id)
    script = str(original.get("script") or "")
    words = script.split()
    if len(words) < 2:
        raise ValueError("Shot needs at least two script words to split cleanly")
    try:
        split_word = int(after_word)
        relative = float(at_seconds)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Choose a valid split position in video seconds and script words") from exc
    if isinstance(after_word, bool) or split_word != after_word or not 1 <= split_word < len(words):
        raise ValueError("Split must preserve text on both sides of a whole-word boundary")
    if not math.isfinite(relative) or relative <= 0:
        raise ValueError("Split offset must be a positive finite number")
    if original.get("narration"):
        raise ValueError(
            "This shot has narration. Split/export the voice into two independent files first "
            "so neither spoken line gets silently truncated or duplicated.")
    first = copy.deepcopy(original)
    second = copy.deepcopy(original)
    second["id"] = ident()
    first["script"] = " ".join(words[:split_word])
    second["script"] = " ".join(words[split_word:])
    # Source text coverage is guaranteed even if formatting normalization differs.
    if (first["script"] + " " + second["script"]).split() != words:
        raise ValueError("Split would lose original dialogue")
    source = quality.normalized_path(original.get("clip"))
    if source:
        if not source.is_file():
            raise ValueError("Cannot split a shot with missing source footage")
        info = quality.media_info(source)
        if not info["has_video"]:
            raise ValueError("Shot source contains no video")
        start, end = timeline_engine.source_window(original, info["duration"])
        full = end-start
        if relative < timeline_engine.MIN_SHOT_SECONDS or full-relative < timeline_engine.MIN_SHOT_SECONDS:
            raise ValueError("Both split clips must be at least 0.35 seconds long")
        first["trim_start_seconds"] = start
        first["trim_end_seconds"] = start + relative
        second["trim_start_seconds"] = start + relative
        second["trim_end_seconds"] = end
        # A paired image animatic uses the same narrative beat lengths, instead
        # of accidentally duplicating the original full shot duration twice.
        first["duration_hint_seconds"] = round(relative, 3)
        second["duration_hint_seconds"] = round(full-relative, 3)
    else:
        full = float(original.get("duration_hint_seconds") or 6.0)
        if not math.isfinite(full) or full <= 0:
            raise ValueError("Storyboard shot has invalid duration")
        if relative < 2.0 or full-relative < 2.0:
            raise ValueError("Image storyboard splits require at least 2 seconds per side")
        first["duration_hint_seconds"] = round(relative, 3)
        second["duration_hint_seconds"] = round(full-relative, 3)
    cues = original.get("caption_cues") or []
    if cues:
        parsed = caption_engine.validate_manual_cues(cues, full)
        one, two = [], []
        for cue in parsed:
            if cue["end"] <= relative + .0005:
                one.append(cue)
            elif cue["start"] >= relative - .0005:
                two.append({
                    "start": round(cue["start"]-relative, 4),
                    "end": round(cue["end"]-relative, 4),
                    "text": cue["text"]
                })
            else:
                raise ValueError(
                    "A manually timed subtitle crosses the split point. "
                    "Move its boundary first so no caption is silently discarded.")
        first["caption_cues"] = one
        second["caption_cues"] = two
    # Preserve original outgoing transition on the second half. The new
    # internal boundary is a hard cut; no unrequested editorial smoothing.
    first["transition_to_next"] = "cut"
    first["transition_duration_seconds"] = 0
    # AI prompt and pinned image references remain editable independently.
    first["beat_position"] = "development" if original.get("beat_position") == "ending" else original.get("beat_position", "development")
    second["beat_position"] = original.get("beat_position", "development")
    second["edit_note"] = "Source-preserving split from " + scene_id
    episode["scenes"][index:index + 1] = [first, second]
    renumber(episode)
    invalidate(episode)
    return {"operation": "split", "first_scene_id": first.get("id"),
            "second_scene_id": second["id"], "scene_count": len(episode["scenes"])}


def archive(episode: dict, scene_id: str) -> dict:
    if len(episode.get("scenes") or []) <= 1:
        raise ValueError("Keep at least one active shot per episode")
    index, original = scene_at(episode, scene_id)
    moved = copy.deepcopy(original)
    moved["_archived_from_index"] = index
    moved["_archived_at"] = clock()
    episode.setdefault("archived_scenes", []).append(moved)
    episode["scenes"].pop(index)
    renumber(episode)
    invalidate(episode)
    return {"operation": "archive", "scene_id": scene_id,
            "archived_count": len(episode["archived_scenes"]),
            "scene_count": len(episode["scenes"])}


def restore(episode: dict, scene_id: str) -> dict:
    archived = episode.get("archived_scenes") or []
    for pos, item in enumerate(archived):
        if item.get("id") == scene_id:
            scene = copy.deepcopy(item)
            index = max(0, min(len(episode["scenes"]), int(scene.pop("_archived_from_index", len(episode["scenes"])))))
            scene.pop("_archived_at", None)
            episode["scenes"].insert(index, scene)
            archived.pop(pos)
            renumber(episode)
            invalidate(episode)
            return {"operation": "restore", "scene_id": scene_id,
                    "scene_count": len(episode["scenes"])}
    raise ValueError("Archived shot not found")
