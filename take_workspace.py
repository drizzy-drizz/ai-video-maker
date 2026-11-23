"""Immutable moving-footage takes: import, register AI output, select/approve versions.

No destructive overwrite: every take is a real, independent local video file
with checksum, duration, dimensions, rights/provenance and stable ID. Imported
sources are copied; local ComfyUI output can be moved into versioned storage.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import studio_quality as quality

USER_RIGHTS = {"original", "licensed", "permission", "public_domain"}
ALL_RIGHTS = USER_RIGHTS | {"generated_unverified"}


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def take_by_id(scene: dict, take_id: str) -> dict:
    for take in scene.get("takes") or []:
        if take.get("id") == take_id:
            return take
    raise ValueError("Video take not found in this scene")


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_video(path: Path) -> dict:
    if path.suffix.lower() not in quality.VIDEO_EXTENSIONS or not path.is_file():
        raise ValueError("Use an existing MP4, MOV, MKV or WebM file")
    info = quality.media_info(path)
    if not info["has_video"] or info["duration"] < .35 or not info["width"] or not info["height"]:
        raise ValueError("Video take must have decodable moving footage and at least 0.35 seconds")
    return info


def add_take(root: Path, series_id: str, episode_id: str, scene: dict,
             source: Path, *, title: str, rights: str, origin: str = "import",
             notes: str = "", provenance: dict | None = None,
             select: bool = True, move: bool = False) -> dict:
    if rights not in ALL_RIGHTS or (rights == "generated_unverified" and origin != "ComfyUI"):
        raise ValueError("Confirm rights to imported footage, or use generated-unverified only for ComfyUI output")
    title = str(title).strip()[:150]
    if not title:
        raise ValueError("Video take needs a title")
    source = source.expanduser().resolve()
    meta = validate_video(source)
    take_id = uuid.uuid4().hex[:16]
    takes = scene.setdefault("takes", [])
    version = max((int(item.get("version") or 0) for item in takes), default=0) + 1
    target_folder = root / "takes" / series_id / episode_id / scene["id"] / take_id
    target_folder.mkdir(parents=True, exist_ok=False)
    target = target_folder / ("footage" + source.suffix.lower())
    try:
        if move:
            shutil.move(str(source), str(target))
        else:
            if shutil.disk_usage(target_folder).free <= source.stat().st_size + 64 * 1024 * 1024:
                raise ValueError("Not enough free disk space to import this footage without deleting the original")
            staging = target_folder / "importing.part"
            shutil.copyfile(source, staging)
            os.replace(staging, target)
        saved = validate_video(target)
        sha = file_digest(target)
        version_meta = {
            "id": take_id, "version": version, "title": title,
            "path": str(target), "sha256": sha, "bytes": target.stat().st_size,
            "rights": rights, "origin": origin, "notes": str(notes)[:1500],
            "approved_for_use": rights != "generated_unverified",
            "approval_at": timestamp() if rights != "generated_unverified" else None,
            "provenance": provenance or {},
            "duration": round(saved["duration"], 3),
            "width": saved["width"], "height": saved["height"],
            "has_audio": saved["has_audio"],
            "created_at": timestamp()
        }
        takes.append(version_meta)
        if select:
            activate_take(scene, take_id, trusted=True)
        return version_meta
    except Exception:
        shutil.rmtree(target_folder, ignore_errors=True)
        raise


def activate_take(scene: dict, take_id: str, *, trusted: bool = False) -> dict:
    selected = take_by_id(scene, take_id)
    path = Path(selected["path"])
    if not trusted:
        validate_video(path)
        if file_digest(path) != selected["sha256"]:
            raise ValueError("Video take checksum changed; import a new version instead")
    previous_start = scene.get("trim_start_seconds")
    previous_end = scene.get("trim_end_seconds")
    try:
        begin = float(previous_start or 0)
        finish = float(previous_end) if previous_end not in (None, "") else float(selected["duration"])
        valid = (begin >= 0 and finish > begin + 0.35 and
                 finish <= float(selected["duration"]) + 0.035)
    except (ValueError, TypeError, OverflowError):
        valid = False
    scene["selected_take_id"] = take_id
    scene["clip"] = selected["path"]
    if not valid:
        scene["trim_start_seconds"] = 0.0
        scene["trim_end_seconds"] = ""
        scene["take_selection_notice"] = (
            "Previous trim was outside this take's duration; trim reset to full take. "
            "Old edit decisions remain available via Project History.")
    else:
        scene["take_selection_notice"] = (
            "Existing trim positions preserved for this take; review the content in source preview.")
    scene["provenance"] = selected.get("provenance") or {
        "backend": selected["origin"], "take_id": take_id
    }
    return selected


def list_takes(scene: dict) -> list[dict]:
    return [
        {**item, "selected": scene.get("selected_take_id") == item.get("id")}
        for item in (scene.get("takes") or [])
    ]
