# Windows setup (v0.1 research-first foundation)

## Prerequisites
- Windows 10/11 x64.
- Python 3.12 (Python 3.11+ should also work). No paid API key needed.
- FFmpeg + FFprobe on PATH for MP4 assembly.
- Optional: \`py -3.12 -m pip install -r requirements-desktop.txt\` for a native app window using WebView2/pywebview. Otherwise it opens in a browser at localhost.
- Optional: Ollama + Qwen3-4B locally for a future AI writer adapter. The current initial segmentation is deterministic, not an LLM result.
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
6. A completed export is playable and downloadable through the Episode Export viewer.

## NOT implemented yet
- Integrated Ollama AI episode enhancement (the model entry is a research choice).
- Built-in Wan2.2 API JSON template, reference image inputs and image generation.
- Natural Tagalog or English AI narration, alignment, music, sound design, speech captions.
- Non-destructive multitrack editor, shot extension, character drift QA and packaging a signed standalone .exe.
- Native Windows integration tests. GitHub Actions CI exercises source and FFmpeg in Linux; that is not a Windows GPU validation.

## Model reality check
Wan2.2 5B uses GPU-heavy diffusion; local generation on Ryzen 5 5600G APU + 16GB RAM without dGPU will be impractically slow or fail. Editing, canon, MP4 assembly and importing existing video remain viable.
No paid service is required by this project. Downloading open weights doesn't imply free GPU compute.

See research: \`docs/RESEARCH_2026-11-23.md\`.
