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

    def test_reference_selection_explicit_then_character(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            character = root / "character.png"
            direct = root / "shot.webp"
            character.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            direct.write_bytes(b"RIFF\x80\x00\x00\x00WEBP" + b"\x00" * 100)
            series = {"bible": {"characters": [
                {"name": "Maria", "reference_image": str(character)}
            ]}}
            scene = {"script": "Maria raises a hand", "prompt": "Camera tracks Maria."}
            self.assertEqual(quality.reference_image_for_scene(series, scene), character)
            scene["reference_image"] = str(direct)
            self.assertEqual(quality.reference_image_for_scene(series, scene), direct)
            quality.validate_image(direct)
            quality.validate_image(character)

    def test_invalid_reference_image_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            invalid = Path(temporary) / "bad.png"
            invalid.write_text("not an actual PNG header")
            with self.assertRaisesRegex(ValueError, "file header"):
                quality.validate_image(invalid)

    def test_comfy_reference_upload_form_payload(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as temporary:
            reference = Path(temporary) / "maria.png"
            reference.write_bytes(b"\x89PNG\r\n\x1a\n" + b"image-fixture")
            class Response:
                def __enter__(self): return self
                def __exit__(self, *unused): return None
                def read(self): return b'{"name":"uploaded.png","type":"input","subfolder":""}'
            with patch("app.urllib.request.urlopen", return_value=Response()) as send:
                result = app.upload_reference_to_comfy(reference)
                self.assertEqual(result, "uploaded.png")
                sent_request = send.call_args.args[0]
                self.assertIn(b'Content-Disposition: form-data; name="image"', sent_request.data)
                self.assertIn(b"image-fixture", sent_request.data)
                self.assertIn("/upload/image", sent_request.full_url)

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

    def test_real_footage_licensed_music_and_atomic_fallback(self):
        video, voice = self.fixture(video_duration=2.2, voice_duration=1.4)
        soundtrack = app.DATA / "background.wav"
        # Reuse a valid local WAV; rights must be confirmed before any export.
        soundtrack.write_bytes(voice.read_bytes())
        series = app.new_series({"storyline": "A young artist writes a letter before the journey."})
        scene = series["episodes"][0]["scenes"][0]
        scene["clip"], scene["narration"] = str(video), str(voice)
        episode = series["episodes"][0]
        episode["soundtrack"] = str(soundtrack)
        episode["soundtrack_rights_confirmed"] = True
        app.save_project(series)
        result = Path(app.render_episode(series["id"], episode["id"]))
        self.assertTrue(result.is_file())
        self.assertTrue(quality.media_info(result)["has_audio"])
        qa = json.loads(Path(app.read_project(series["id"])["episodes"][0]["quality_report_path"]).read_text())
        self.assertEqual(qa["status"], "technical_checks_passed")
        self.assertTrue(qa["music_included"])
        original_bytes = result.read_bytes()
        latest = app.read_project(series["id"])
        latest["episodes"][0]["soundtrack_rights_confirmed"] = False
        app.save_project(latest)
        check = quality.episode_preflight(latest, latest["episodes"][0])
        self.assertIn("music_rights", [item["code"] for item in check["findings"]])
        with self.assertRaisesRegex(ValueError, "rights|permission"):
            app.render_episode(series["id"], episode["id"])
        self.assertEqual(result.read_bytes(), original_bytes)

    def test_real_footage_end_to_end_with_manual_burned_subtitles(self):
        import caption_engine
        if not caption_engine.subtitle_filter_available():
            self.skipTest("FFmpeg libass subtitle renderer unavailable")
        video, voice = self.fixture(video_duration=2.35, voice_duration=1.1)
        project = app.new_series({"storyline": "A character returns to the city and finds a letter."})
        episode = project["episodes"][0]
        scene = episode["scenes"][0]
        episode["caption_mode"] = "burned"
        scene["clip"], scene["narration"] = str(video), str(voice)
        scene["caption_cues"] = [{"start": 0.0, "end": 1.8,
                                   "text": "A character returns to the city"}]
        app.save_project(project)
        exported = Path(app.render_episode(project["id"], episode["id"]))
        self.assertTrue(exported.is_file())
        saved = app.read_project(project["id"])["episodes"][0]
        meta = json.loads(Path(saved["quality_report_path"]).read_text())
        self.assertEqual(meta["caption_export"], "burned")
        self.assertEqual(meta["caption_timing_mode"], "manual")
        self.assertEqual(meta["status"], "technical_checks_passed")
        self.assertTrue(quality.media_info(exported)["has_audio"])
        srt = Path(saved["captions_path"]).read_text(encoding="utf-8-sig")
        self.assertIn("A character returns to the city", srt)

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
