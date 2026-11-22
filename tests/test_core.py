"""Unit and integration checks for the zero-paid-API core."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

import app


class SeriesTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.original = app.DATA
        app.DATA = Path(self.folder.name)

    def tearDown(self):
        app.DATA = self.original
        self.folder.cleanup()

    def test_english_and_tagalog_source_story_preserved(self):
        for language, text in (
            ("en", "Maria entered the room. She found a letter. It changed everything. " * 14),
            ("tl", "Umuwi si Ana sa probinsya. Nakita niya ang lumang litrato. Doon nagsimula ang kuwento. " * 14),
        ):
            with self.subTest(language=language):
                series = app.new_series({"storyline": text, "language": language,
                                         "episode_word_target": 30})
                self.assertEqual(series["storyline"], text.strip())
                self.assertEqual(series["language"], language)
                self.assertGreater(len(series["episodes"]), 1)
                shots = [shot["script"] for episode in series["episodes"] for shot in episode["scenes"]]
                self.assertEqual(" ".join(shots), " ".join(text.split()))

    def test_no_horror_default_or_arbitrary_episode_limit(self):
        story = "A scientist presents a new invention. " * 120
        series = app.new_series({"storyline": story, "genre": "Science fiction",
                                  "episode_word_target": 30})
        self.assertEqual(series["genre"], "Science fiction")
        self.assertGreater(len(series["episodes"]), 10)

    def test_reject_tiny_source(self):
        with self.assertRaises(ValueError):
            app.new_series({"storyline": "short"})

    def test_json_storage(self):
        series = app.new_series({"storyline": "A story begins in the city, and changes over time."})
        series["bible"]["canon"] = "Character keeps the same blue jacket."
        app.save_project(series)
        loaded = app.read_project(series["id"])
        self.assertEqual(loaded["bible"]["canon"], "Character keeps the same blue jacket.")
        self.assertEqual(app.list_projects()[0]["id"], series["id"])

    def test_workflow_replacement_and_validation(self):
        workflow = {"1": {"class_type": "CLIPTextEncode", "inputs": {"text": "{{PROMPT}}"}},
                    "2": {"class_type": "Sampler", "inputs": {"seed": "{{SEED}}"}}}
        app.install_workflow("my_wan_5b", workflow)
        saved = json.loads(app.workflow_path("my_wan_5b").read_text("utf-8"))
        new = app.interpolate(saved, {"{{PROMPT}}": "Character running", "{{SEED}}": 123,
                                       "{{NEGATIVE_PROMPT}}": "glitch"})
        self.assertEqual(new["1"]["inputs"]["text"], "Character running")
        self.assertEqual(new["2"]["inputs"]["seed"], 123)
        with self.assertRaises(ValueError):
            app.install_workflow("../unsafe", workflow)
        with self.assertRaises(ValueError):
            app.install_workflow("invalid", {"node": {"class_type": "Sampler", "inputs": {}}})

    def test_no_fake_ai_video_on_missing_clips(self):
        series = app.new_series({"storyline": "A young artist builds a business from nothing."})
        app.save_project(series)
        with self.assertRaisesRegex(ValueError, "Missing REAL moving video"):
            app.render_episode(series["id"], series["episodes"][0]["id"])

    def test_local_only_model_hosts(self):
        self.assertEqual(app.local_url("http://127.0.0.1:8188"), "http://127.0.0.1:8188")
        with self.assertRaises(ValueError):
            app.local_url("https://paid-inference.example/api")

    def test_gpu_preflight_gtx750_is_not_video_ready(self):
        from unittest.mock import Mock
        result = Mock(returncode=0, stdout="GeForce GTX 750, 1024, 5.0\n")
        with patch("app.shutil.which", return_value="nvidia-smi"), patch(
            "app.subprocess.run", return_value=result
        ):
            gpu = app.gpu_preflight()
        self.assertTrue(gpu["detected"])
        self.assertEqual(gpu["video_generation"], "insufficient_for_wan22_5b")
        self.assertEqual(gpu["compute_capability"], "5.0")
        self.assertAlmostEqual(gpu["vram_gb"], 1.0)

    def test_gpu_preflight_no_nvidia_smi_is_unknown_not_success(self):
        with patch("app.shutil.which", return_value=None):
            gpu = app.gpu_preflight()
        self.assertFalse(gpu["detected"])
        self.assertEqual(gpu["video_generation"], "unverified")

    def test_gpu_preflight_stronger_card_still_unverified(self):
        from unittest.mock import Mock
        result = Mock(returncode=0, stdout="RTX GPU, 12288, 8.6\n")
        with patch("app.shutil.which", return_value="nvidia-smi"), patch(
            "app.subprocess.run", return_value=result
        ):
            gpu = app.gpu_preflight()
        self.assertEqual(gpu["video_generation"], "not_validated")

    def test_ffmpeg_real_video_render(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("FFmpeg missing on test runner")
        series = app.new_series({"storyline": "A person climbs a hill. At the summit they meet a friend.",
                                 "episode_word_target": 100})
        episode = series["episodes"][0]
        # Give two scenes a real MP4 file, one with audio and one without.
        for scene in episode["scenes"]:
            target = app.DATA / (scene["id"] + ".mp4")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y",
                            "-f", "lavfi", "-i", "color=c=blue:s=160x240:r=12:d=0.5",
                            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                            str(target)], check=True, capture_output=True)
            scene["clip"] = str(target)
        app.save_project(series)
        result = Path(app.render_episode(series["id"], episode["id"]))
        self.assertTrue(result.is_file())
        streams = json.loads(subprocess.check_output(["ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type", "-of", "json", str(result)]))["streams"]
        self.assertIn("video", [s["codec_type"] for s in streams])
        self.assertIn("audio", [s["codec_type"] for s in streams])


if __name__ == "__main__":
    unittest.main()
