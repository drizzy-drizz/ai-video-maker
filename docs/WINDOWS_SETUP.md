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
- Automatically generated natural Tagalog/English TTS, forced word alignment, licensed music/SFX library and burn-in caption preview parity. User-supplied narration audio and rough sidecar SRT are now supported.
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

- [Linux media and API CI — 33 tests passed](https://github.com/drizzy-drizz/ai-video-maker/actions/runs/45060101450)
- [Windows Python runtime, UI/story-save smoke test and portable app packaging passed](https://github.com/drizzy-drizz/ai-video-maker/actions/runs/45060101472)
- These tests DO NOT validate a real AI diffusion model on the GTX 750, a native double-click GUI session on the user's PC, full quality of Tagalog/English TTS, or any advanced edited film output.

## Portable Windows build

Use GitHub Actions → **Windows desktop build** → download the `AI-Video-Maker-Windows-portable` artifact after a successful run. Extract the entire folder and run `AI-Video-Maker.exe`; do not run just the EXE without its bundled files. The project does not bundle FFmpeg or large Hugging Face model weights. Windows GPU/full render acceptance testing remains pending.

## Model reality check
Wan2.2 5B uses GPU-heavy diffusion; local generation on Ryzen 5 5600G APU + 16GB RAM without dGPU will be impractically slow or fail. Editing, canon, MP4 assembly and importing existing video remain viable.
No paid service is required by this project. Downloading open weights doesn't imply free GPU compute.

See research: \`docs/RESEARCH_2026-11-23.md\`.
