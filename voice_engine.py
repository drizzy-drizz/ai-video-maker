"""Free, local-only TTS adapter for user-installed licensed voice models.

Supports:
  Piper CLI with ONNX model (English, or Tagalog if user supplies a valid voice)
  VoxCPM2 GGUF via llama.cpp-omni's voxcpm2-cli (English/Tagalog)
Neither model is downloaded silently; model licenses and voice/reference consent
must be checked explicitly. External engines are separately installed by user.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path

from studio_quality import media_info

BACKENDS = {"piper", "voxcpm2"}
MAX_CHARS = 4000


def command_path(config: str, default: str) -> str | None:
    value = os.environ.get(config, default).strip()
    if not value:
        return None
    path = Path(value).expanduser()
    if path.is_file():
        return str(path.resolve())
    return shutil.which(value)


def configured_backend(language: str, engine: str) -> dict:
    language = "tl" if language == "tl" else "en"
    if engine == "piper":
        exe = command_path("AIVM_PIPER_EXE", "piper")
        model_env = "AIVM_PIPER_TL_MODEL" if language == "tl" else "AIVM_PIPER_EN_MODEL"
        model = Path(os.environ.get(model_env, "")).expanduser()
        reason = ""
        if not exe:
            reason = "Piper executable not installed or not on PATH"
        elif not model.is_file() or model.suffix.lower() != ".onnx":
            reason = model_env + " must point to an installed, licensed .onnx voice"
        elif not Path(str(model) + ".json").is_file():
            reason = "Piper .onnx.json voice config is missing"
        return {"name": "piper", "available": not reason, "reason": reason,
                "model": str(model) if model.is_file() else "",
                "executable": exe or "", "language": language}
    if engine == "voxcpm2":
        exe = command_path("AIVM_VOXCPM2_EXE", "voxcpm2-cli")
        base = Path(os.environ.get("AIVM_VOXCPM2_BASE", "")).expanduser()
        acoustic = Path(os.environ.get("AIVM_VOXCPM2_ACOUSTIC", "")).expanduser()
        reference = os.environ.get("AIVM_VOXCPM2_REFERENCE", "").strip()
        reason = ""
        if not exe:
            reason = "VoxCPM2 CLI not installed; build voxcpm2-cli from llama.cpp-omni"
        elif not base.is_file() or base.suffix.lower() != ".gguf":
            reason = "AIVM_VOXCPM2_BASE must point to local BaseLM GGUF"
        elif not acoustic.is_file() or acoustic.suffix.lower() != ".gguf":
            reason = "AIVM_VOXCPM2_ACOUSTIC must point to local acoustic GGUF"
        elif reference and not Path(reference).expanduser().is_file():
            reason = "VoxCPM2 optional reference WAV not found"
        return {"name": "voxcpm2", "available": not reason, "reason": reason,
                "model": str(base) if base.is_file() else "",
                "acoustic": str(acoustic) if acoustic.is_file() else "",
                "reference": reference, "executable": exe or "", "language": language}
    raise ValueError("Voice backend must be piper or voxcpm2")


def voice_options(language: str) -> dict:
    candidates = [configured_backend(language, mode) for mode in ("piper", "voxcpm2")]
    preferred = "voxcpm2" if language == "tl" else "piper"
    available = [item["name"] for item in candidates if item["available"]]
    chosen = preferred if preferred in available else (available[0] if available else None)
    return {
        "language": language, "backends": candidates, "recommended": chosen,
        "note": ("No paid API. Voices/models are separately installed. User must confirm "
                 "source-model commercial license and voice/reference permission; "
                 "audio quality is unverified until listened to.")
    }


def generate_wav(text: str, language: str, engine: str, destination: Path,
                 rights_confirmed: bool) -> dict:
    script = str(text).strip()
    if not 1 <= len(script) <= MAX_CHARS:
        raise ValueError(f"Voice script must contain 1-{MAX_CHARS} characters")
    if not rights_confirmed:
        raise ValueError("Confirm voice-model license and rights to any reference voice before generation")
    if engine == "auto":
        engine = voice_options(language)["recommended"] or ""
    if engine not in BACKENDS:
        raise ValueError("No configured offline voice model. Install Piper or VoxCPM2 and set local environment paths.")
    config = configured_backend(language, engine)
    if not config["available"]:
        raise ValueError(engine + " unavailable: " + config["reason"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    # All generation writes to an unadvertised WAV, never overwrites selected audio on failure.
    temp = destination.with_name("generating-" + uuid.uuid4().hex + ".wav")
    try:
        if engine == "piper":
            command = [config["executable"], "--model", config["model"], "--output_file", str(temp)]
            process = subprocess.run(command, input=script + "\n", text=True,
                                     encoding="utf-8", errors="replace",
                                     capture_output=True, timeout=3600)
        else:
            command = [config["executable"], "-t", script, "-o", str(temp)]
            if config["reference"]:
                command.extend(["-r", str(Path(config["reference"]).expanduser().resolve())])
            command.extend([config["model"], config["acoustic"]])
            process = subprocess.run(command, capture_output=True, text=True,
                                     encoding="utf-8", errors="replace", timeout=3600)
        if process.returncode:
            raise RuntimeError(engine + " CLI failed: " + (process.stderr or process.stdout)[-1200:])
        if not temp.is_file() or temp.stat().st_size < 100:
            raise RuntimeError(engine + " returned no usable WAV file")
        info = media_info(temp)
        if not info["has_audio"] or info["duration"] <= 0.08 or info["duration"] > 7200:
            raise RuntimeError(engine + " generated WAV is silent/invalid or out of duration bounds")
        # One artifact per request, never overwrite prior generated voice versions.
        os.replace(temp, destination)
        return {
            "engine": engine, "language": language, "wav": str(destination),
            "duration_seconds": round(info["duration"], 3),
            "model": config["model"], "reference_used": bool(config.get("reference")),
            "synthetic_voice": True, "quality_reviewed": False,
            "model_license_verified_by_user": True
        }
    finally:
        temp.unlink(missing_ok=True)
