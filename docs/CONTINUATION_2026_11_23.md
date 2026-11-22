# CONTINUATION HANDOFF — 2026-11-23 (quality-first batch)

Repo: https://github.com/drizzy-drizz/ai-video-maker — default branch main.

## Goal, nonnegotiables
Build a **general** (no horror-only presets) **Tagalog + English** episodic faceless filmmaking Windows application. Paste an original storyline, preserve it, plan unlimited episodes, enforce character and story canon, generate authentic moving shots with local open models on suitable GPUs, and deliver watchable Facebook reels. No required paid API or cloud, nor dishonest equivalence between free weights and free GPU compute.

User hardware: GTX 750 (VRAM detect at runtime; older Maxwell) + Ryzen 5 5600G and 16GB RAM. GTX 750 is not sufficient for modern local Wan2.2 5B diffusion. Story/shot planning, asset management, imported footage and CPU FFmpeg assembly remain possible.

## Newest finished vertical slice — CPU motion storyboard + managed ingredients (2026-11-23)

- asset_library.py: source+rights-confirmed native file upload with checksum, immutable versions, stable asset IDs, source/rights/credit metadata. Old references never update when new images are imported as a replacement.
- Scene references can be pinned to a managed library image ID; both ComfyUI image handoff and CPU storyboard use the same pinned image. Character Bible can use reference_asset_id.
- animatic.py: **fully separate** image-based Ken Burns motion storyboard generator with per-scene movement and duration, narration audio with automatic extension to avoid speech cuts, optional license-confirmed looping soundtrack, 9:16/16:9 H.264+A​​AC MP4, estimated captions and technical QA. Never overwrites generated-video footage or scene clip data.
- Native upload via local HTTP, new Asset Library tab, shot-level image picker and motion controls, separate preview player, downloadable MP4/SRT/QA, image+audio preflight.
- Tests: **33 automated tests green**, including HTTP image upload/preview, immutable references, actual FFmpeg image→motion MP4, narration, licensed soundtrack for BOTH real-footage and storyboard exports, caption sidecar, and postflight. Linux CI successful at commit `8556e28a7`. [CI run](https://github.com/drizzy-drizz/ai-video-maker/actions/runs/45060101450).
- This is **motion storyboard, NOT AI motion generation**. Genuine video diffusion still requires a newer adequate GPU. No high-end generated-episode quality claims.

## What was actually shipped in latest implementation
- studio_quality.py: per-scene *relevant cast* + Bible (world, visual style, wardrobe, continuity, locations) canonical textual ComfyUI prompt compilation. Text conditioning does not guarantee visual identity.
- Per-scene or character-local reference image paths; PNG/JPG/WebP signature and 25MB checks. With a ComfyUI API graph containing **{{REFERENCE_IMAGE}}** (e.g. LoadImage node), file is POSTed via local **/upload/image** and the returned name is inserted into graph. Block when image exists but graph cannot accept it; block when graph requires missing reference. One-image support; no claimed multi-face consistency or actual GTX750 compatibility.
- studio_quality.py technical *preflight*: missing or unreadable real moving footage, source duration/ratio, duplicate footage, high words/sec, missing voice or narration longer than shot, basic series canon completeness. Only actionable blockers stop export; advisory issues remain reviewable.
- app.py: per-scene *user-provided narration audio* (.wav/.mp3/.m4a/.flac/.ogg) mixed atop original background at 0.18 background gain; video is not truncated to audio duration; speech-too-long shot blocks export.
- scene-normalized MP4 export still uses FFmpeg. Sidecars: scene-timed estimated SRT (NOT ASR/forced alignment) and JSON codec/duration postflight. Successful episode status: rendered_needs_human_review.
- UI: optional audio path, approved reference image path, explicit character names, "Preview Canon-Bound AI Prompt", "Check Episode Quality" with specific warning/blocker rows, subtitle and technical QA download links.
- story_planner.py: source-preserving narrative boundary heuristics for **new** projects, preferential paragraph/sentence/turning point breaks near episode size, shot-level metadata, hook/ending excerpts, no lost original words. Existing series remain unchanged. Not a semantic plot evaluator and not cinematic AI story selection.
- Historical core suite: 26 green. Latest expanded suite: **33 green** at `8556e28a7`. **Windows runtime smoke** now confirms server startup, API story creation/retrieval, and HTTP UI; PyInstaller portable EXE built successfully in [Windows run](https://github.com/drizzy-drizz/ai-video-maker/actions/runs/45060101472). These are still not hardware-level Wan/GTX model tests or human visual-quality reviews.

## Research
- [Competitor feature study](COMPETITIVE_RESEARCH_2026_11_23.md): official Google Flow, Runway References, Kling 4.0, and LTX Desktop.
- [Full model/license study](RESEARCH_2026-11-23.md).
- [Release QA rules](QUALITY_GATES_2026_11_23.md).
- [Windows install and workflows](WINDOWS_SETUP.md).
- [Living master backlog](https://github.com/drizzy-drizz/ai-video-maker/issues/1).

## NEXT IMPLEMENTATION PRIORITY — not claimed complete
1. **Implemented:** Approved immutable reference image library with stable per-version asset IDs, local image picker, rights and hash metadata, and pinned ComfyUI/animatic shots. Multi-character image conditioning and automated visual drift QC remain open.
2. Story-structure AI planner via local Qwen that suggests episode boundaries/cliffhanger with strict source coverage and human approval. Do NOT silently overwrite existing custom edits/timeline.
3. TTS adapters with commercial-use verification: English Kokoro, Filipino VoxCPM2/QnVoice, standalone Windows install checks and actual listening tests.
4. **True speech alignment**; replace estimated SRT with tested forced aligned captions for both Filipino and English, plus burn-in captions matching editor preview. Do not conflate per-scene interpolation with alignment.
5. **Implemented:** Real CPU-only motion storyboard from approved still images with user narration/music, preview, exports and provenance. Upgrade remaining: optional scene transitions and accurate speech-aligned captions.
6. Non-destructive editing timeline with trims/transitions, full music/SFX track controls, A/V parity. **Done in foundation:** optional rights-confirmed soundtrack mix for both actual-moving-video and CPU motion-storyboard exports, serial heavy render lock, atomic QA-passed MP4 replacement, scene narration. Missing: advanced multitrack editor, burn-in captions and speech alignment.
7. Actually generate 2 English + 2 Tagalog coherent episode samples on a modern GPU and human review watchability. No one-shot "Google Flow-quality" claim until visually verified.

## Technical gotchas
- Core server in app.py uses stdlib HTTP loopback; no paid endpoint. Models are **not automatically installed**.
- Story planner is used only when creating a new series; existing JSON projects unaffected.
- ComfyUI image handoff requires **API-format** JSON with placeholder in LoadImage node and a compatible model, not editor layout JSON.
- Current **one-image** reference path feeds one LoadImage placeholder (or many string substitutions, but not distinct character slots).
- All uploaded paths are local; no remote image download or cloud TTS.
- SRT is *estimated*; human review mandatory. Technical QA JSON does not detect facial drift, bad audio, emotional pacing.
- Keep Windows Python3.12 and FFmpeg compatibility. Unit coverage and CI cannot substitute actual Windows render or GPU test.
