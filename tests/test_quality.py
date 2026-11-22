"""Quality and real-audio integration coverage for the local-first episode engine."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import studio_quality as quality


class CanonTests(unittest.TestCase):
    def test_canon_only_includes_relevant_characters(self):
        series = {
            "title": "Buhay ni Maria", "genre": "Drama",
            "bible": {
                "world": "Manila, 2026", "style": "Warm documentary film",
                "canon": "Maria always keeps her blue jacket",
                "characters": [
                    {"name": "Maria", "appearance": "short hair", "wardrobe": "blue jacket"},
                    {"name": "Pedro", "appearance": "red cap", "wardrobe": "black coat"},
                ],
                "locations": [{"name": "Divisoria", "description": "Busy market stalls"}]
            }
        }
        episode = {"title": "Ang simula"}
        scene = {"script": "Si Maria ay naglalakad sa Divisoria.", "prompt": "Slow camera push", "character_ids": []}
        compiled = quality.compose_canonical_prompt(series, episode, scene)
        self.assertIn("Maria", compiled["characters"])
        self.assertIn("blue jacket", compiled["prompt"])
        self.assertIn("Divisoria", compiled["prompt"])
        self.assertNotIn("Pedro", compiled["characters"])
        self.assertNotIn("red cap", compiled["prompt"])

    def test_english_immutable_source(self):
        series = {"title": "Space Station", "bible": {"style": "Realistic", "canon": "No aliens"}}
        ep = {"title": "Part 1"}
        scene = {"script": "The captain finds water.", "prompt": "handheld camera"}
        result = quality.compose_canonical_prompt(series, ep, scene)
        self.assertIn("The captain finds water.", result["prompt"])
        self.assertEqual(scene["script"], "The captain finds water.")

    def test_caption_estimates_bilingual_and_contiguous(self):
        scenes = [{"script": "Kumusta sa lahat ng tao sa bayan."},
                  {"script": "Today we are going to the station together."}]
        srt = quality.make_subtitles(scenes, [3.0, 4.5], words_per_caption=4)
        self.assertIn("Kumusta", srt)
        self.assertIn("station", srt)
        self.assertIn("00:00:03,000", srt)
        self.assertIn("00:00:07,500", srt)
        self.assertEqual(srt.count(" --> "), 4)

    def test_media_missing_is_render_blocker(self):
        with patch("studio_quality.media_info") as mocked:
            report = quality.episode_preflight(
                {"format": "9:16", "bible": {"style": "Cinematic", "characters": [], "canon": "Keep continuity"}},
                {"scenes": [{"number": 1, "clip": ""}]}
            )
        self.assertFalse(report["can_render"])
        self.assertIn("missing_video", [f["code"] for f in report["findings"]])
        mocked.assert_not_called()

    def test_technical_qc_detects_duration_mismatch(self):
        with patch("studio_quality.media_info", return_value={
            "duration": 5, "has_video": True, "has_audio": True,
            "width": 720, "height": 1280, "video_codec": "h264", "audio_codec": "aac"
        }):
            qa = quality.quality_report_export(Path("example.mp4"), expected_duration=15)
        self.assertEqual(qa["status"], "technical_checks_failed")


class ActualFFmpegTests(unittest.TestCase):
    def setUp(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("FFmpeg/ffprobe are required for media integration test")
        self.tmp = tempfile.TemporaryDirectory()
        self.original = app.DATA
        app.DATA = Path(self.tmp.name)

    def tearDown(self):
        if hasattr(self, "original"):
            app.DATA = self.original
        if hasattr(self, "tmp"):
            self.tmp.cleanup()

    def ffmpeg(self, *args):
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
                       check=True, capture_output=True, timeout=90)

    def fixture(self, video_duration=2.0, voice_duration=1.2):
        video = app.DATA / "test_video.mp4"
        voice = app.DATA / "test_voice.wav"
        # Video contains spoken-background-like sine audio; separate narration overlays it.
        self.ffmpeg("-f", "lavfi", "-i", f"color=c=blue:s=160x240:r=12:d={video_duration}",
                    "-f", "lavfi", "-i", f"sine=frequency=220:sample_rate=48000:duration={video_duration}",
                    "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", str(video))
        self.ffmpeg("-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={voice_duration}",
                    "-ac", "1", str(voice))
        return video, voice

    def test_voice_longer_than_clip_is_blocked_not_cut_off(self):
        video, voice = self.fixture(video_duration=1.4, voice_duration=2.5)
        series = app.new_series({"storyline": "Maria traveled home to meet friends."})
        scene = series["episodes"][0]["scenes"][0]
        scene["clip"], scene["narration"] = str(video), str(voice)
        app.save_project(series)
        report = quality.episode_preflight(series, series["episodes"][0])
        self.assertFalse(report["can_render"])
        self.assertIn("voice_longer_than_clip", [f["code"] for f in report["findings"]])
        with self.assertRaisesRegex(ValueError, "Voice is"):
            app.render_episode(series["id"], series["episodes"][0]["id"])

    def test_voice_mixed_and_srt_qc_written(self):
        video, voice = self.fixture(video_duration=2.2, voice_duration=1.3)
        series = app.new_series({"storyline": "Maria found a letter and read it."})
        scene = series["episodes"][0]["scenes"][0]
        scene["clip"], scene["narration"] = str(video), str(voice)
        app.save_project(series)
        episode_id = series["episodes"][0]["id"]
        output = Path(app.render_episode(series["id"], episode_id))
        self.assertTrue(output.is_file())
        info = quality.media_info(output)
        self.assertTrue(info["has_video"])
        self.assertTrue(info["has_audio"])
        self.assertEqual((info["width"], info["height"]), (720, 1280))
        self.assertAlmostEqual(info["duration"], 2.2, delta=0.5)
        updated = app.read_project(series["id"])["episodes"][0]
        self.assertEqual(updated["status"], "rendered_needs_human_review")
        srt = Path(updated["captions_path"]).read_text(encoding="utf-8-sig")
        self.assertIn("Maria found a letter", srt)
        self.assertIn("-->", srt)
        qc = json.loads(Path(updated["quality_report_path"]).read_text())
        self.assertEqual(qc["status"], "technical_checks_passed")
        self.assertIn("approximate", qc["subtitles"])


if __name__ == "__main__":
    unittest.main()
