"""Local, versioned music library with user-owned/permissioned audio imports.

Streaming uploads stay on the local machine. Files are kept independently of
individual episode edits, so switching soundtrack never deletes an old track.
"""
from __future__ import annotations
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import studio_quality as quality
from take_workspace import file_digest, USER_RIGHTS


def import_track(root: Path, series: dict, source: Path, *,
                 title: str, rights: str, notes: str = "", move: bool = False) -> dict:
    if rights not in USER_RIGHTS:
        raise ValueError("Confirm original, licensed, permitted, or verified public-domain music rights")
    source = source.expanduser().resolve()
    if not source.is_file() or source.suffix.lower() not in quality.AUDIO_EXTENSIONS:
        raise ValueError("Choose an existing WAV, MP3, M4A, FLAC, OGG, OPUS or AAC file")
    info = quality.media_info(source)
    if not info["has_audio"] or info["duration"] < 0.1:
        raise ValueError("Music file must contain decodable audio")
    title = str(title or source.stem).strip()[:150]
    if not title:
        raise ValueError("Give the audio track a title")
    track_id = uuid.uuid4().hex[:16]
    folder = root / "music" / series["id"] / track_id
    folder.mkdir(parents=True, exist_ok=False)
    dest = folder / ("track" + source.suffix.lower())
    try:
        if move:
            shutil.move(str(source), str(dest))
        else:
            if shutil.disk_usage(folder).free < source.stat().st_size + 64 * 1024 * 1024:
                raise ValueError("Not enough space to import music and preserve original file")
            intermediate = folder / "import.part"
            shutil.copy2(source, intermediate)
            os.replace(intermediate, dest)
        saved = quality.media_info(dest)
        if not saved["has_audio"] or saved["duration"] <= 0:
            raise ValueError("Imported music contains no audio after copying")
        track = {
            "id": track_id, "title": title, "path": str(dest),
            "sha256": file_digest(dest), "duration": round(saved["duration"], 3),
            "bytes": dest.stat().st_size, "rights": rights,
            "notes": str(notes)[:1500],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        series.setdefault("music_library", []).append(track)
        return track
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise


def get_track(series: dict, track_id: str) -> dict:
    for item in series.get("music_library") or []:
        if item.get("id") == track_id:
            return item
    raise ValueError("Music track not found in this series")


def choose_track(series: dict, episode: dict, track_id: str) -> dict:
    track = get_track(series, track_id)
    media = Path(track["path"])
    if not media.is_file() or file_digest(media) != track["sha256"]:
        raise ValueError("Music file is missing or altered; import a fresh version")
    episode["soundtrack"] = str(media)
    episode["soundtrack_track_id"] = track_id
    episode["soundtrack_rights_confirmed"] = True
    return track
