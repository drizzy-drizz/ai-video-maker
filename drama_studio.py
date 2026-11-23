"""Source-anchored micro-drama planning + honest open-model workflow catalog.

This module provides a complete local, non-destructive drama direction layer:
shot roles, acting, camera, identity and dialogue metadata are saved to a
project and included in the actual model prompt. It does NOT pretend to run
a visual diffusion model, magically infer dialogue voice or verify story quality.
"""
from __future__ import annotations

import copy
import re
from datetime import datetime, timezone

import studio_quality as quality

GENRES = {
    "drama": {"style": "grounded dramatic realism", "camera": "intimate human eye-level framing", "sound": "room tone and restrained tension"},
    "romance": {"style": "warm intimate romance", "camera": "soft over-the-shoulder close-ups", "sound": "soft room tone and meaningful pauses"},
    "revenge": {"style": "restrained revenge thriller", "camera": "controlled push-ins and confrontational reverses", "sound": "tense silence and sharp revealing beats"},
    "family": {"style": "grounded domestic family drama", "camera": "human-scale medium shots and reaction close-ups", "sound": "natural home ambiance"},
    "suspense": {"style": "psychological suspense", "camera": "slow reveal angles without confusing geography", "sound": "quiet apprehension and situational room tone"},
    "comedy": {"style": "naturalistic situational comedy", "camera": "clear reaction shots timed around the joke", "sound": "authentic reactions, no forced canned laughter"},
    "action": {"style": "grounded action choreography", "camera": "readable wide action followed by restrained close-ups", "sound": "source-grounded impacts, footsteps and movement"},
    "fantasy": {"style": "coherent fantastical world", "camera": "establishing frames that preserve visual geography", "sound": "environmental texture matching the original world"},
    "mystery": {"style": "investigative mystery", "camera": "motivated close-ups of actual story evidence", "sound": "subtle environmental detail and quiet"},
    "slice_of_life": {"style": "candid everyday life", "camera": "natural conversational blocking", "sound": "authentic everyday environments"},
}
ROLES = ("hook", "setup", "escalation", "reveal", "payoff", "cliffhanger")
ANGLES = ("wide", "medium", "close_up", "over_shoulder", "two_shot", "reaction", "insert")
ACTIONS = {
    "wide": "Keep place and blocking spatially legible.",
    "medium": "Show the characters physically reacting to one another.",
    "close_up": "Hold on the face and visible change of expression, no morphing.",
    "over_shoulder": "Keep the speaking person's eye line and spatial relationship coherent.",
    "two_shot": "Keep both people distinct with stable identities and consistent wardrobe.",
    "reaction": "Hold on the listener's visible reaction after the spoken line.",
    "insert": "Emphasize only the actual source-story object or clue, not invented props.",
}
EMOTIONS = ("restrained", "anxious", "joyful", "angry", "heartbroken", "hopeful", "shocked", "suspicious", "tender", "amused")
ROLE_TRIGGERS = {
    "reveal": re.compile(r"\b(nalaman|natuklasan|sikreto|katotohanan|ibinunyag|revealed|secret|truth|discovered|realized|betrayal)\b", re.I),
    "escalation": re.compile(r"\b(pero|ngunit|biglang|nagalit|sinampal|takot|but|suddenly|argued|confronted|ran|afraid)\b", re.I),
    "payoff": re.compile(r"\b(patawad|sa wakas|nagpatawad|finally|forgave|won|reunited|relief)\b", re.I),
    "cliffhanger": re.compile(r"\b(sino|bakit|paano|ano|what if|who was|why|how could|to be continued)\b", re.I),
}
EMOTION_TRIGGERS = [
    ("heartbroken", r"\b(umiiyak|luha|nasaktan|heartbroken|crying|tears|broke up|namatay|death)\b"),
    ("shocked", r"\b(nagulat|bigla|shocked|suddenly|unbelievable|hindi makapaniwala)\b"),
    ("angry", r"\b(galit|nagalit|sinampal|angry|furious|shouted|confronted)\b"),
    ("anxious", r"\b(takot|kinabahan|nervous|afraid|worried|anxious)\b"),
    ("tender", r"\b(mahal|love|hugged|niyakap|kissed|hinagkan)\b"),
    ("amused", r"\b(tawa|tumawa|laughed|funny|joke|nakakatawa)\b"),
]
CAMERAS = {
    "hook": "close_up", "setup": "wide", "escalation": "over_shoulder",
    "reveal": "reaction", "payoff": "two_shot", "cliffhanger": "close_up",
}
# Curated research pointers. The license belongs to each checkpoint, not to us.
MODELS = [
    {"id":"wan22_s2v","name":"Wan2.2 S2V 14B","task":"image+speech-to-video","capabilities":["image","dialogue_audio","video"],"requires":["{{REFERENCE_IMAGE}}","{{DIALOGUE_AUDIO}}"],"integration":"comfyui-api","hardware":"very_high_gpu","license":"Wan repository Apache-2.0; verify checkpoint/reference rights","url":"https://github.com/Wan-Video/Wan2.2","workflow_url":"https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_wan2_2_14B_s2v.json","note":"Talking portrait/actor generation requires an actual ComfyUI S2V API graph."},
    {"id":"ltx25","name":"LTX-2.5","task":"multishot audio-video","capabilities":["video","audio","image"],"requires":["{{PROMPT}}"],"integration":"comfyui-api","hardware":"very_high_gpu","license":"LTX-2.x Community License with commercial conditions; review terms and gated checkpoints","url":"https://github.com/Lightricks/LTX-2","workflow_url":"https://github.com/Lightricks/LTX-Desktop","note":"Use local Fast weights with a compatible workflow; API-only Pro is not a free local model."},
    {"id":"skyreels_v3","name":"SkyReels V3","task":"reference/extension/talking-avatar video","capabilities":["video","image","dialogue_audio"],"requires":["{{PROMPT}}"],"integration":"comfyui-api","hardware":"very_high_gpu","license":"Skywork Community License; commercial conditions must be checked","url":"https://github.com/SkyworkAI/SkyReels-V3","workflow_url":"https://github.com/SkyworkAI/SkyReels-V3","note":"Use only with an installed, verified ComfyUI API-compatible graph; upstream CLI alone is not a ComfyUI workflow."},
    {"id":"hunyuan15","name":"HunyuanVideo 1.5","task":"text/image-to-video","capabilities":["video","image"],"requires":["{{PROMPT}}"],"integration":"comfyui-api","hardware":"modern_gpu","license":"Tencent Hunyuan model-specific license; review conditions","url":"https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5","workflow_url":"https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5/tree/main/ComfyUI","note":"Consumer-grade is still modern multi-GB VRAM, not GTX 750."},
    {"id":"infinitetalk","name":"InfiniteTalk","task":"audio-driven character/video dubbing","capabilities":["dialogue_audio","video","image"],"requires":["{{DIALOGUE_AUDIO}}"],"integration":"comfyui-api","hardware":"very_high_gpu","license":"Repository Apache-2.0; verify base model and voice/face reference rights separately","url":"https://github.com/MeiGen-AI/InfiniteTalk","workflow_url":"https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_wan2_1_infinitetalk.json","note":"Requires a compatible ComfyUI API graph and original approved dialogue audio."},
    {"id":"musetalk","name":"MuseTalk","task":"lip sync on existing video","capabilities":["dialogue_audio","video"],"requires":["{{DIALOGUE_AUDIO}}"],"integration":"external-model","hardware":"modern_gpu","license":"Code MIT, model weights and third-party assets have separate terms","url":"https://github.com/TMElyralab/MuseTalk","workflow_url":"https://github.com/TMElyralab/MuseTalk","note":"Research option, not directly executable by generic ComfyUI API without a compatible adapter."},
    {"id":"liveportrait","name":"LivePortrait","task":"portrait expression transfer","capabilities":["image","video"],"requires":["{{REFERENCE_IMAGE}}"],"integration":"external-model","hardware":"modern_gpu","license":"Model-specific licensing/checkpoint terms; inspect official repo","url":"https://github.com/KlingAIResearch/LivePortrait","workflow_url":"https://github.com/KlingAIResearch/LivePortrait","note":"Expression transfer isn't the same as authored speech-driven footage."},
    {"id":"skyreels_v2","name":"SkyReels V2","task":"longer-form I2V film generation","capabilities":["video","image"],"requires":["{{PROMPT}}"],"integration":"comfyui-api","hardware":"very_high_gpu","license":"Skywork Community License; review commercial conditions","url":"https://github.com/SkyworkAI/SkyReels-V2","workflow_url":"https://github.com/SkyworkAI/SkyReels-V2","note":"Infinity-length research does not guarantee a coherent unedited episode."}
]
MODEL_INDEX = {item["id"]: item for item in MODELS}

def model_catalog() -> list[dict]:
    return copy.deepcopy(MODELS)

def workflow_capabilities(workflow: dict) -> dict:
    """Audit explicit placeholder contracts in a real ComfyUI API graph."""
    if not isinstance(workflow, dict) or not workflow:
        raise ValueError("Install a nonempty ComfyUI API-format workflow")
    if not all(isinstance(node, dict) and "class_type" in node and isinstance(node.get("inputs"), dict)
               for node in workflow.values()):
        raise ValueError("Export ComfyUI API-format JSON, not the graphical editor layout")
    raw = __import__("json").dumps(workflow)
    recognized = ("{{PROMPT}}","{{NEGATIVE_PROMPT}}","{{SEED}}",
                  "{{REFERENCE_IMAGE}}","{{DIALOGUE_AUDIO}}","{{PREVIOUS_FRAME}}")
    found = [token for token in recognized if token in raw]
    if "{{PROMPT}}" not in found:
        raise ValueError("Put {{PROMPT}} in the positive prompt input of the ComfyUI graph")
    unsupported = sorted(set(re.findall(r"\{\{[A-Z][A-Z0-9_]*\}\}", raw))-set(recognized))
    if unsupported:
        raise ValueError("Unsupported unbound workflow placeholders: " + ", ".join(unsupported))
    outputs = sorted({str(node.get("class_type")) for node in workflow.values()
                      if any(token in str(node.get("class_type")).lower()
                             for token in ("save", "combine", "video", "imageoutput"))})
    return {
        "placeholders": found,
        "has_image_conditioning": "{{REFERENCE_IMAGE}}" in found,
        "has_dialogue_audio": "{{DIALOGUE_AUDIO}}" in found,
        "has_previous_frame": "{{PREVIOUS_FRAME}}" in found,
        "output_nodes": outputs,
        "note": "Graph capabilities checked structurally only. Model checkpoints/GPU are not tested."
    }

def validate_model_workflow(family: str, workflow: dict) -> dict:
    family = str(family or "custom")
    if family != "custom" and family not in MODEL_INDEX:
        raise ValueError("Unknown drama model family")
    info = workflow_capabilities(workflow)
    if family in MODEL_INDEX:
        model = MODEL_INDEX[family]
        if model["integration"] == "external-model":
            raise ValueError(model["name"] + " requires a specific adapter; generic ComfyUI integration is not verified")
        for token in model["requires"]:
            if token not in info["placeholders"]:
                raise ValueError(model["name"] + " workflow must actually contain " + token)
    return {"family": family, **info}

def scene_role(index: int, total: int, script: str) -> str:
    if index == 0:
        return "hook"
    if index == total-1:
        return "cliffhanger" if re.search(r"[\?!]\s*$", script) or ROLE_TRIGGERS["cliffhanger"].search(script) else "payoff"
    for role in ("reveal", "payoff", "escalation"):
        if ROLE_TRIGGERS[role].search(script):
            return role
    return "setup" if index <= max(1, total//4) else "escalation"

def infer_emotion(script: str) -> str:
    for name, pattern in EMOTION_TRIGGERS:
        if re.search(pattern, script, re.I):
            return name
    return "restrained"

def dialogue_beats(script: str, names: list[str]) -> list[dict]:
    """Only extract lines actually present; do not invent dialogue or actors."""
    output = []
    lines = script.splitlines()
    used = set()
    for line in lines:
        m = re.match(r"^\s*([^\n:]{1,70})\s*:\s*(.+)", line)
        if m:
            speaker = m.group(1).strip()
            if speaker.casefold() in {name.casefold() for name in names}:
                content = m.group(2).strip()
                if content:
                    output.append({"speaker": speaker, "exact_line": content[:1500]})
                    used.add(content)
    if not output:
        for found in re.finditer(r'[“"]([^”"\n]{2,420})[”"]', script):
            if found.group(1).strip() not in used:
                output.append({"speaker": "speaker not specified", "exact_line": found.group(1).strip()})
    return output[:25]

def board_for_episode(series: dict, episode: dict, *, genre: str="drama") -> dict:
    genre = str(genre or "drama").lower()
    if genre not in GENRES:
        raise ValueError("Choose a supported drama style: " + ", ".join(sorted(GENRES)))
    scenes = episode.get("scenes") or []
    if not scenes:
        raise ValueError("Episode has no source-grounded shots")
    bible = series.get("bible") or {}
    catalog = [p for p in (bible.get("characters") or []) if isinstance(p, dict)]
    current = []
    last_location = ""
    for i, scene in enumerate(scenes):
        source = str(scene.get("script") or "").strip()
        if not source:
            raise ValueError("Source script missing from scene " + str(i+1))
        role = scene_role(i, len(scenes), source)
        cast = [p.get("name") for p in quality.referenced_characters(series, scene)
                if p.get("name")]
        locations = []
        for item in bible.get("locations") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "")
            if name and re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", source, re.I):
                locations.append(name)
        if locations:
            last_location = locations[0]
        lines = dialogue_beats(source, [str(p.get("name")) for p in catalog if p.get("name")])
        angle = CAMERAS[role]
        if lines and len(cast) > 1 and role in ("setup","escalation"):
            angle = "two_shot"
        mood = infer_emotion(source)
        current.append({
            "scene_id": scene["id"],
            "source_script": source,
            "role": role,
            "emotion": mood,
            "shot_type": angle,
            "location": locations[0] if locations else last_location,
            "cast": cast,
            "dialogue": lines,
            "look": GENRES[genre]["style"],
            "acting": ACTIONS[angle],
            "audio_intent": GENRES[genre]["sound"],
            "visual_objective": "Show only the event in this exact story beat. Keep its outcome and participants unchanged.",
            "locked": False,
        })
    return {
        "version": 1, "genre": genre, "language": series.get("language") or "en",
        "series_id": series.get("id"), "episode_id": episode.get("id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "original_story_unchanged": True,
        "source_coverage": all(x["source_script"] == str(y.get("script") or "").strip()
                               for x,y in zip(current,scenes)),
        "shot_count": len(current), "scenes": current,
        "editing_advice": "Source-anchored camera/emotion proposals. Review dialogue, action, timing, likeness and actual generated motion.",
    }

def apply_board(series: dict, episode: dict, board: dict,
                *, preserve_locked: bool=True) -> dict:
    """Attach every shot's direction, keeping manually locked shots unchanged."""
    expected = [s["id"] for s in episode.get("scenes") or []]
    proposed = [entry.get("scene_id") for entry in board.get("scenes") or []]
    if expected != proposed or not board.get("source_coverage"):
        raise ValueError("Drama board is stale; all shot IDs/order and source text must match")
    accepted, skipped = 0, 0
    for scene, direction in zip(episode["scenes"], board["scenes"]):
        if direction["source_script"] != str(scene.get("script") or "").strip():
            raise ValueError("Shot script changed since drama board was constructed")
        if preserve_locked and (scene.get("drama_plan") or {}).get("locked"):
            skipped += 1
            continue
        scene["drama_plan"] = copy.deepcopy(direction)
        accepted += 1
    episode["drama_style"] = board["genre"]
    episode["drama_board_created_at"] = board["created_at"]
    episode["drama_board_coverage"] = {"scene_count": len(expected), "all_original_text_preserved": True}
    return {"updated": accepted, "locked_skipped": skipped, "shot_count": len(expected),
            "genre": board["genre"]}

def validated_scene_direction(plan: dict) -> dict:
    if not isinstance(plan, dict):
        raise ValueError("Drama direction must be an object")
    if plan.get("role") not in ROLES or plan.get("shot_type") not in ANGLES or plan.get("emotion") not in EMOTIONS:
        raise ValueError("Unknown scene role, camera angle or emotion")
    for key in ("acting","visual_objective","audio_intent","look","location"):
        if len(str(plan.get(key) or "")) > 1000:
            raise ValueError("Drama direction text too long: " + key)
    return plan

def prompt_block(plan: dict) -> str:
    plan = validated_scene_direction(plan)
    shot = plan["shot_type"].replace("_", " ")
    return "\n".join([
        "DRAMA DIRECTOR — visible performance and camera blocking, never replace source events:",
        "Dramatic purpose: " + str(plan["role"]),
        "Shot composition: " + shot,
        "Actor emotion: " + str(plan["emotion"]),
        "Acting notes: " + str(plan.get("acting") or ""),
        "Visual objective: " + str(plan.get("visual_objective") or ""),
        "Soundscape intention: " + str(plan.get("audio_intent") or ""),
        "Consistent location: " + str(plan.get("location") or "original story location"),
        "Established mood and look: " + str(plan.get("look") or ""),
        "Use exact source text for dialogue; DO NOT overlay unsupported captions or invented spoken lines."
    ])
