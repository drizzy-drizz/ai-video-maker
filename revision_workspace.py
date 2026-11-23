"""Bounded, durable undo/recovery snapshots for local series JSON files.

Snapshots store only project edit decisions, never duplicate large media files.
Every previously saved revision can be restored while retaining the current
revision as a new recovery point. Entries are content-addressed to avoid
wasting space on no-op saves; retention is bounded for normal desktop use.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

MAX_HISTORY = 60


def normalized(doc: dict) -> bytes:
    current = dict(doc)
    current.pop("updated_at", None)
    return json.dumps(current, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def history_folder(data_root: Path, project_id: str) -> Path:
    return data_root / "revisions" / project_id


def capture(data_root: Path, project_id: str, before: dict, after: dict) -> str | None:
    if normalized(before) == normalized(after):
        return None
    folder = history_folder(data_root, project_id)
    folder.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(normalized(before)).hexdigest()
    # Prevent duplicate backups on repeated revisions/no-op commits.
    latest = sorted(folder.glob("*.json"), key=lambda file: file.stat().st_mtime_ns, reverse=True)
    if latest:
        try:
            previous = json.loads(latest[0].read_text(encoding="utf-8"))
            if hashlib.sha256(normalized(previous["project"])).hexdigest() == digest:
                return None
        except (ValueError, OSError, KeyError):
            pass
    rid = uuid.uuid4().hex[:24]
    snap = {
        "id": rid, "created_at": datetime.now(timezone.utc).isoformat(),
        "sha256": digest, "title": str(before.get("title") or "")[:150],
        "episode_count": len(before.get("episodes") or []),
        "project": before
    }
    name = folder / (rid + ".json")
    # Write temp then atomically rename: crash cannot create half-written backup.
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=folder, suffix=".tmp",
                                     delete=False) as output:
        tmp_name = output.name
        json.dump(snap, output, ensure_ascii=False)
    os.replace(tmp_name, name)
    all_files = sorted(folder.glob("*.json"), key=lambda file: file.stat().st_mtime_ns, reverse=True)
    for outdated in all_files[MAX_HISTORY:]:
        outdated.unlink(missing_ok=True)
    return rid


def list_revisions(root: Path, project_id: str) -> list[dict]:
    folder = history_folder(root, project_id)
    files = sorted(folder.glob("*.json"), key=lambda f: f.stat().st_mtime_ns, reverse=True)
    rows = []
    for f in files:
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
            rows.append({
                "id": doc["id"], "created_at": doc["created_at"],
                "title": doc["title"], "episode_count": doc["episode_count"],
                "sha256": doc["sha256"]
            })
        except (OSError, ValueError, KeyError):
            continue
    return rows


def load_revision(root: Path, project_id: str, revision_id: str) -> dict:
    if (not isinstance(revision_id, str) or len(revision_id) != 24 or
            any(c not in "0123456789abcdef" for c in revision_id)):
        raise ValueError("Invalid revision identifier")
    path = history_folder(root, project_id) / (revision_id + ".json")
    if not path.is_file():
        raise FileNotFoundError("Revision does not exist")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("id") != revision_id or doc.get("project", {}).get("id") != project_id:
        raise ValueError("Revision does not belong to the requested series")
    data = doc["project"]
    if hashlib.sha256(normalized(data)).hexdigest() != doc.get("sha256"):
        raise ValueError("Revision checksum mismatch; refusing damaged backup")
    return data
