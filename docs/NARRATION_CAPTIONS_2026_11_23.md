# Narration + Editable Captions — local workflow

Updated: 2026-11-23. No required paid APIs. Engine installs and voice weights are not bundled.

## What works after installing locally licensed models

- **Piper CLI with ONNX voice model**. English default if configured; Filipino ONLY if the user supplies a legitimately licensed, matching Tagalog ONNX voice and its adjacent .onnx.json configuration. Do not assume every hosted voice is cleared for monetization.
- **VoxCPM2 GGUF via voxcpm2-cli** (llama.cpp-omni) with matching BaseLM and acoustic GGUF files. One Filipino candidate is QnVoice: https://huggingface.co/CholoAsis/qnvoice-filipino-voxcpm2-gguf . Review the chosen model and reference WAV rights before publishing.
- Every scene has an optional Generate Local Narration button. The local process runs without a shell, checks the resulting WAV with FFprobe, saves a versioned output under the user's workspace, and attaches it to the original scene only if the script has not changed. The user can listen to the WAV in an embedded audio player.
- The app never silently substitutes another voice, calls a paid API, or claims high-quality speech unless the user actually listens to it.

## Piper setup (Windows PowerShell example)

Install the free Piper executable and a voice model whose specific license permits intended commercial use. Save an adjacent ONNX JSON config. Then set, in the same shell that launches the desktop app:

    $env:AIVM_PIPER_EXE = 'C:\Tools\piper\piper.exe'
    $env:AIVM_PIPER_EN_MODEL = 'C:\Models\my-permitted-english.onnx'
    py -3.12 app.py --desktop

Optional Tagalog Piper model (ONLY if legally usable):

    $env:AIVM_PIPER_TL_MODEL = 'C:\Models\my-permitted-filipino.onnx'

Official command syntax: https://tderflinger.github.io/piper-docs/guides/usage/

## Filipino VoxCPM2 setup (Windows PowerShell example)

Build/install llama.cpp-omni voxcpm2-cli, obtain compatible BaseLM GGUF and acoustic GGUF. Then set:

    $env:AIVM_VOXCPM2_EXE = 'C:\Tools\voxcpm2-cli.exe'
    $env:AIVM_VOXCPM2_BASE = 'C:\Models\VoxCPM2-BaseLM-Q8_0.gguf'
    $env:AIVM_VOXCPM2_ACOUSTIC = 'C:\Models\VoxCPM2-Acoustic-F16.gguf'

Optional, permitted reference WAV for synthetic voice:

    $env:AIVM_VOXCPM2_REFERENCE = 'C:\Models\permitted-reference.wav'

The application constructs the native CLI arguments: -t (scene text), -o (output WAV), optional -r (permitted reference WAV), then the two GGUF files. It doesn't download files or choose proprietary hosted inference. Actual model speed, voice quality, and Tagalog comprehension must be tested on your hardware. GTX 750 cannot provide modern high-end TTS or video-model acceleration.

Official CLI example: https://github.com/OpenBMB/VoxCPM (on-device inference)

## Shot narration workflow

1. Paste/create a Tagalog or English series and open Episodes + Shots.
2. Sidebar OFFLINE VOICE STATUS shows which local engines/models are present and exactly why a candidate is missing.
3. In each scene choose Auto, Piper or VoxCPM2, confirm voice/model/reference usage rights, and click Generate Local Narration.
4. Review the resulting WAV via the scene audio player; reject, revise, or use your own recorded voice if needed.
5. CPU image-motion storyboard extends the scene to fit voice duration. Actual moving-video export blocks too-long narration to avoid cutting words off.

## Exact manual subtitle timing

Each shot now has an optional timecode editor. Format is relative to that shot in seconds, for example:

    0.00 --> 1.35 | Kumusta! Ito ang simula.
    1.35 --> 2.90 | May kailangan akong sabihin.

- Scene-level cues cannot overlap, contain empty text, or go beyond footage/scene duration; validation runs in both UI and Python.
- Leave the shot's caption field empty for explicitly **approximate** word-proportional timing.
- At episode level choose **SRT sidecar only** or **Burn same SRT into MP4**. The latter renders final subtitle pixels using FFmpeg's libass subtitles filter and plays that resulting MP4 directly in the editor.
- Sidecar SRT and rendered MP4 use identical cues; it is not separate web CSS pretending to represent export.
- Manual timings are exact, but automatically inferred cues are NOT forced speech alignment. No Apple emoji promise or per-word karaoke claim.

Official FFmpeg subtitle-filter documentation: https://www.ffmpeg.org/ffmpeg-filters.html

## Safety, release state and remaining priorities

User must own/permit scripts, voices, likenesses and music. Explicit consent is required when using voice references. The app reports readiness and media-tech validation separately from subjective speech/visual review.

**Not yet claimed complete:** downloaded model installation/benchmarks, actual VoxCPM2/Piper checkpoint Windows listening validation, full automatic video diffusion on compatible GPU, Filipino/English true ASR forced alignment, professional multitrack editor, per-episode shot coherence human QA and final monetization/publishing acceptance.
