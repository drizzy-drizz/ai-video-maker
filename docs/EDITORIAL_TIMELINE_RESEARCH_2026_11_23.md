# AI Video Maker: Editorial Timeline Engineering Dossier

Reviewed: 2026-11-23. Source: official/open project documentation and native FFmpeg filters. Technical correctness is not a claim of video-quality parity with commercial generators.

## Competitive engineering research

Commercial video-generation applications combine advanced models with reliable editorial workflows. The open-source app can differentiate on multi-episode canon, editability, local control, reproducibility, and output parity on machines that cannot run large diffusion models.

Existing foundation had character references and clip assembly but NO real source trims, no reorder controls and hard-cut-only footage rendering. That causes wrong story pacing even when source clips are good. Prioritize a real edit decision timeline before chasing additional models.

Primary documentation:
- [FFmpeg xfade](https://ffmpeg.org/ffmpeg-filters.html#xfade) is the real video-transition filter. Inputs must use consistent frame dimensions, pixel format, frame rate and timebase; normalize with FFmpeg filters first.
- [FFmpeg acrossfade](https://ffmpeg.org/ffmpeg-filters.html#acrossfade) joins audio with matching overlaps; video-only wipes with hard audio cuts are not production quality.
- [Academy Software Foundation OpenTimelineIO](https://opentimelineio.readthedocs.io/en/latest/index.html) represents editable decisions with clips/tracks/transitions but is NOT a renderer. Native persistent shot JSON is currently the timeline authority; a real OTIO export adapter remains optional future work.
- [whisper.cpp CLI](https://github.com/ggml-org/whisper.cpp/blob/master/examples/cli/README.md) can output rich JSON token timestamps; a documented [VAD token timebase mismatch issue](https://github.com/ggml-org/whisper.cpp/issues/4046) makes blind word-for-word captions unsafe. Do NOT advertise automatic precise Filipino speech alignment without real validation.

## Fully integrated real-moving-footage timeline design

1. Attach or generate genuine MP4/MOV/MKV/WebM video sources to scene IDs; original assets are never rewritten.
2. Reorder shots with earlier/later actions; media, captions and narration follow the same scene IDs. Set source in/out trims. Missing out point means full source duration.
3. A real ffprobe-based timeline plan rejects non-finite/negative/too-short trims, unsupported effects, unsafe transitions, too-long narration and captions that conflict at transition boundaries.
4. Outgoing transitions are cut, fade, wipe-left or slide-left, each with 0.10–1.50-second overlap capped at 45% of adjacent trimmed clips. Both video AND audio get corresponding crossfades.
5. FFmpeg normalizes every clip to 24fps, 720x1280 or 1280x720, H.264/AAC; incoming narration is delayed until its incoming transition finishes. Outgoing narration must finish before its transition. The source content is untouched.
6. Consecutive hard cuts are joined with concat copy. Transition boundaries are encoded using xfade video and acrossfade audio. This is NOT a frontend-only CSS animation.
7. Caption starts use actual encoded timeline offsets, not sum of untrimmed source durations. Manual cues are exact and validated outside the ambiguous half-transition windows; approximate cues are confined to solo-visible windows. A single SRT feeds both exported file and optional libass burn-in.
8. Final technical quality report includes planned source in/out, timeline start/end, transition count, expected duration, audio streams and frame dimensions. Last published MP4 is not replaced if new output QA fails.
9. Shot source preview streams actual local video with byte-range requests. Preview of the final MP4 after Render Episode is the actual authority for audio/caption/transition appearance, not an approximate browser simulation.

## Limits and next milestones

This full edit pipeline currently applies to real moving-video scenes. CPU still-image motion storyboard is an independent export mode and does not automatically inherit the real-video crossfade feature. Browser source preview is not a perfect live simulation of FFmpeg effects.

The app is not a full multi-track drag/drop NLE. Speed ramps, keyframing LUTs, source-wide AI event detection, advanced sound effects, shot-to-shot visual identity QA, end-to-end on-device video generation on GTX 750, and real spoken-word alignment remain open.

FFmpeg integration tests verify technical render, not visual storytelling or generated-voice naturalness. GTX 750 remains unsuitable for modern Wan video diffusion.

## Release gates for this workstream

- Valid trimmed/reordered footage produces correct-length MP4 while originals remain unchanged.
- Multi-shot cuts and at least two video/audio transition types export valid footage with audio and no blank frames.
- Word caption cues cannot overlap transition boundaries or exceed real edited footage; preflight catches errors.
- Old untrimmed footage projects hard-cut and pass previous media tests.
- Final editor playback uses encoded exported footage, not fake simulation.
- CI and Windows packaging pass; native Windows model/video qualitative tests remain outstanding.
