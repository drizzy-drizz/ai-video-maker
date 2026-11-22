# AI Video Maker — Quality First Acceptance Gates (2026-11-23)

## Honest status
The existing v0.x is **a prototype**, not a finished Flow alternative. It has editable series/episodes, optional local Qwen direction, ComfyUI API workflow integration, and FFmpeg clip normalization/concatenation, but **NOT** a complete high-quality film generator. The current renderer stitches clips and may output hard cuts, blank/silent background, missing narration and inconsistent character shots. Passing a compiler, Windows PyInstaller build or a synthetic FFmpeg color-video test is **not** evidence of acceptable real episode quality.

## User machine
- Reported NVIDIA **GeForce GTX 750** (older Maxwell compute 5.0 generation, typically 1GB VRAM; some board variants may differ).
- Ryzen 5 5600G, 16GB system RAM (previously reported).
- **Do not automatically install or queue Wan2.2, Hunyuan, LTX or other modern high-memory diffusion models on this GPU**; model memory needs are dramatically higher. GPU detection via `nvidia-smi` is now shown in the app; unknown GPUs must be labelled unverified.
- With the GTX 750, use CPU-based story work and local editing. Real generated motion requires a compatible, adequately resourced GPU in a later setup; free Hugging Face weights alone do not include GPU compute.
- **CPU motion storyboard is now implemented and tested**: approved still image versions, Ken Burns camera moves, optional supplied narration and licensed music, MP4/SRT/technical QA. It is expressly labelled a motion storyboard, NOT diffusion-generated video. Real video generation on the GTX 750 remains infeasible.

## Before calling a release "video making app ready"
### A — Story coherence
- An episode follows the pasted source and clear beginning/catalyst/conflict/payoff; scenes not arbitrarily sliced by word counts alone.
- Character and location identities persist across episodes; maintain appearance/voice/reference versions.
- Every beat has an editable script, shot plan and actual motion footage or a clearly labelled animatic alternative.
- Reference episodes for **Tagalog** and **English**, across at least two genres (e.g. contemporary drama and science fiction); no horror default.

### B — Visual QA
- A shot's person, outfit and location match the canon; no obvious character drift, camera teleport or jump cuts hidden behind fake transitions.
- Real video output uses model-produced moving frames; do not substitute still-image slides without explicit animatic selection.
- Scene duration and frame timing match action and spoken content; each generated shot can be retaken without overwriting approved footage.
- Detect/reshoot visual artifacts, duplicate frames, jitter/flicker, black or blank frames, watermark defects and unsafe/copyright source assets.
- Verify phone-size 9:16 framing and readable captions; ensure 16:9 export is not stretched.

### C — Audio / subtitle QA
- Narrator/character voice is natural, intelligible and language-correct in both English and Tagalog.
- Dialogue pacing is aligned to scenes; no abrupt word cuts or missing lines.
- Music and sound FX rights recorded; audio ducking, peaks and transitions validated.
- Captions accurate, synchronized and equal in preview and exported MP4.
- A missing TTS/music service must be clearly indicated, not silently included in a claim of a complete episode.

### D — Export + reliability
- Source-to-preview and preview-to-export visual/audio parity; frame duration, aspect ratio, audio streams all probed.
- Recovery/resume when video model fails or system runs out of resources; no invisible paid API fallback.
- Final QC report with pass/fail + human review for actual watchability.
- Windows execution with installed model engine and **genuine video clips**. Synthetic test-color footage alone does not qualify.
- Optional portable Windows executable release only after the app starts, saves/loads, handles models, renders and plays correctly on Windows.

## Release labels
- **Foundation**: source planning / editors / clip stitching. CURRENT STATUS.
- **Animatic preview**: **implemented** for approved images with camera moves, narration/music, and standalone MP4/SRT/QA. It is not a generated video model.
- **Generated video beta**: actual model-generated shot clips, rendered audio and captions; model + GPU verified.
- **Production-ready**: multiple completed representative episodes reviewed for story, visuals, audio and continuity; repeatability proven.

## Test plan for GTX 750
1. Confirm true VRAM and NVIDIA driver via `nvidia-smi` (do not assume 1GB in all hardware).
2. Save, reopen and edit a 5-episode Tagalog source and 5-episode English source without data loss.
3. Import *preexisting real MP4* shots, render a 9:16 episode with audio, inspect A/V stream and cut timing.
4. When trying to connect a large model on the GTX 750, show a preflight warning and allow user to stay in planning/editor.
5. Do not advertise one-click cinematic video until narration, consistency, effects, and GPU-capable motion models are properly integrated.

## Sources
- [Official NVIDIA GTX 750 specifications](https://www.nvidia.com/en-us/geforce/graphics-cards/geforce-gtx-750/specifications/)
- [NVIDIA CUDA architecture matrix](https://docs.nvidia.com/datacenter/tesla/drivers/latest/cuda-toolkit-driver-and-architecture-matrix.html)
- [NVIDIA CUDA Toolkit 13 release notes](https://docs.nvidia.com/cuda/archive/13.0.0/cuda-toolkit-release-notes/)
- [ComfyUI Wan2.2 guide](https://docs.comfy.org/tutorials/video/wan/wan2_2)
