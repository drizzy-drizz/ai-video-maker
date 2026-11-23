# AI Short Drama / AI Film Research and Implementation
Date: November 23, 2026
Repo: https://github.com/drizzy-drizz/ai-video-maker
Status: Integrated in code, not yet compiled/tested/visually benchmarked as requested. CI and Windows packaging are manual-trigger-only.

## Why real micro-dramas need more than one text-to-video prompt

A compelling drama needs (1) a screenplay, (2) recurring actor/wardrobe/location canon, (3) emotional story beats, (4) moving shot generation, (5) voice dialogue and lip sync, (6) true audio/video edit decisions, and (7) final quality review. Many public repos specialize in only one layer. The integrated studio must coordinate these layers without claiming unsupported model capabilities.

## Primary GitHub research — actual model functions and integration limits

- Wan2.2 S2V: https://github.com/Wan-Video/Wan2.2 — speech + approved actor still as talking-video input, large GPU requirement. ComfyUI source: https://github.com/Comfy-Org/docs/blob/main/tutorials/video/wan/wan2-2-s2v.mdx
- InfiniteTalk: https://github.com/MeiGen-AI/InfiniteTalk — audio-driven talking character video and long sequences, compatible local ComfyUI workflow required.
- SkyReels V3: https://github.com/SkyworkAI/SkyReels-V3 — reference-conditioned film shots and talking avatars; model-specific Skywork community terms.
- SkyReels V2: https://github.com/SkyworkAI/SkyReels-V2 — longer-video generation research; does not guarantee story continuity.
- LTX-2 / LTX-2.5: https://github.com/Lightricks/LTX-2 — synchronized video/audio and video generations, LTX-2.x community license; verify commercial conditions per checkpoint.
- HunyuanVideo 1.5: https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5 — local T2V/I2V on sufficiently powerful modern GPUs.
- MuseTalk: https://github.com/TMElyralab/MuseTalk — existing-video lip sync; external adapter, not automatically connected just because its repo is open.
- LivePortrait: https://github.com/KlingAIResearch/LivePortrait — driven portrait animation; external research adapter, not generative full-film replacement.
- ArcReel: https://github.com/ArcReel/ArcReel — multi-stage story, storyboard and movie architecture.
- printfilm: https://github.com/yi1108/printfilm — AI movie and micro-drama creative production structure.
- StoryDiffusion: https://github.com/HVision-NKU/StoryDiffusion — consistent story imagery, model separately required.
- Official ComfyUI: https://github.com/Comfy-Org/ComfyUI/blob/master/server.py — native image upload; do NOT assume a universally portable audio upload endpoint.
- ComfyUI sample S2V UI template: https://github.com/Comfy-Org/workflow_templates/blob/main/templates/video_wan2_2_14B_s2v.json — export a real API-format graph from a working setup; the visual UI template itself is not an API workflow.

Do not confuse free code with unrestricted commercial model use. Each checkpoint/base model, actor/voice likeness, reference material and audio clip has its own terms and permissions. No model is silently downloaded, no paid endpoint is called.

## Implemented in the local application — code not yet release-validated

1. Drama Director in drama_studio.py creates a source-anchored board for drama, romance, revenge, family, suspense, comedy, action, mystery, fantasy and slice of life. Preserves every original scene script, casts and real story events. Assigns hook/setup/escalation/reveal/payoff/cliffhanger roles, visible acting emotions, camera angles, relevant recurring actor names, locations and exact dialogue extracts.
2. The director's scene-level camera, acting, emotion, location, visual objective and soundscape controls persist in episode JSON, respect manually locked shots and feed the ACTUAL ComfyUI positive prompt. Stale source text blocks inaccurate old direction reuse.
3. Optional locally installed Ollama/Qwen can suggest acting and screenplay lines. screenplay_drafts.py distinguishes SOURCE-EXACT lines from CREATIVE MODEL DRAFTS. The artist approves each draft independently; the original storyline and scenes never change automatically. Single-speaker per shot; proposals cannot introduce new named actors if the cast was established.
4. Dedicated Spoken Dialogue/Voice Script editor allows spoken lines separate from camera/stage directions. The approved text is the actual Piper/VoxCPM2 TTS source, and estimated captions use it. Silent-action mode skips additional narration and estimated spoken captions. Generated voice provenance stores a spoken-script SHA256; stale WAVs cannot drive newer speech-video.
5. ComfyUI model families can be chosen for local API workflows and verified for declared placeholders, while model presence/GPU performance is explicitly unverified. Supported placeholder contract: PROMPT, NEGATIVE_PROMPT, SEED, REFERENCE_IMAGE, DIALOGUE_AUDIO, DIALOGUE_TEXT and PREVIOUS_FRAME (each enclosed in double curly braces in the real JSON). LoadImage must consume a genuine uploaded reference; LoadAudio must consume a real local audio filename.
6. comfy_drama_bridge.py copies rights-confirmed narration audio into the configured local ComfyUI input folder and validates its checksum. The env variable AIVM_COMFY_INPUT_DIR must point at the same local ComfyUI input folder; no fake cloud audio endpoint. Previous-frame continuity extracts the last actual source frame of the previous approved shot (honoring trim points) or uses its approved still image.
7. A real ComfyUI prompt job receives the canonical shot direction plus approved image, audio and/or previous visual frame, polls real model results, retrieves actual MP4/MOV/MKV/WebM, and creates an immutable unapproved take. It never overwrites prior footage when the editor is changed. Source audio carrying generated speech is not mixed with the original TTS a second time during export.
8. drama_production.py lets the user choose a dedicated talking workflow and a cinematic workflow for the whole episode. It routes per shot, skips already attached footage, checkpoints successful moving-video takes, and resumes after errors. A detailed dashboard shows missing references, approved voices, missing footage, and unreviewed generated takes; no automatic fake completed movie.
9. All previously coded non-destructive edits, matching captions, scene SFX and licensed soundtrack library still produce the intended final storyboard/video export pipeline, pending a deliberate full validation run.

## Setup on a compatible local Windows model workstation

In PowerShell, before opening the application:

    $env:AIVM_COMFY_URL = 'http://127.0.0.1:8188'
    $env:AIVM_COMFY_INPUT_DIR = 'C:\AI\ComfyUI\input'
    $env:AIVM_OLLAMA_URL = 'http://127.0.0.1:11434'
    $env:AIVM_OLLAMA_MODEL = 'qwen3:4b'
    py -3.12 app.py --desktop

These paths are examples. Install ComfyUI, Ollama, model weights and licensed reference assets separately. The same-machine audio folder is necessary for LoadAudio models.

Working procedure: create a Tagalog or English series; define actor Bible/canon and approved reference images; open Drama Director and build a board; optionally ask Qwen for acting and dialogue, then approve per shot; generate or attach permitted WAV speech and listen to it; install a genuine ComfyUI API graph for talking and another for cinematic shots; select model workflows; inspect drama readiness; run Generate Missing Drama Video Shots; review generated takes and their rights; trim/reorder/edit effects/music/captions and render actual MP4; human-review story meaning, dialogue emotion, facial consistency and lips before publishing.

## Limitations and pending consolidated acceptance

- No newest-batch Python or JavaScript compile, GitHub CI, native Windows model or FFmpeg tests have been run, deliberately following coding-first preference.
- GTX 750 is insufficient for practical modern Wan2.2 S2V, LTX-2.5 or high-resolution SkyReels local diffusion; free weights do not provide free GPU computation.
- Research-only MuseTalk/LivePortrait CLI adapters, fully automatic emotionally perfect screenplay writing, professional multitrack NLE, verified Tagalog word-for-word ASR timing, automatic visual identity metrics, and multi-voice acting within a single shot are not claimed complete.
- Manual approval is required for creative dialogue and generated media; technical checks do not guarantee emotional or commercial-quality cinema.
- Run all checks and actual model/storyboard benchmarks in ONE consolidated acceptance phase before declaring the new drama workflow production-ready.
