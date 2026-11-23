"""Portable, rights-preserving project archive for an entire episodic workspace.

Exports a single ZIP with JSON timeline/canon, actual referenced footage,
generated takes, stills, voices, licensed music and previous output artifacts.
Imports into a NEW series ID with checksummed, path-safe, privately owned files.
This is backup/transfer, not rendering or permission to redistribute assets.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

FORMAT = "AI-Video-Maker-project-v1"
PATH_FIELDS = {
    "path", "clip", "narration", "reference_image", "soundtrack",
    "render_path", "captions_path", "quality_report_path",
    "animatic_path", "animatic_captions_path", "animatic_quality_path", "wav",
}
MANIFEST_LIMIT = 8 * 1024 * 1024


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(2 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def referenced_paths(item, label: str = ""):
    if isinstance(item, dict):
        for key, value in item.items():
            if key in PATH_FIELDS and isinstance(value, str) and value.strip():
                yield key, value
            else:
                yield from referenced_paths(value, key)
    elif isinstance(item, list):
        for value in item:
            yield from referenced_paths(value, label)


def map_paths(value, mapping: dict[str, str]):
    if isinstance(value, dict):
        return {
            key: mapping.get(v, v) if key in PATH_FIELDS and isinstance(v, str)
            else map_paths(v, mapping)
            for key, v in value.items()
        }
    if isinstance(value, list):
        return [map_paths(item, mapping) for item in value]
    return value


def store_rel(root: Path, original: Path, series_id: str, sha: str) -> str:
    for family in ("takes", "assets", "narrations", "exports", "media", "animatic"):
        base = (root / family / series_id).resolve()
        if original.is_relative_to(base):
            original_subpath = original.relative_to(base)
            # Keep managed path structure. These segments come from existing
            # local project files, but normalizing still prevents path traversal.
            return str(Path(family) / "@SERIES@" / original_subpath).replace("\\", "/")
    return "imported-media/@SERIES@/" + sha + original.suffix.lower()


def export_package(root: Path, project: dict, progress=None) -> Path:
    series_id = str(project["id"])
    archive_dir = root / "backups" / series_id
    archive_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    missing = []
    for field, value in referenced_paths(project):
        selected = Path(value).expanduser().resolve()
        if selected.is_file():
            files[str(selected)] = selected
        else:
            missing.append(field + ": " + value[:180])
    if missing:
        raise ValueError(
            "Portable backup cannot include missing project media. "
            "Repair these references before export: " + "; ".join(missing[:10]))
    required = sum(p.stat().st_size for p in files.values())
    if shutil.disk_usage(archive_dir).free < required + 64 * 1024 * 1024:
        raise ValueError("Not enough disk space to create a complete portable project archive")
    path_map = {}
    media = []
    visited = set()
    total = len(files)
    for i, source in enumerate(files.values(), 1):
        if progress:
            progress(f"Hashing linked media {i}/{total}: {source.name[:70]}")
        sha = digest(source)
        name = "media/" + sha + source.suffix.lower()
        token = "package://" + name
        path_map[str(source)] = token
        if name in visited:
            continue
        visited.add(name)
        media.append({
            "archive_path": name, "sha256": sha, "bytes": source.stat().st_size,
            "store_relative": store_rel(root, source, series_id, sha),
            "_source": str(source)
        })
    project_copy = map_paths(copy.deepcopy(project), path_map)
    for item in media:
        # Absolute source paths are never exposed in the exported manifest.
        item.pop("_source", None)
    manifest = {
        "format": FORMAT, "exported_at": now(),
        "source_title": project.get("title", ""),
        "files": media, "project": project_copy,
        "note": "External model weights and software executables are NOT bundled. "
                "Asset rights remain the author's responsibility."
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(manifest_bytes) > MANIFEST_LIMIT:
        raise ValueError("Project metadata is too large for portable manifest")
    staged = archive_dir / ("bundle-" + uuid.uuid4().hex[:12] + ".part")
    finished = archive_dir / (series_id + "-" + uuid.uuid4().hex[:12] + ".aivm.zip")
    try:
        with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zip_out:
            zip_out.writestr("manifest.json", manifest_bytes)
            # Refuse repeated archive name with incompatible sources.
            included = set()
            for i, source in enumerate(files.values(), 1):
                token = path_map[str(source)][len("package://"):]
                if token in included:
                    continue
                included.add(token)
                if progress:
                    progress(f"Packing source file {i}/{total}: {source.name[:70]}")
                zip_out.write(source, arcname=token)
        os.replace(staged, finished)
        return finished
    finally:
        staged.unlink(missing_ok=True)


def import_package(root: Path, archive: Path, progress=None) -> dict:
    if not zipfile.is_zipfile(archive):
        raise ValueError("Not an AI Video Maker ZIP archive")
    series_id = uuid.uuid4().hex[:12]
    with zipfile.ZipFile(archive) as pack:
        names = pack.namelist()
        if "manifest.json" not in names or len(names) != len(set(names)):
            raise ValueError("Missing manifest or duplicate archive entries")
        manifest_info = pack.getinfo("manifest.json")
        if manifest_info.file_size > MANIFEST_LIMIT:
            raise ValueError("Oversized project manifest")
        manifest = json.loads(pack.read("manifest.json"))
        if manifest.get("format") != FORMAT or not isinstance(manifest.get("project"), dict):
            raise ValueError("Not a compatible AI Video Maker project archive")
        entries = manifest.get("files")
        if not isinstance(entries, list) or len(entries) > 100_000:
            raise ValueError("Invalid media manifest file list")
        described = {"manifest.json"}
        placements: dict[str, Path] = {}
        expected_bytes = 0
        for record in entries:
            arcname = record["archive_path"]
            if (not isinstance(arcname, str) or
                    not re.fullmatch(r"media/[0-9a-f]{64}\.[A-Za-z0-9]{1,10}", arcname)):
                raise ValueError("Invalid archive media identifier")
            sha = record["sha256"]
            if not re.fullmatch(r"[0-9a-f]{64}", str(sha)) or not arcname.startswith("media/" + sha):
                raise ValueError("Archive media checksum label mismatch")
            if arcname not in names or arcname in described:
                raise ValueError("Required media missing or duplicated in archive")
            described.add(arcname)
            store = str(record["store_relative"]).replace("@SERIES@", series_id)
            target = (root / store).resolve()
            if not target.is_relative_to(root.resolve()):
                raise ValueError("Archive target tries to write outside local workspace")
            info = pack.getinfo(arcname)
            size = int(record["bytes"])
            if size < 0 or info.file_size != size:
                raise ValueError("Archive media size mismatch")
            expected_bytes += size
            placements[arcname] = target
        if set(names) != described:
            raise ValueError("Archive includes unexpected or potentially unsafe files")
        if shutil.disk_usage(root).free < expected_bytes + 64 * 1024 * 1024:
            raise ValueError("Not enough disk space to restore this complete series")
        created = []
        token_to_path = {}
        try:
            for i, record in enumerate(entries, 1):
                arcname = record["archive_path"]
                target = placements[arcname]
                if target.exists():
                    raise ValueError("Package import conflicts with an existing local media file")
                target.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=target.parent, delete=False, suffix=".part") as temp:
                    temp_path = Path(temp.name)
                    with pack.open(arcname) as reader:
                        shutil.copyfileobj(reader, temp, length=1024 * 1024)
                if digest(temp_path) != record["sha256"]:
                    temp_path.unlink(missing_ok=True)
                    raise ValueError("Portable media checksum mismatch: " + arcname)
                os.replace(temp_path, target)
                created.append(target)
                token_to_path["package://" + arcname] = str(target)
                if progress:
                    progress(f"Restored media {i}/{len(entries)}: {target.name[:70]}")
            new_project = map_paths(manifest["project"], token_to_path)
            new_project["id"] = series_id
            new_project["imported_at"] = now()
            new_project["original_portable_project_id"] = manifest["project"].get("id")
            # Verify no unresolved package references or source machine paths.
            if any(str(value).startswith("package://") for _, value in referenced_paths(new_project)):
                raise ValueError("Some packaged media references could not be restored")
            return new_project
        except Exception:
            for target in created:
                target.unlink(missing_ok=True)
            raise
