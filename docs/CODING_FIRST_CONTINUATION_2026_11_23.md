# Coding-first continuation — 2026-11-23

Repository: https://github.com/drizzy-drizz/ai-video-maker
Branch: main
Status: IMPLEMENTED IN CODE, NOT YET FULLY VALIDATED

## Explicit process change

The user asked for feature implementation before repetitive compile, FFmpeg tests and Windows packaging. BOTH GitHub Actions workflows have been switched to MANUAL-ONLY workflow_dispatch. No new tests or builds have been manually run in this coding batch. At the consolidated acceptance stage, restore automatic CI, run the complete historical+new suite, package Windows, review real films, and request the user's one-shot manual QA.

This is a general (all genres), Tagalog/English episodic film studio with no required paid API. The GTX 750, Ryzen 5 5600G and 16GB RAM can support planning/CPU editing, not modern high-quality local video diffusion.

## New implementation groups — code connected end-to-end; awaiting validation

### Shot editing: scene_workspace.py
- Non-destructive duplicate, source-clock split, reversible archive and restore.
- Splits preserve every script word. Video sources keep correct in/out windows; still-image storyboard halves get matching durations.
- Manual captions are split/rebased only when no cue crosses the boundary. Narration-containing scenes are explicitly blocked from split to avoid losing speech.
- Archive never deletes source media; restoration keeps take IDs, prompts, captions and scene associations. Previous exports remain accessible but are marked stale when edits change.
- Backend routes and per-shot editor controls integrated.

### Immutable video retakes: take_workspace.py
- Browser video picker or existing local path imports genuine MP4/MOV/MKV/WebM with rights declaration, SHA256, duration, dimensions, independent permanent file and version ID.
- Every new ComfyUI video output now gets a unique managed take instead of overwriting old clips. Edits during generation prevent a stale take from silently replacing current footage.
- Take preview, select, provenance, explicit approval and review-required generated-video preflight. Compatible trims are retained on take switch; incompatible trims generate a visible reset notice.
- One-click missing-shot episode video batch is resumable: existing footage is skipped, each success is saved, retries continue missing clips. Actual compatible GPU/model remains required.

### Local scene-image drafts: app.py and asset_library.py
- Single-scene and episode-wide ComfyUI SaveImage workflows, with actual still-file download/validation, canonical scene/character prompt, seed, workflow and optional real reference conditioning.
- Save model output as generated-unverified image draft in immutable asset library, not as a fake approved character asset.
- Preview and approve per scene or in Asset Library. Rendering/reference resolution forbids unapproved drafts. No model is automatically installed.

### Project history: revision_workspace.py
- Previous project JSON states are backed up atomically on meaningful changes, SHA256 checked, bounded to 60 snapshots (no huge media duplication).
- History/Recovery studio tab lists and restores revisions. Restore takes a snapshot of the current state before applying the old edit.
- Not a substitute for complete media backup; see portable ZIP.

### Full portable ZIP: portable_workspace.py
- Export a .aivm.zip containing project decisions, actual referenced media, immutable takes, images, voice files, music and existing rendered outputs/sidecars.
- Each file is hashed and named in a manifest; ZIP64 stream file writes rather than storing entire movies in memory.
- Import into a NEW series ID, remap managed asset/take/music/narration/export paths, verify SHA256 and size, reject unexpected ZIP members and restrict extraction to the imported series private workspace directories.
- UI file picker import, background progress, history backup list and portable ZIP download.
- Does not include model weights, local FFmpeg, ComfyUI or Ollama runtimes.

### Precision soundtrack: music_workspace.py, animatic.py and app.py
- Unlimited-by-disk local audio library: WAV, MP3, M4A, FLAC, OGG, OPUS, AAC. Browser picker or local path import, rights confirmation, file checksums and duration.
- Library track selection and audio player.
- Both genuine-video and CPU storyboard FFmpeg exports use the saved start position within the song, editable gain, loop mode, fade-in and fade-out. Music rights and valid timing are checked.
- Songs are reusable across episodes without recreating edit recipes.
- Music library media is included in portable transfer.

### Scene-level audio effects: sound_effects.py
- Multiple independent timed SFX cues per shot, with existing licensed audio-library source or own local file, cue offset, gain, explicit rights check, and cue removal.
- Real-video FFmpeg normalized segments receive mixed SFX BEFORE audio/video transitions; CPU motion storyboard segments use the same effect mix function.
- Effects exceeding the available scene tail receive a short fade rather than abrupt cutoff. Audio inputs are not modified.
- Media preflight checks rights, path, offset, actual duration and gain. QA includes SFX count.

## Existing features kept

- Source-preserving story planner, editable episodes and shot prompts, Series Bible, approved image references.
- Local optional Ollama/Qwen directing suggestions, ComfyUI API video handoff, character prompt canon, local model readiness.
- Piper/VoxCPM2 offline voice adapters (not bundled); batch narration and generated WAV listen player.
- Exact manual captions, estimated caption fallback, optional FFmpeg libass MP4 burn-in and actual MP4 preview.
- CPU motion storyboard clearly NOT labelled as video diffusion, real FFmpeg cuts/xFade/audio transitions, final technical QA and staged MP4 publication.

## NOT validated / important limitations

- This batch has NOT been compiled, tested or built; do not state a passing test count for the new code. There may be defects requiring the consolidated test pass.
- Current GTX 750 cannot practically run modern high-quality video diffusion. Free model weights do not mean free GPU compute. No high-end synthetic visuals or voice naturalness has been tested here.
- Full drag-and-drop multitrack editor, automatic word-level Filipino/English speech alignment, deep AI plot/payoff reasoning, persistent background job recovery, lip-sync and visual identity consistency scoring remain future work.
- Imported music/video rights and image/video-model licenses require user verification; face/voice likeness consent cannot be inferred.
- Reusable globally installed ComfyUI workflow JSON and large model checkpoints are not packed into portable ZIP.

## Single consolidated acceptance pass (deferred)

1. Re-enable automatic CI and Windows packaging after the user agrees to feature freeze.
2. Static checks for all Python modules and studio JS; full historical regression suite.
3. New API tests for shot split/duplicate/archive/recovery, take versions/approval, image drafts, music and SFX rights, revision rollback.
4. ZIP round-trip across multiple episodes, duplicate media contents, imported songs, original external footage, frozen voice references and final exports.
5. Real FFmpeg exports for trims, crossfades, music start/gain/loop/fade, shot SFX and burn-in subtitle parity.
6. Windows runtime, file uploads/downloads, genuine voice-model and compatible ComfyUI model benchmarks, human review of Tagalog+English episodes.
7. Fix failures, produce final Windows artifact, then user performs ONE manual comprehensive test.

## Next coding priorities, not falsely marked done

- True multitrack drag/drop timeline with sound waveforms, split/merge across audio/video layers and richer keyframe controls.
- Source-grounded semantic act/plot AI planning and recurring character look-sheet generation.
- Actual tested automatic Filipino/English speech-to-word alignment and production captions.
- Persistent cancelable/resumable task scheduler, comprehensive published-output visual QA.
- Real I2V/video generation and continuity evaluation on an appropriate modern GPU.

Keep every new implementation and continuation update on main, with clear pending-validation status. Do not run repetitive automated tests or builds during the user-selected coding-first period.
