# Competitive research — Google Flow, Runway, Kling and LTX Desktop

Reviewed 2026-11-23. Primary documentation only. This is a *feature comparison*, not a claim that we reproduce proprietary inference model quality.

## Competitive observations

| Product | Official capabilities (2026) | Product lesson | Our status |
|---|---|---|---|
| [Google Flow](https://support.google.com/flow/answer/16353334?hl=en) | Text-to-video, image/frame/ingredient references, editable scene workflows | Keep reusable ingredient IDs, clear scene builder and shot extension pipeline, instead of unrelated text prompts | Canon text conditioning now integrated; real visual ingredients/extension pending |
| [Flow Scenebuilder](https://support.google.com/flow/answer/16935718?hl=en) | Build and extend shots, save start/end frames and reference ingredients | Make outputs and past frames persist across scenes and episodes | Shot files persist; linked keyframes pending |
| [Runway references](https://help.runwayml.com/hc/en-us/articles/40042718905875-Creating-with-Gen-4-Image-References) | Multi-perspective/subject/style references for image generation, more consistent characters/environments | Every recurring named character needs stable, versioned reference assets and an approval/retake workflow | Character names/appearance/canon now injected into real video prompts, but **no image conditioning** yet |
| [Kling 4.0](https://kling.ai/quickstart/kling-4-model-user-guide) | Start/middle/end reference frames, elements and timed character changes | Shot planner should encode actions with time and recurring identities, then pass to compatible backend adapters | Text prompts plus explicit names ready; timed keyframes not implemented |
| [LTX Desktop](https://github.com/Lightricks/LTX-Desktop) | Free/open-source non-linear editor, text-to-video, image-to-video, audio-to-video, extension and retakes, with cloud/paid options for some models | Timebase and editing matter as much as models. Deliver editable production, not just generated clips | Basic scene normalization and concat; no full multitrack editor or local LTX runtime |

**Do not blindly copy competitor code, prompts, image assets or proprietary model access.** Implement original and properly licensed capabilities based on published features.

## Where AI Video Maker can actually differentiate

**1. Multi-episode continuity, not only clips.** Preserve source script, plot canon, world geography, wardrobe, recurring characters and chronology. Use series-scoped versioned character references when introduced; generate each shot with a canonical prompt compiled from scene and Bible rather than independent text. What we did *now*: implement text-based canonical shot compiler; only include relevant cast and locations, prevent universal cast stuffing. Model output may still drift.

**2. Native Filipino/English storytelling.** User pastes the actual story (any genre), not forced horror or AI-written template. Tagalog+English original source is preserved; TTS with compliant licensing still pending. Optional user-provided WAV/MP3/M4A narration is now supported in exports. Script-based captions are **timing estimates**; no forced alignment so do not promise perfect subtitles.

**3. Editing that respects the user.** Local and non-destructive. Keep prompt edits, source text, manual voices, and shot files. AI Director outputs suggestions separately for approval. Multi-track timeline and retake versions are still pending.

**4. Quality gates, not a fake progress bar.** Technical preflight now checks real footage, duration, voice longer than clip, caption speed, aspect mismatch, duplicate clips, missing audio/character bible. It blocks export if source missing or narration would be truncated, not on subjective warning. FFmpeg export now writes a technical postflight JSON report and estimated SRT. It does **not** score cinematic visuals, faces, speech or real watchability.

**5. Honest hardware/cost story.** Runs offline for script/editor/FFmpeg. GTX 750 lacks the VRAM/architecture for modern local Wan; no “free Google Flow-level generation” on that GPU. ComfyUI can optionally accept a real video model on a suitable GPU. Free models are not equal to free compute. The app never calls a paid provider.

## Implementation milestones

**New additional delivery:** The deterministic episode planner now favors natural story paragraph/scene breaks and source-preserving shot coverage, instead of naive fixed-word splitting. It is not a full semantic AI screenwriter; true story-act planning remains open.

### Complete in the new quality-first batch### Complete in the new quality-first batch
- [x] Research current competitors using primary docs
- [x] Scene-specific characters and Bible injected into real-video prompts (text only)
- [x] Scene character assignments and optional narration audio inputs in studio UI
- [x] Actual ffprobe preflight and blocking narration-overrun checks
- [x] Render with optional local voice audio mixed over source audio
- [x] Write timestamped scene-proportional SRT captions and technical QC JSON
- [x] Expose episode preflight, prompt preview and report downloads in UI
- [x] Regression tests, including synthetic FFmpeg footage and voice — monitor CI separately

### Highest priority next batches
- [ ] Character image reference asset import + approved version pinning, with actual I2V model conditioning
- [ ] Better story-structure-based episode boundary selection and preserved context/recaps
- [ ] Commercially usable offline Filipino/English TTS with full practical install and benchmark
- [ ] Speech alignment (WhisperX / aeneas or alternative with tested Filipino alignment) replacing estimated SRT
- [ ] Audio + music tracks, ducking automation, independent level control and subtitle preview/export parity
- [ ] Non-destructive timeline with trim, split, merge, transitions, first/last frame controls, and retake selection
- [ ] Real video generator validated using a proper compatible GPU, character visual consistency checks
- [ ] Full representative Tagalog and English episodes personally reviewed for pacing, coherence, visuals and audio

## Hardware profiles / licensing

Refer to [research dossier](RESEARCH_2026-11-23.md) and [quality gates](QUALITY_GATES_2026_11_23.md). Modern diffusion video models are not suitable for GTX 750. For CPU mode, local planning and clip assembly should remain responsive. An explicitly marked motion animatic is a potential feature but **not implemented or labeled generated video**.

**Meta/Facebook** monetization requires original/rightsholder-compliant video and may require synthetic media disclosure. Model permissions, training/data provenance, music and external voices must be checked per asset.
