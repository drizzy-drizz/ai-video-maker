# Windows setup (v0.1 research-first foundation)

## Prerequisites
- Windows 10/11 x64.
- Python 3.12 (Python 3.11+ should also work). No paid API key needed.
- FFmpeg + FFprobe on PATH for MP4 assembly.
- Optional: \`py -3.12 -m pip install -r requirements-desktop.txt\` for a native app window using WebView2/pywebview. Otherwise it opens in a browser at localhost.
- Optional: Ollama + Qwen3-4B locally (`ollama pull qwen3:4b`) for non-destructive **AI Direct Episode** shot and title suggestions. Initial episode segmentation remains deterministic.
- Optional: ComfyUI on localhost port 8188, loaded with a *real video-generating* model workflow (e.g. Wan2.2-TI2V-5B) to enable moving AI shots.

## Launch
Run \`start-windows.bat\`. Or \`py -3.12 app.py --desktop\`, or \`python app.py\` for the browser-hosted editor.
Data persists at \`%USERPROFILE%\\AI-Video-Maker\`. Set \`AIVM_DATA_DIR\` to customize.
The server binds only to \`127.0.0.1:8766\`.

## Current verified workflows
1. Paste any storyline and choose Tagalog or English. The app builds editable episodes and shot plans and saves the original text verbatim.
2. Open Series Bible and save canon, world, style and character reference descriptions.
3. Edit prompts shot by shot. You can import existing footage by entering its absolute local filename and saving.
4. If using ComfyUI, open its workflow, export it in **API JSON** format (not the editor graph layout), replace **positive prompt text** with \`{{PROMPT}}\`. Optionally set negative prompt to \`{{NEGATIVE_PROMPT}}\` and seed to \`{{SEED}}\`. Paste JSON into the app's right sidebar and install. Start ComfyUI locally with matching model weights. Generate each shot from the episode pane; outputs must be video (MP4/MOV/WebM), not a PNG.
5. Click Render Episode to normalize resolution/audio and concatenate moving clips into a MP4. If any scene is missing a real clip, export **fails with a clear error** rather than creating a slideshow.
6. A completed export is playable and downloadable through the Episode Export viewer. It also produces a scene-proportional SRT file and a machine-readable technical QC JSON report; subtitle words are **not yet speech aligned**.
7. When Ollama and Qwen are installed, click **AI Direct Episode (Local Qwen)**. Review suggested shot directions individually and apply only the ones you want. This never automatically overwrites manual prompts.

## Full real-video editorial timeline (new)

This path uses actual **moving footage**, from your own files or a compatible local ComfyUI model. The separate CPU image-motion storyboard remains distinct.

1. Attach at least one supported MP4/MOV/MKV/WebM video clip to each shot in the Episodes + Shots tab, or generate true footage using ComfyUI on sufficient hardware.
2. Use **Move earlier/later** to rearrange shots without changing media files. Set **Trim in** (seconds from source start) and optional **Trim out** (blank = original video end).
3. For each boundary choose **Hard cut**, **Video + audio fade**, **Wipe left + audio fade**, or **Slide left + audio fade**. Transition duration must be 0.10–1.50 seconds and less than 45% of either neighboring shot.
4. **Preview Source Trim** plays the original selected clip using local byte-range playback; it is not an imitation of FFmpeg crossfade. Click **Check Timeline Timing** to inspect real source times, episode offsets and full duration.
5. Add optional narration, licensed music, manual or approximate captions. Crossfades delay the incoming narrated line until its transition ends, and outgoing narration must fit before its outgoing fade. The app blocks unsafe narration and manually timed subtitles that overlap boundaries.
6. Click **Check Episode Quality** to surface edit and media problems. Then **Render Edited Episode**. FFmpeg actually normalizes H.264/AAC clips and combines them with video xfade and matched audio acrossfade.
7. Playback the **final encoded MP4** for the real transitions, audio and burned subtitles; download MP4, SRT and technical QA JSON. The QA report lists actual timeline offsets and transition types. Rendering is non-destructive; your raw video files are never rewritten.
8. Editing the timeline while a render is running invalidates that job's saved revision, rather than publishing stale footage over the current edit.

The exact full-media regression and install requirements are documented in [Editorial Timeline research](EDITORIAL_TIMELINE_RESEARCH_2026_11_23.md). Model-generated video quality still needs real GPU and human review. Large episodes with many sequential crossfades can take substantial CPU time.

## Voice and caption finishing (new workflow)

- [Narration + Captions installation/configuration](NARRATION_CAPTIONS_2026_11_23.md) documents the optional **Piper** and **VoxCPM2 GGUF** offline engines. You must install a compatible and permitted voice/model externally; the app does NOT auto-download weights and will show missing-engine details.
- Each shot now has **Generate Local Narration** (explicit license consent), a WAV playback control for generated voices, and a manual-caption editor. Leave manual cues blank to continue using explicitly approximate subtitle timing.
- For exact manual cues, enter one line per relative time interval, for example: 0.00 --> 1.50 | Magandang gabi. Overlaps and shot overruns are rejected before export.
- At the episode level select sidecar SRT or **Burn captions into final MP4**. The same cues are used for both the subtitle file and video burn-in. Burn-in requires FFmpeg libass and causes a final re-encode.
- This is a full editor/export integration, **not** a claim that models are preinstalled or the Filipino/English speech generated on the user's machine has been human-validated.

## Coding-first workspace additions (not yet release-validated)

This phase is explicitly focused on implementing features before running the consolidated test/build cycle. **Application CI and Windows packaging are temporarily manual-trigger only. Do not treat previous Windows EXE artifacts as containing the newest features.** Read the [current handoff](CODING_FIRST_CONTINUATION_2026_11_23.md) for exact status and deferred acceptance steps.

Use Episodes + Shots to Duplicate, Split or Archive/Restore a scene. Splits require a time within the trimmed shot and a script word boundary. Manually timed captions and sound effects are rebased safely; crossing cues or existing narration block the split rather than discarding sound. A scene can have unlimited-version video takes, previews, approval and alternate take selection.

For real-model production, choose a compatible local ComfyUI API workflow. The new episode controls can generate missing videos or generate still-image drafts, retaining each output. Model-generated assets require user quality and rights approval before using them in a finished export. The GTX 750 cannot practically run modern high-end video diffusion.

Music and sound: The episode has a local audio import picker, a reusable rights-cleared music library, song start position, gain, loop and fades; every scene has editable timed SFX cues that use library tracks or user-provided audio paths. Actual mix outputs are produced by FFmpeg during real-video or CPU-storyboard render.

History/Recovery stores recent project JSON revisions; Portable Project Backup writes a full media .aivm.zip. Importing restores into a different series ID instead of overwriting your existing work. ZIP contains referenced media, **not external model checkpoints or installed programs**.

**These paths have been integrated into code but have not undergone this batch's full tests or Windows builds**, per user request.

## Complete CPU motion-storyboard workflow

This is **an actual video file made by animating existing still images**, not an AI video generator. It runs on CPU with standard FFmpeg; it is intended for concept/episode preview and optional stylized faceless videos.

1. Run the Windows app and create a new English or Tagalog series from your storyline. Series Bible and episodes remain editable.
2. Open **Asset Library**; use the native file selector to import PNG/JPEG/WebP pictures (max 25MB per image). Select accurate rights (original, licensed, permission, public domain), and optionally add source credit. The app saves a managed, SHA256-checked copy under your project. Replacing a reference creates **new version**, preserving existing pinned IDs.
3. Open **Episodes + Shots**, select an episode, and set **Pinned library image** for **each** scene. Optionally assign saved images to characters via reference_asset_id in the Series Bible character JSON for automatic fallback.
4. Choose zoom in/out, pan left/right, or still movement, and edit shot duration as needed. For existing narration, optionally type a local audio file path into each scene's narration field. The app automatically extends a shot to fit the full audio; it never trims or cuts off spoken lines.
5. Optional licensed soundtrack: enter its local WAV/MP3/M4A/FLAC/OGG path and **explicitly confirm music rights**. This soundtrack is mixed at conservative volume in both CPU motion-storyboard and real moving-video episode exports.
6. Click **Check Images** to validate every scene reference and narration. Click **Render Motion Storyboard**. Progress/failure appears under Background Jobs.
7. Review the generated video in the separate Motion Storyboard Preview. Download the **MP4, estimated SRT, and technical QA JSON**. The output is separate from genuine ComfyUI-generated moving clips. The original storyline and real-footage edit slots are unchanged.
8. Important: SRT subtitles are **estimated from text and duration, not speech-aligned**; check the captions manually before posting. A technical QA report checks codec, time and frame dimensions, not emotional storytelling or photorealism.

Automatic image creation, face-locking, natural voice synthesis and Google Flow-level video models still require separately installed free local models and compatible GPU memory. The GTX 750 is not enough for modern video diffusion.

## Natural episode boundaries

New projects preferentially split at paragraph breaks and sentence boundaries near the selected episode word target, preserving the original word order (including Tagalog). Each episode records its opening/ending source excerpt to aid later recap and cliffhanger development. The system **does not** claim reliable automated emotional payoff detection yet. Existing user-edited series are never automatically re-planned when the app upgrades.

## New (quality-first batch)

- Define your recurring characters in Series Bible as JSON objects (name, appearance, wardrobe, continuity). Assign a matching name to any shot, then **Preview Canon-Bound AI Prompt**; the same text conditioning is used when launching a video generation job. This is NOT image-reference identity locking.
- Supply an existing local WAV/MP3/M4A/FLAC/OGG narration audio file per scene. The renderer lowers any source sound under it and checks the full voice fits within the video. Too-short shots are blocked, not trimmed.
- **Check Episode Quality** runs local ffprobe preflight for missing videos, audio overrun, extreme speech pace, aspect mismatch, duplicate footage and basic series-bible completeness.
- Successful export includes separate SRT estimated captions and a technical QC report. Manually watch for wrong speech/caption alignment before Facebook publication.

## NOT implemented yet
- Advanced AI-chosen episode boundaries, cliffhanger structure and holistic episode writing (Qwen currently suggests per-shot direction and title).
- Built-in Wan2.2 API JSON template, reference image inputs and image generation.
- Voice generation adapters for locally installed Piper/VoxCPM2 and MP4 burned-caption workflow are now implemented, but **real model performance and listening quality on Windows remain untested**. True forced word-alignment, licensed SFX libraries and full multitrack sound editing are still open.
- Non-destructive multitrack editor, shot extension, character drift QA and packaging a signed standalone .exe.
- Native Windows integration tests. GitHub Actions CI exercises source and FFmpeg in Linux; that is not a Windows GPU validation.

## Reference images → actual ComfyUI image-to-video

This is the **I2V image handoff**, not a finished visual character consistency scorer. It uses only the local ComfyUI upload API.

1. In **Series Bible**, create recurring cast entries with a name, consistent description and an optional absolute local reference_image path pointing to a PNG/JPG/WebP image. Or put a scene-specific path in the new **Approved character reference image** input.
2. In ComfyUI, create a genuine image-to-video workflow (with an appropriate *LoadImage* node and the model installed). Export **API-format JSON**. Set the LoadImage filename/input to {{REFERENCE_IMAGE}} and the positive prompt to {{PROMPT}}.
3. Install the JSON in AI Video Maker and choose **Generate Moving Shot**. The app picks the explicit scene reference first, otherwise the first matching character's image. It checks the image signature/size, uploads it to the **local** ComfyUI /upload/image endpoint, and supplies the resulting actual filename to the workflow graph.
4. If an image reference is provided but the API workflow lacks {{REFERENCE_IMAGE}}, generation fails loudly instead of pretending the reference was used. If the workflow requires a reference but no image is attached, generation also fails.
5. The existing GTX 750 preflight still blocks modern local video generation. Use a compatible GPU before testing this pipeline end to end.
6. Multiple characters require a composite reference or advanced multi-input workflow; the basic implementation only supplies one reference image to the first LoadImage placeholder. Character likeness is **not guaranteed** by either text or reference conditioning.

This does not copy images into project storage or ensure a persistent approved reference asset catalog. Those are separate upcoming features.

## Verified CI status (2026-11-23)

- [Linux media, narration, captions and API CI — 45 tests passed](https://github.com/drizzy-drizz/ai-video-maker/actions/runs/45061593330)
- [Latest Windows Python runtime/UI/story-save smoke test and portable app packaging PASSED](https://github.com/drizzy-drizz/ai-video-maker/actions/runs/45061593343) (download GitHub Actions Artifacts > AI-Video-Maker-Windows-portable)
- These tests DO NOT validate a real AI diffusion model on the GTX 750, a native double-click GUI session on the user's PC, full quality of Tagalog/English TTS, or any advanced edited film output.

## Portable Windows build

Use GitHub Actions → **Windows desktop build** → download the `AI-Video-Maker-Windows-portable` artifact after a successful run. Extract the entire folder and run `AI-Video-Maker.exe`; do not run just the EXE without its bundled files. The project does not bundle FFmpeg or large Hugging Face model weights. Windows GPU/full render acceptance testing remains pending.

## Model reality check
Wan2.2 5B uses GPU-heavy diffusion; the reported Ryzen 5 5600G, 16GB RAM and GTX 750 dGPU do **not** provide sufficient modern GPU compute/VRAM. Local generation of full-resolution cinematic model clips is impractical on this setup. Editing, canon, MP4 assembly and importing existing video remain viable.
No paid service is required by this project. Downloading open weights doesn't imply free GPU compute.

See research: \`docs/RESEARCH_2026-11-23.md\`.
