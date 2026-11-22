"""Immutable, user-licensed image ingredient library for episodic filmmaking.

Every imported image is copied into managed project storage. 'Replacing' an asset
creates a NEW immutable version, keeping all existing shot references pinned.
No cloud requests, no account, no inference provider.
"""
from __future__ import annotations
import hashlib
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from studio_quality import validate_image

RIGHTS = {"original", "licensed", "permission", "public_domain"}
MAX_TOTAL_ASSETS = 10000


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def get_asset(series: dict, asset_id: str) -> dict | None:
    if not asset_id:
        return None
    for asset in series.get("assets") or []:
        if asset.get("id") == asset_id:
            return asset
    return None


def add_image_asset(data_root: Path, series: dict, source: str, *, title: str,
                    rights: str, credit: str = "", replace_asset_id: str = "") -> dict:
    if rights not in RIGHTS:
        raise ValueError("Choose verified image rights: original, licensed, permission or public_domain")
    title = title.strip()
    if not title or len(title) > 120:
        raise ValueError("Image title must be 1–120 characters")
    assets = series.setdefault("assets", [])
    if len(assets) >= MAX_TOTAL_ASSETS:
        raise ValueError("Image library safety limit reached")
    parent = get_asset(series, replace_asset_id) if replace_asset_id else None
    if replace_asset_id and parent is None:
        raise ValueError("Replacement image ID not found")
    source_path = Path(source).expanduser().resolve()
    validate_image(source_path)
    file_id = uuid.uuid4().hex[:16]
    directory = data_root / "assets" / series["id"] / file_id
    directory.mkdir(parents=True, exist_ok=False)
    destination = directory / ("image" + source_path.suffix.lower())
    # Stage copied files atomically; verify copied content matches input.
    digest = hashlib.sha256()
    temporary = directory / "incoming.part"
    try:
        with source_path.open("rb") as reader, temporary.open("wb") as writer:
            for chunk in iter(lambda: reader.read(1024 * 1024), b""):
                digest.update(chunk)
                writer.write(chunk)
        os.replace(temporary, destination)
        validate_image(destination)
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    new_version = (int(parent.get("version", 1)) + 1) if parent else 1
    meta = {
        "id": file_id, "version": new_version,
        "parent_asset_id": parent["id"] if parent else None,
        "title": title, "path": str(destination), "sha256": digest.hexdigest(),
        "rights": rights, "credit": credit.strip()[:1000], "created_at": timestamp()
    }
    assets.append(meta)
    return meta


def resolve_image(series: dict, scene: dict) -> Path | None:
    """Pinned scene asset, user-provided image path, or pinned character asset."""
    chosen_id = str(scene.get("reference_asset_id") or "")
    if chosen_id:
        asset = get_asset(series, chosen_id)
        if not asset:
            raise ValueError("Scene references a missing image library asset: " + chosen_id)
        selected = Path(asset["path"])
        validate_image(selected)
        return selected
    # Legacy explicit image path takes precedence over inherited character image.
    path = str(scene.get("reference_image") or "").strip()
    if path:
        selected = Path(path).expanduser().resolve()
        validate_image(selected)
        return selected
    from studio_quality import referenced_characters
    for person in referenced_characters(series, scene):
        pinned = str(person.get("reference_asset_id") or "")
        if pinned:
            asset = get_asset(series, pinned)
            if not asset:
                raise ValueError("Character references a missing library asset: " + pinned)
            selected = Path(asset["path"])
            validate_image(selected)
            return selected
        legacy = str(person.get("reference_image") or "").strip()
        if legacy:
            selected = Path(legacy).expanduser().resolve()
            validate_image(selected)
            return selected
    return None


def verify_asset(series: dict, asset_id: str) -> dict:
    asset = get_asset(series, asset_id)
    if not asset:
        raise ValueError("Asset not found")
    image_path = Path(asset["path"])
    validate_image(image_path)
    digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
    return {"id": asset_id, "valid": digest == asset["sha256"],
            "reason": "" if digest == asset["sha256"] else "Stored file hash differs; possible modification"}
