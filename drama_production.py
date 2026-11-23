"""Real drama-production orchestration and honest review gates.

This is a resumable local driver that uses the existing ComfyUI image-to-video
and audio-to-video backends and their checkpointed immutable takes. It never
manufactures a video when a checkpoint/reference/voice is absent and never
publishes an unreviewed model-generated face or voice.
"""
from __future__ import annotations

from pathlib import Path

import drama_studio
import studio_quality as quality


def wants_talking(scene: dict) -> bool:
    mode = str(scene.get("drama_generation_mode") or "auto")
    if mode not in ("auto", "cinematic", "talking"):
        raise ValueError("Drama video mode must be auto, cinematic or talking")
    if mode == "talking":
        return True
    if mode == "cinematic":
        return False
    plan = scene.get("drama_plan") or {}
    return bool(plan.get("dialogue") and scene.get("narration") and
                scene.get("dialogue_audio_rights_confirmed") is True)


def report(series: dict, episode: dict) -> dict:
    """Actionable story/refs/voices/footage/review status, not a quality score."""
    shots = []
    tally = {
        "total": 0, "directed": 0, "images_missing": 0,
        "talking_voice_missing": 0, "footage_missing": 0,
        "unreviewed_takes": 0, "video_ready": 0
    }
    for number, scene in enumerate(episode.get("scenes") or [], 1):
        tally["total"] += 1
        plan = scene.get("drama_plan") or {}
        directed = bool(plan and plan.get("source_script") ==
                        str(scene.get("script") or "").strip())
        if directed:
            tally["directed"] += 1
        talking = wants_talking(scene)
        reference_error = ""
        try:
            ref = quality.reference_image_for_scene(series, scene)
        except (ValueError, FileNotFoundError, OSError) as exc:
            ref = None
            reference_error = str(exc)
        if not ref:
            tally["images_missing"] += 1
        voice = quality.normalized_path(scene.get("narration"))
        voice_valid = bool(voice and voice.is_file() and
                           scene.get("dialogue_audio_rights_confirmed"))
        if talking and not voice_valid:
            tally["talking_voice_missing"] += 1
        clip = quality.normalized_path(scene.get("clip"))
        clip_ready = bool(clip and clip.is_file())
        if not clip_ready:
            tally["footage_missing"] += 1
        selected = next((t for t in scene.get("takes") or []
                         if t.get("id") == scene.get("selected_take_id")), None)
        approved = not (selected and selected.get("rights") == "generated_unverified"
                        and not selected.get("approved_for_use"))
        if clip_ready and not approved:
            tally["unreviewed_takes"] += 1
        if clip_ready and approved:
            tally["video_ready"] += 1
        blockers = []
        if not directed:
            blockers.append("Build/review Drama Board")
        if talking and not ref:
            blockers.append("Approve an actor reference image for talking video")
        if talking and not voice_valid:
            blockers.append("Attach approved spoken audio and confirm voice rights")
        if not clip_ready:
            blockers.append("Generate or import real moving footage")
        if clip_ready and not approved:
            blockers.append("Watch/approve generated video take before export")
        shots.append({
            "id": scene.get("id"), "number": number,
            "mode": "talking" if talking else "cinematic",
            "dramatic_role": plan.get("role", "unplanned"),
            "reference_ready": bool(ref), "reference_error": reference_error,
            "voice_ready": voice_valid, "clip_ready": clip_ready,
            "take_approved": approved, "blockers": blockers
        })
    next_actions = []
    if tally["directed"] != tally["total"]:
        next_actions.append("Build the source-grounded drama board")
    if tally["images_missing"]:
        next_actions.append("Create/approve character and scene reference images where needed")
    if tally["talking_voice_missing"]:
        next_actions.append("Generate or attach permitted actor narration audio")
    if tally["footage_missing"]:
        next_actions.append("Run missing scene video generation with installed compatible model workflows")
    if tally["unreviewed_takes"]:
        next_actions.append("Watch and approve real generated video takes")
    if tally["video_ready"] == tally["total"] and tally["total"]:
        next_actions.append("Render and visually review the final MP4 and dialogue sync")
    return {
        "episode_id": episode.get("id"),
        "status": ("footage_ready_for_render" if tally["video_ready"] == tally["total"]
                   and tally["total"] > 0 else "in_production"),
        "counts": tally, "scenes": shots, "next_actions": next_actions,
        "truth_note": "Based on project media/rights presence, NOT a model-quality, lip-sync or emotional-engagement score."
    }


def produce_missing(series_id: str, episode_id: str, cinematic_workflow: str,
                    talking_workflow: str, *,
                    load_project, get_episode, prepare_board, generate_scene,
                    workflow_path, progress=None) -> str:
    """One real resumable batch with model-specific routing per shot.

    For each missing scene, require the actual workflow/conditioning sources,
    then call the same already-wired ComfyUI video generator used by the editor.
    Completed takes are checkpointed independently. No silent fallback to
    a different model if an audio/portrait workflow is not configured.
    """
    series = load_project(series_id)
    episode = get_episode(series, episode_id)
    if not episode.get("scenes"):
        raise ValueError("No story shots to direct")
    if not all((scene.get("drama_plan") or {}).get("source_script") ==
               str(scene.get("script") or "").strip()
               for scene in episode["scenes"]):
        # Re-read and acquire the application's global project lock inside
        # prepare_board, preventing lost edits from an asynchronous model job.
        prepare_board(series_id, episode_id)
        series = load_project(series_id)
        episode = get_episode(series, episode_id)
    missing = [s["id"] for s in episode["scenes"]
               if not s.get("clip") or not Path(str(s["clip"])).is_file()]
    if not missing:
        return "All scenes already contain moving footage. Review takes and export; no footage regenerated."
    done = 0
    for index, scene_id in enumerate(missing, 1):
        current = load_project(series_id)
        shot = next((s for s in get_episode(current, episode_id)["scenes"]
                     if s.get("id") == scene_id), None)
        if not shot:
            raise RuntimeError("Scene was removed during drama production; no replacement generated")
        if shot.get("clip") and Path(str(shot["clip"])).is_file():
            continue
        talking = wants_talking(shot)
        workflow = talking_workflow if talking else cinematic_workflow
        if not workflow or not workflow_path(workflow).is_file():
            raise RuntimeError(
                "Scene " + str(index) + "/" + str(len(missing)) +
                (" needs a local S2V talking workflow" if talking
                 else " needs a local cinematic video workflow") +
                ". No fake video was substituted.")
        if progress:
            progress("Generating REAL " + ("speaking" if talking else "cinematic") +
                     " shot " + str(index) + "/" + str(len(missing)) +
                     ": " + str(shot.get("script") or "")[:90])
        try:
            generate_scene(series_id, episode_id, scene_id, workflow)
        except Exception as exc:
            raise RuntimeError(
                f"Drama generation paused at shot {index}/{len(missing)}: {exc}. "
                f"{done} previous shots are retained as versioned takes. "
                "Fix model/input issue, then resume this batch.") from exc
        done += 1
    after = load_project(series_id)
    state = report(after, get_episode(after, episode_id))
    return (
        f"Drama generation batch saved {done} new moving-video take(s). "
        f"{state['counts']['unreviewed_takes']} generated take(s) need human "
        "visual/model-rights approval. No episode was automatically published."
    )
