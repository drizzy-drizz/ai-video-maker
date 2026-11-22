# AI Video Maker — episodic, local-first filmmaking

**Research baseline:** 2026-11-23. **Repository:** `drizzy-drizz/ai-video-maker`.

A general-purpose Windows-first app: paste a Tagalog or English storyline; build a reusable **series bible**; divide it into editable episodes and shots; create consistent characters and scene prompts; generate moving footage through open-weight local models; add voices, captions, sound, and export episodes. **No horror-only presets, mandatory paid API, cloud subscription, or artificial episode limit.**

## Status

- Research and implementation blueprint: **documented** (see [docs/RESEARCH_2026-11-23.md](docs/RESEARCH_2026-11-23.md)).
- Working foundation: series/story library; automatic editable episode-and-shot planning; non-destructive **local Qwen AI Director** suggestions; series bible; local ComfyUI video queue; FFmpeg real-clip stitching; preview/download; Linux media regression tests. This is **not** Google Flow quality parity yet.
- Target platforms: Windows desktop; local network services bound to loopback by default.
- Current developer machine: Ryzen 5 5600G, 16 GB RAM, **GeForce GTX 750** (older Maxwell GPU). This machine can edit and CPU-encode a motion storyboard, but it cannot practically run modern high-quality video diffusion models like Wan2.2 5B.

## Three separate honest workflows

**Local motion storyboard — complete CPU feature:** Storyline → editable scenes → upload licensed/approved still images to an immutable versioned asset library → pin images to shots → select camera movement and duration → optionally supply a narration file per scene and rights-confirmed music → **Check Images** → **Render Motion Storyboard** → actual 9:16 or 16:9 animated MP4, scene-timed estimated SRT, technical QA JSON. This uses FFmpeg zoom/pan on still images, **NOT diffusion-generated moving AI video**. A GTX 750 is not needed; CPU does the work. Uploaded image versions never silently change old scene assignments.

**Real AI video on a suitable GPU:** Storyline → series/character canon → pinned image references → local ComfyUI image-to-video model → real moving clips → MP4 and QA. GPU and model weights are external requirements and have NOT been validated with real rendered footage.

**Manual video workflow:** Storyline → import/attach user-approved moving clips and narration → FFmpeg episode assembly → estimated SRT and technical report.

## The two workflows

**Creative:** Storyline → Series Bible → Episode Outline → Shot List → Reference Assets / Voices → AI Video Generation → Timeline → Narration, SFX, Captions → QA → Export.

**Hardware-safe:** Storyline → Series Bible → Episodes → Edit shot list → Import existing/generated clips → Assemble/export locally. Works independently of a paid inference provider. Generative engines are optional and must report availability instead of silently substituting slides.

## Development stage and real-output quality

**This is a foundation/prototype, NOT a finished Google Flow competitor.** It has basic real-footage stitching, but not an end-to-end automatically generated cinematic episode: natural bilingual narration, multitrack sound design, subtitles, consistently generated characters, and subjective video-quality QA are still missing. Passing automated FFmpeg tests or packaging a Windows EXE does **not** mean the export looks good.

**Current machine note:** GTX 750 GPU (older Maxwell, typically very low VRAM) with Ryzen 5 5600G / 16GB RAM. The app performs a local `nvidia-smi` GPU check and clearly warns for GPU configurations unsuitable for Wan2.2 5B. CPU-side scripting and existing video editing still work; local Wan2.2 generation requires a more capable GPU. Read [Quality Gates](docs/QUALITY_GATES_2026_11_23.md) before calling this production-ready.

### Real image-reference input for ComfyUI

For compatible local image-to-video workflows, **approved scene/character image paths** are now uploaded through ComfyUI's local image API and passed into an explicit {{REFERENCE_IMAGE}} LoadImage placeholder. A missing placeholder **blocks generation** rather than falsely claiming that a reference was applied. Supports PNG/JPEG/WebP, one reference image per basic workflow. This is an actual media handoff but character identity and visual quality still require human review and a compatible GPU. See [Windows reference setup](docs/WINDOWS_SETUP.md).

### Narrative-aware story structure (new series only)

The story planner now weighs **paragraph/scene endings, sentence boundaries and modest turning-point cues** instead of arbitrarily splitting exactly every N words. It records hook/ending excerpts and rough beat-position metadata, verifies every original word remains included, and leaves already-edited existing series untouched. This is a **deterministic heuristic**, not a deep AI evaluation of plot quality; Ollama shot direction remains optional.

### New quality-first implementation

- Scene-specific character, wardrobe, location, world and style text canon is composed into the **actual ComfyUI prompt**. Identity is not guaranteed without reference-image support.
- Scene-local optional human or locally generated audio tracks are accepted and combined with quieter source sound. An overlong narration **blocks export** instead of being silently cut.
- Click **Check Episode Quality** to validate actual footage duration, narration, aspect ratio, caption speed and missing assets before render.
- Every successful rendered episode now includes an **estimated SRT subtitle file** and JSON **technical QA report**. The subtitles are scene-proportional, not forced speech alignment; review them before publishing.

[Competitive research: Flow vs Runway vs Kling vs LTX Desktop](docs/COMPETITIVE_RESEARCH_2026_11_23.md).


## Why not claim Google Flow parity yet?

Google Flow supports prompt-to-video, start/end frames, reusable visual ingredients, scene building, and extending. Many advanced features depend on a subscription or credits. We can reproduce its *workflow ideas*, not Google's proprietary Veo/Omni generation quality using only an APU. Open weights are free to download, but compute, storage, and some community licenses may not be free. See research file.

## Intended local stack

- **Story LLM:** Ollama with Qwen3-4B (Apache-2.0), used for optional **per-episode cinematic shot suggestions**. The initial episode segmentation is currently deterministic.
- **Video:** ComfyUI + Wan2.2-TI2V-5B (Apache-2.0; real text/image-to-video if compatible GPU available).
- **Alternative generation:** HunyuanVideo-1.5 (custom license, >=14 GB VRAM with offload); LTX-2.5 (community license, high VRAM).
- **Image ingredients:** Z-Image-Turbo, FLUX.1-schnell or Qwen-Image (Apache-2.0).
- **Speech:** QnVoice Filipino VoxCPM2 GGUF (commercial permission for bundled synthetic reference per author), English Kokoro (Apache-2.0), optional Piper depending on voice license.
- **Assembly:** FFmpeg/FFprobe local.
- **App:** local server + desktop shell; no authentication tokens sent to external providers.

## Quick start (Windows)

Clone or download this GitHub repository and double-click `start-windows.bat`. Python 3.12 is recommended; pywebview is optional for a native window (`py -3.12 -m pip install -r requirements-desktop.txt`). Install FFmpeg/FFprobe for actual MP4 export. The editor opens locally at `http://127.0.0.1:8766`. Optional AI Director: run Ollama locally and `ollama pull qwen3:4b`. Optional moving AI footage: run ComfyUI locally with a GPU and an installed real-video model, then import an API-format JSON workflow with `{{PROMPT}}` placeholder. All data saves under your Windows home folder in `AI-Video-Maker`.

A separate [Windows desktop build workflow](.github/workflows/windows-build.yml) packages a portable application folder as a downloadable GitHub Actions artifact; an executable build is not proof of full Windows media/model compatibility. See [setup](docs/WINDOWS_SETUP.md).

## Implementation priorities

1. Persist series, episodes, canon, characters, and shot prompts; never overwrite manually edited canon.
2. Plug-in model adapters, local readiness checks, explicit license info and resource profiles.
3. ComfyUI workflow templates with controlled substitutions, job queue, failure recovery, and clip metadata.
4. Footage assembly with reliable audio/video timebases and preview/export parity.
5. Episode continuity checks, scene re-generation, captions, sound and finished-video QA.
6. Desktop packaging and Windows integration testing.

**Research references:** see [docs/RESEARCH_2026-11-23.md](docs/RESEARCH_2026-11-23.md).
