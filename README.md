# AI Video Maker — episodic, local-first filmmaking

**Research baseline:** 2026-11-23. **Repository:** `drizzy-drizz/ai-video-maker`.

A general-purpose Windows-first app: paste a Tagalog or English storyline; build a reusable **series bible**; divide it into editable episodes and shots; create consistent characters and scene prompts; generate moving footage through open-weight local models; add voices, captions, sound, and export episodes. **No horror-only presets, mandatory paid API, cloud subscription, or artificial episode limit.**

## Status

- Research and implementation blueprint: **documented** (see [docs/RESEARCH_2026-11-23.md](docs/RESEARCH_2026-11-23.md)).
- Development: incremental; do **not** confuse episode planning, motion-storyboard exports, or image slides with true AI video generation.
- Target platforms: Windows desktop; local network services bound to loopback by default.
- Existing developer hardware context: Ryzen 5 5600G APU, 16 GB RAM, no discrete GPU. That hardware can plan stories and edit/encode low-resolution video, but modern diffusion-based video generation is not reasonably fast on CPU alone.

## The two workflows

**Creative:** Storyline → Series Bible → Episode Outline → Shot List → Reference Assets / Voices → AI Video Generation → Timeline → Narration, SFX, Captions → QA → Export.

**Hardware-safe:** Storyline → Series Bible → Episodes → Edit shot list → Import existing/generated clips → Assemble/export locally. Works independently of a paid inference provider. Generative engines are optional and must report availability instead of silently substituting slides.

## Why not claim Google Flow parity yet?

Google Flow supports prompt-to-video, start/end frames, reusable visual ingredients, scene building, and extending. Many advanced features depend on a subscription or credits. We can reproduce its *workflow ideas*, not Google's proprietary Veo/Omni generation quality using only an APU. Open weights are free to download, but compute, storage, and some community licenses may not be free. See research file.

## Intended local stack

- **Story LLM:** Ollama with Qwen3-4B GGUF (Apache-2.0).
- **Video:** ComfyUI + Wan2.2-TI2V-5B (Apache-2.0; real text/image-to-video if compatible GPU available).
- **Alternative generation:** HunyuanVideo-1.5 (custom license, >=14 GB VRAM with offload); LTX-2.5 (community license, high VRAM).
- **Image ingredients:** Z-Image-Turbo, FLUX.1-schnell or Qwen-Image (Apache-2.0).
- **Speech:** QnVoice Filipino VoxCPM2 GGUF (commercial permission for bundled synthetic reference per author), English Kokoro (Apache-2.0), optional Piper depending on voice license.
- **Assembly:** FFmpeg/FFprobe local.
- **App:** local server + desktop shell; no authentication tokens sent to external providers.

## Implementation priorities

1. Persist series, episodes, canon, characters, and shot prompts; never overwrite manually edited canon.
2. Plug-in model adapters, local readiness checks, explicit license info and resource profiles.
3. ComfyUI workflow templates with controlled substitutions, job queue, failure recovery, and clip metadata.
4. Footage assembly with reliable audio/video timebases and preview/export parity.
5. Episode continuity checks, scene re-generation, captions, sound and finished-video QA.
6. Desktop packaging and Windows integration testing.

**Research references:** see [docs/RESEARCH_2026-11-23.md](docs/RESEARCH_2026-11-23.md).
