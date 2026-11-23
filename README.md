# AI Video Maker — episodic, local-first filmmaking

**Research baseline:** 2026-11-23. **Repository:** `drizzy-drizz/ai-video-maker`.

A general-purpose Windows-first app: paste a Tagalog or English storyline; build a reusable **series bible**; divide it into editable episodes and shots; create consistent characters and scene prompts; generate moving footage through open-weight local models; add voices, captions, sound, and export episodes. **No horror-only presets, mandatory paid API, cloud subscription, or artificial episode limit.**

## Status

- Research and implementation blueprint: **documented** (see [docs/RESEARCH_2026-11-23.md](docs/RESEARCH_2026-11-23.md)).
- Working foundation: series/story library; automatic editable episode-and-shot planning; non-destructive **local Qwen AI Director** suggestions; series bible; local ComfyUI video queue; FFmpeg real-clip stitching; preview/download; Linux media regression tests. This is **not** Google Flow quality parity yet.
- Target platforms: Windows desktop; local network services bound to loopback by default.
- Current developer machine: Ryzen 5 5600G, 16 GB RAM, **GeForce GTX 750** (older Maxwell GPU). This machine can edit and CPU-encode a motion storyboard, but it cannot practically run modern high-quality video diffusion models like Wan2.2 5B.

## Latest coding-first workspace upgrades (November 23, 2026)

**Development status: code implemented and connected in the local editor, but this new batch has NOT been compiled, regression-tested or Windows-packaged.** Per the user's workflow preference, both GitHub Actions CI and Windows workflows are temporarily **manual-trigger only**. Do not interpret the old green build artifacts as validation of the code below.

- **Production shot workspace:** duplicate scenes, split real clips and story text at controlled positions, archive/restore shots without deleting media, and restore older saved series revisions.
- **Video retakes:** browser video imports, rights/ownership declaration, versioned immutable footage files, per-take playback/selection, preserved editing decisions when possible, and explicit approval for model-generated footage. ComfyUI outputs no longer overwrite previous video takes.
- **One-click model batches:** generate missing moving footage or still-image drafts through a locally installed ComfyUI workflow; successful shot results persist, failed jobs can resume without replacing already supplied footage, and editor changes prevent stale generation from overriding current selections.
- **Still-image review:** each generated image is saved as an unapproved, source-prompt-grounded ingredient. User reviews image and model/source rights before pinning it to ComfyUI reference conditioning or CPU motion storyboard.
- **Portable projects:** full-media ZIP export/import with checksum and path-safe recovery into a NEW series ID; fast bounded JSON revision history remains available separately.
- **Real licensed soundtrack catalog:** import unlimited-by-local-disk audio files, preview them, choose tracks per episode and edit the point where the song starts, gain, loop option, fade-in/out. Same saved settings are applied to moving-video and CPU-storyboard MP4 audio.
- **Scene-level sound effects:** multiple user-owned/licensed audio cues per scene with local source choice, on-shot timing, volume, and independent actual FFmpeg mix. Expiring effects receive a short tail fade rather than silently truncating with a click.

[**Full coding-first continuation, boundaries and deferred one-shot acceptance plan**](docs/CODING_FIRST_CONTINUATION_2026_11_23.md)

The desktop application still requires external optional free model weights and compatible hardware for genuine local AI image/video generation. The GTX 750 does not realistically meet modern Wan video diffusion needs. Real model visual quality, Filipino/English voice naturalness, automatic word alignment, and a complete multitrack NLE are not yet proven.

## Three separate honest workflows

**Local motion storyboard — complete CPU feature:** Storyline → editable scenes → upload licensed/approved still images to an immutable versioned asset library → pin images to shots → select camera movement and duration → optionally supply a narration file per scene and rights-confirmed music → **Check Images** → **Render Motion Storyboard** → actual 9:16 or 16:9 animated MP4, scene-timed estimated SRT, technical QA JSON. This uses FFmpeg zoom/pan on still images, **NOT diffusion-generated moving AI video**. A GTX 750 is not needed; CPU does the work. Uploaded image versions never silently change old scene assignments.

**Real AI video on a suitable GPU:** Storyline → series/character canon → pinned image references → local ComfyUI image-to-video model → real moving clips → MP4 and QA. GPU and model weights are external requirements and have NOT been validated with real rendered footage.

**Editable real-footage timeline:** Storyline → import/attach user-approved moving clips and narration → reorder shots, set source in/out trims, add paired video/audio transitions → technical preflight + source review → FFmpeg H.264/AAC export → manually timed or estimated SRT, optional burned captions and a technical QA timeline report. This does not require paid APIs or a modern video diffusion GPU.

## Development stage and real-output quality

**This is a foundation/prototype, NOT a finished Google Flow competitor.** It has basic real-footage stitching, but not an end-to-end automatically generated cinematic episode: natural bilingual narration, multitrack sound design, subtitles, consistently generated characters, and subjective video-quality QA are still missing. Passing automated FFmpeg tests or packaging a Windows EXE does **not** mean the export looks good.

**Current machine note:** GTX 750 GPU (older Maxwell, typically very low VRAM) with Ryzen 5 5600G / 16GB RAM. The app performs a local `nvidia-smi` GPU check and clearly warns for GPU configurations unsuitable for Wan2.2 5B. CPU-side scripting and existing video editing still work; local Wan2.2 generation requires a more capable GPU. Read [Quality Gates](docs/QUALITY_GATES_2026_11_23.md) before calling this production-ready.

### Real image-reference input for ComfyUI

For compatible local image-to-video workflows, **approved scene/character image paths** are now uploaded through ComfyUI's local image API and passed into an explicit {{REFERENCE_IMAGE}} LoadImage placeholder. A missing placeholder **blocks generation** rather than falsely claiming that a reference was applied. Supports PNG/JPEG/WebP, one reference image per basic workflow. This is an actual media handoff but character identity and visual quality still require human review and a compatible GPU. See [Windows reference setup](docs/WINDOWS_SETUP.md).

### Narrative-aware story structure (new series only)

The story planner now weighs **paragraph/scene endings, sentence boundaries and modest turning-point cues** instead of arbitrarily splitting exactly every N words. It records hook/ending excerpts and rough beat-position metadata, verifies every original word remains included, and leaves already-edited existing series untouched. This is a **deterministic heuristic**, not a deep AI evaluation of plot quality; Ollama shot direction remains optional.

### New completed offline-narration + exact-caption workflow

- **Offline TTS adapters:** Piper ONNX CLI and VoxCPM2 GGUF CLI, with local executable/model checks, per-shot license/voice-reference confirmation, generated WAV validation and embedded listening. **One-click Generate Voices For Entire Episode** safely generates missing voices, preserves existing audio, and attaches only after every shot succeeds. Nothing is auto-downloaded; no paid service is contacted. Model quality on the user's GTX 750/Windows remains untested.
- **Manually timed captions** use seconds relative to each shot. Example: 0.00 --> 1.30 | Hello. Captions are checked for overlap and overrun, and saved in the episode.
- **Actual MP4 subtitle burn-in:** choose between SRT-only and FFmpeg/libass burned captions for both imported/generated moving footage and CPU motion storyboards. Downloaded SRT and burned MP4 come from the same cue list; final video preview plays the actual rendered pixels. Estimated timings remain clearly marked when no manual cues are supplied.
- **New tests:** real FFmpeg burned subtitle frames, audio retained in MP4, full real-footage and storyboard MP4 exports with exact manual captions, local TTS CLI/WAV output contract tests, protected generated WAV playback and episode-wide voice job rollback.

See [Narration + Captions setup](docs/NARRATION_CAPTIONS_2026_11_23.md) for Windows model-path configuration and commercial-rights precautions.

### Non-destructive editorial timeline (real moving footage)

The real-footage editor now has per-shot source trims (seconds from original video), shot move-earlier/move-later controls, source trim playback, a timing report and actual FFmpeg video/audio transitions: hard cut, fade, wipe-left or slide-left. The original media is never modified. Transitions require fixed video timebases, source duration checks and dialogue-safe overlap; invalid trims, subtitle timing collisions and narration cuts block export.

The final MP4 is encoded using FFmpeg xfade plus acrossfade and plays directly in the desktop viewer. Scene captions use real edited timeline offsets rather than incorrect original duration sums, and source audio is faded on the same boundaries as video. A new renderer version is staged until passing technical checks; edits during render invalidate obsolete output.

**Scope:** applies to genuine moving-video clips (imported or locally generated), not the separate image-only CPU storyboard. Source preview reviews trim points but does not falsely simulate fully encoded transitions in CSS. [Engineering research and acceptance gates](docs/EDITORIAL_TIMELINE_RESEARCH_2026_11_23.md).

### New quality-first implementation

- Scene-specific character, wardrobe, location, world and style text canon is composed into the **actual ComfyUI prompt**. Identity is not guaranteed without reference-image support.
- Scene-local optional human or locally generated audio tracks are accepted and combined with quieter source sound. An overlong narration **blocks real-footage export** instead of being silently cut. Storyboard scenes automatically extend to fit narration. Licensed, user-confirmed episode music can now be mixed into **both** export modes.
- Click **Check Episode Quality** to validate actual footage duration, narration, aspect ratio, caption speed and missing assets before render.
- Every successful rendered episode now includes an **estimated SRT subtitle file** and JSON **technical QA report**. The subtitles are scene-proportional, not forced speech alignment; review them before publishing. Real footage and motion-storyboard modes publish their MP4 only after codec/duration QA, preserving the previously playable export on failure.

[Competitive research: Flow vs Runway vs Kling vs LTX Desktop](docs/COMPETITIVE_RESEARCH_2026_11_23.md).


## Why not claim Google Flow parity yet?

Google Flow supports prompt-to-video, start/end frames, reusable visual ingredients, scene building, and extending. Many advanced features depend on a subscription or credits. We can reproduce its *workflow ideas*, not Google's proprietary Veo/Omni generation quality using only an APU. Open weights are free to download, but compute, storage, and some community licenses may not be free. See research file.

## Intended local stack

- **Story LLM:** Ollama with Qwen3-4B (Apache-2.0), used for optional **per-episode cinematic shot suggestions**. The initial episode segmentation is currently deterministic.
- **Video:** ComfyUI + Wan2.2-TI2V-5B (Apache-2.0; real text/image-to-video if compatible GPU available).
- **Alternative generation:** HunyuanVideo-1.5 (custom license, >=14 GB VRAM with offload); LTX-2.5 (community license, high VRAM).
- **Image ingredients:** Z-Image-Turbo, FLUX.1-schnell or Qwen-Image (Apache-2.0).
- **Speech (implemented optional adapters):** Piper ONNX and VoxCPM2 GGUF external local CLIs, with recorded usage consent and WAV validation; no model is bundled or auto-installed. QnVoice Filipino GGUF is an optional licensed model; Kokoro remains a planned integration, not a working adapter.
- **Assembly:** FFmpeg/FFprobe local.
- **App:** local server + desktop shell; no authentication tokens sent to external providers.

## Quick start (Windows)

Clone or download this GitHub repository and double-click `start-windows.bat`. Python 3.12 is recommended; pywebview is optional for a native window (`py -3.12 -m pip install -r requirements-desktop.txt`). Install FFmpeg/FFprobe for actual MP4 export. The editor opens locally at `http://127.0.0.1:8766`. Optional AI Director: run Ollama locally and `ollama pull qwen3:4b`. Optional moving AI footage: run ComfyUI locally with a GPU and an installed real-video model, then import an API-format JSON workflow with `{{PROMPT}}` placeholder. All data saves under your Windows home folder in `AI-Video-Maker`.

A separate [Windows desktop build workflow](.github/workflows/windows-build.yml) can run a Windows server/runtime smoke test and package a portable application folder as a GitHub Actions artifact. **During the current coding-first feature batch this workflow and application CI are manual-trigger only; the most recent successful artifact predates the newest production features.** See [setup](docs/WINDOWS_SETUP.md).

## Implementation priorities

1. Persist series, episodes, canon, characters, shot prompts and manually timed captions; preserve manually edited canon and prevent voice job staleness.
2. Plug-in model adapters, local readiness checks, explicit license info and resource profiles.
3. ComfyUI workflow templates with controlled substitutions, job queue, failure recovery, and clip metadata.
4. Footage assembly with reliable audio/video timebases and preview/export parity.
5. Episode continuity checks, scene re-generation, captions, sound and finished-video QA.
6. Desktop packaging and Windows integration testing.

**Research references:** see [docs/RESEARCH_2026-11-23.md](docs/RESEARCH_2026-11-23.md).
