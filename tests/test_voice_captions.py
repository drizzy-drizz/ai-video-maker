"""End-to-end no-paid-API narration adapters and exact caption/MP4 parity tests."""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import app
import caption_engine
import studio_quality as quality
import voice_engine


def make_wav(path: Path, seconds=1.1):
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(16000)
        out.writeframes(struct.pack("<h", 200) * int(seconds * 16000))


class CaptionEditorTests(unittest.TestCase):
    def test_manual_round_trip_and_exact_srt(self):
        raw = "0.00 --> 1.25 | Magandang umaga.\n1.25 --> 2.30 | Hello, world."
        cues = caption_engine.parse_cue_lines(raw)
        self.assertEqual(len(cues), 2)
        self.assertEqual(caption_engine.parse_cue_lines(caption_engine.cues_as_lines(cues)), cues)
        srt, meta = caption_engine.build_srt([{"caption_cues": cues, "script": "unrelated script"}], [2.3])
        self.assertEqual(meta["caption_timing_mode"], "manual")
        self.assertEqual(meta["estimated_cues"], 0)
        self.assertIn("00:00:01,250 --> 00:00:02,300", srt)
        self.assertNotIn("unrelated script", srt)

    def test_mixed_manual_and_approximate_scene_timings(self):
        scenes = [{"script": "Hey there.", "caption_cues": [{"start": 0.2, "end": 1.0, "text": "Welcome"}]},
                  {"script": "Bumalik ka na rito ngayon."}]
        srt, meta = caption_engine.build_srt(scenes, [1.5, 2.3])
        self.assertIn("00:00:01,500 --> 00:00:03,800", srt)
        self.assertEqual(meta["caption_timing_mode"], "mixed_manual_and_estimated")
        self.assertGreater(meta["estimated_cues"], 0)

    def test_reject_bad_cues_instead_of_silently_shifting_words(self):
        bad = [{"start": 0, "end": 1.5, "text": "Hello"},
               {"start": 1.1, "end": 2, "text": "overlapping"}]
        with self.assertRaisesRegex(ValueError, "overlapping"):
            caption_engine.validate_manual_cues(bad, 3.0)
        with self.assertRaisesRegex(ValueError, "beyond"):
            caption_engine.validate_manual_cues([{"start": 0, "end": 8, "text": "long"}], 2)
        with self.assertRaisesRegex(ValueError, "expected|Line 1"):
            caption_engine.parse_cue_lines("wrong format")
        with self.assertRaises(ValueError):
            caption_engine.apply_caption_mode(Path("video.mp4"), Path("x.srt"),
                                              Path("out.mp4"), "fake", height=540)

    def test_real_mp4_burned_pixels_and_audio_retention(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("FFmpeg missing")
        if not caption_engine.subtitle_filter_available():
            self.skipTest("FFmpeg build lacks libass subtitle filter")
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.mp4"
            subtitles = root / "manual-captions.srt"
            target = root / "captions.mp4"
            subprocess.run([
                "ffmpeg", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=blue:s=320x568:r=24:d=1.8",
                "-f", "lavfi", "-i", "sine=frequency=420:duration=1.8",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest", str(source)
            ], check=True, capture_output=True, timeout=50)
            subtitles.write_text(
                "1\n00:00:00,000 --> 00:00:01,750\nHELLO, CAPTIONS!\n",
                encoding="utf-8-sig"
            )
            mode = caption_engine.apply_caption_mode(source, subtitles, target,
                                                     "burned", height=568)
            self.assertEqual(mode["mode"], "burned")
            info = quality.media_info(target)
            self.assertTrue(info["has_audio"])
            self.assertTrue(info["has_video"])
            self.assertEqual((info["width"], info["height"]), (320, 568))
            self.assertAlmostEqual(info["duration"], 1.8, delta=0.2)

            def grab_frame(video):
                return subprocess.check_output([
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", "0.6",
                    "-i", str(video), "-frames:v", "1",
                    "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"
                ], timeout=40)
            self.assertNotEqual(grab_frame(source), grab_frame(target),
                                "Burned subtitle pixels must appear in the actual final frames")


class OfflineVoiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.model = self.root / "voice.onnx"
        self.model.write_bytes(b"local voice model for testing")
        Path(str(self.model) + ".json").write_text("{}", encoding="utf-8")
        self.gguf_a = self.root / "base.gguf"
        self.gguf_b = self.root / "acoustic.gguf"
        self.gguf_a.write_bytes(b"base fixture")
        self.gguf_b.write_bytes(b"acoustic fixture")

    def tearDown(self):
        self.tmp.cleanup()

    def fake_piper(self, command, **kwargs):
        self.assertIn("--model", command)
        self.assertIn("--output_file", command)
        self.assertIn("Hello", kwargs.get("input", ""))
        make_wav(Path(command[command.index("--output_file") + 1]))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_voxcpm(self, command, **kwargs):
        self.assertIn("-t", command)
        self.assertIn("Kumusta", command)
        make_wav(Path(command[command.index("-o") + 1]))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def test_real_wav_checked_from_local_piper_output(self):
        env = {"AIVM_PIPER_EN_MODEL": str(self.model), "AIVM_PIPER_EXE": sys.executable}
        with patch.dict(os.environ, env, clear=True), patch(
            "voice_engine.subprocess.run", side_effect=self.fake_piper
        ):
            output = self.root / "english.wav"
            with self.assertRaisesRegex(ValueError, "rights"):
                voice_engine.generate_wav("Hello there", "en", "piper", output, False)
            meta = voice_engine.generate_wav("Hello there", "en", "piper", output, True)
        self.assertTrue(output.is_file())
        self.assertTrue(quality.media_info(output)["has_audio"])
        self.assertGreater(meta["duration_seconds"], 1)
        self.assertEqual(meta["engine"], "piper")

    def test_real_wav_checked_from_local_filipino_voxcpm2(self):
        env = {"AIVM_VOXCPM2_BASE": str(self.gguf_a), "AIVM_VOXCPM2_ACOUSTIC": str(self.gguf_b),
               "AIVM_VOXCPM2_EXE": sys.executable}
        with patch.dict(os.environ, env, clear=True), patch(
            "voice_engine.subprocess.run", side_effect=self.fake_voxcpm
        ):
            voice = voice_engine.generate_wav("Kumusta ka?", "tl", "voxcpm2",
                                              self.root / "tagalog.wav", True)
        self.assertTrue(Path(voice["wav"]).is_file())
        self.assertEqual(voice["language"], "tl")
        self.assertEqual(voice["engine"], "voxcpm2")

    def test_no_models_never_returns_fake_speech(self):
        with patch.dict(os.environ, {}, clear=True), patch("voice_engine.shutil.which", return_value=None):
            result = voice_engine.voice_options("tl")
            self.assertIsNone(result["recommended"])
            with self.assertRaisesRegex(ValueError, "No configured offline"):
                voice_engine.generate_wav("Kumusta!", "tl", "auto",
                                          self.root / "bad.wav", True)
        self.assertFalse((self.root / "bad.wav").exists())

    def test_project_voice_attachment_and_script_revision_protection(self):
        old = app.DATA
        app.DATA = self.root
        try:
            project = app.new_series({"storyline": "A young woman visits an old friend.",
                                      "language": "en"})
            app.save_project(project)
            scene_id = project["episodes"][0]["scenes"][0]["id"]
            episode_id = project["episodes"][0]["id"]
            def attached(text, language, engine, destination, confirmed):
                make_wav(destination)
                return {"engine": "piper", "duration_seconds": 1.1,
                        "wav": str(destination), "quality_reviewed": False}
            with patch("app.voice_engine.generate_wav", side_effect=attached):
                actual = app.generate_scene_voice(project["id"], episode_id, scene_id, "piper", True)
            saved = app.read_project(project["id"])
            self.assertEqual(saved["episodes"][0]["scenes"][0]["narration"], actual)
            self.assertTrue(Path(actual).is_file())
            self.assertFalse(saved["episodes"][0]["scenes"][0]["voice_provenance"]["quality_reviewed"])
        finally:
            app.DATA = old


if __name__ == "__main__":
    unittest.main()
