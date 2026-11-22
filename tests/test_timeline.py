"""Real end-to-end checks of non-destructive editorial timeline and AV transitions."""
from __future__ import annotations

import copy
import json
import math
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import caption_engine
import studio_quality as quality
import timeline_engine as timeline


def source_video(path: Path, color: str, tone: int, duration: float) -> None:
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"color=c={color}:s=240x426:r=24:d={duration}",
        "-f", "lavfi", "-i", f"sine=frequency={tone}:sample_rate=48000:duration={duration}",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)
    ], check=True, capture_output=True, timeout=70)


class TimelinePlanningTests(unittest.TestCase):
    def test_crossfade_offsets_and_source_windows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = [root / f"source-{i}.mp4" for i in range(3)]
            for file in sources:
                file.write_bytes(b"media checked by mock ffprobe")
            scenes = [
                {"id": "one", "clip": str(sources[0]), "script": "Scene one",
                 "trim_start_seconds": .4, "trim_end_seconds": 2.3,
                 "transition_to_next": "fade", "transition_duration_seconds": .3},
                {"id": "two", "clip": str(sources[1]), "script": "Scene two",
                 "transition_to_next": "wipeleft", "transition_duration_seconds": .25},
                {"id": "three", "clip": str(sources[2]), "script": "Scene three"},
            ]
            def info(path):
                duration = 2.6 if str(path) == str(sources[1]) else (
                    2.0 if str(path) == str(sources[2]) else 3.0)
                return {"duration": duration, "has_video": True, "has_audio": True,
                        "width": 240, "height": 426}
            with patch("timeline_engine.quality.media_info", side_effect=info):
                plan = timeline.plan_episode({"format": "9:16"}, {"scenes": scenes})
            self.assertAlmostEqual(plan["total_seconds"], 5.95, delta=.002)
            self.assertEqual(plan["crossfades"], 2)
            self.assertAlmostEqual(plan["entries"][1]["start"], 1.6, delta=.002)
            self.assertAlmostEqual(plan["entries"][2]["start"], 3.95, delta=.002)
            self.assertEqual(plan["entries"][0]["source_start"], .4)
            self.assertEqual(plan["entries"][0]["source_end"], 2.3)
            srt, meta = caption_engine.build_srt(
                scenes, [p["duration"] for p in plan["entries"]], plan["entries"])
            self.assertTrue(meta["timeline_aware"])
            self.assertIn("Scene three", srt)
            self.assertIn("00:00:05", srt)

    def test_broken_windows_long_voice_and_caption_collision_are_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            left, right = root / "a.mp4", root / "b.mp4"
            left.write_bytes(b"mock")
            right.write_bytes(b"mock")
            scene1 = {"id": "a", "clip": str(left), "transition_to_next": "fade",
                      "transition_duration_seconds": .4,
                      "caption_cues": [{"start": .0, "end": 1.9, "text": "late line"}]}
            scene2 = {"id": "b", "clip": str(right)}
            probe = lambda path: {"duration": 2.0, "has_video": True, "has_audio": True,
                                  "width": 240, "height": 426}
            with patch("timeline_engine.quality.media_info", side_effect=probe):
                with self.assertRaisesRegex(ValueError, "subtitle extends into a transition"):
                    timeline.plan_episode({"format": "9:16"}, {"scenes": [scene1, scene2]})
                scene1["caption_cues"][0]["end"] = 1.6
                scene1["trim_start_seconds"] = 1.8
                with self.assertRaisesRegex(ValueError, "Trimmed shot"):
                    timeline.plan_episode({"format": "9:16"}, {"scenes": [scene1, scene2]})
                scene1["trim_start_seconds"] = 0
                scene1["transition_duration_seconds"] = 1.3
                with self.assertRaisesRegex(ValueError, "45%"):
                    timeline.plan_episode({"format": "9:16"}, {"scenes": [scene1, scene2]})

    def test_retime_plan_preserves_caption_handoff_and_boundary_count(self):
        entries = [
            {"scene_id": "1", "transition_to_next": "fade",
             "transition_duration_seconds": .3},
            {"scene_id": "2", "transition_to_next": "cut",
             "transition_duration_seconds": 0},
        ]
        calculated = timeline.with_durations(entries, [2.0, 2.2])
        self.assertAlmostEqual(calculated["total_seconds"], 3.9)
        self.assertAlmostEqual(calculated["entries"][0]["caption_max"], 1.85)
        self.assertAlmostEqual(calculated["entries"][1]["caption_min"], .15)
        srt, meta = caption_engine.build_srt(
            [{"script": "Alpha one"}, {"script": "Beta two"}],
            [2.0, 2.2], calculated["entries"])
        self.assertTrue(meta["timeline_aware"])
        # Last cue in outgoing shot ends at midpoint; first incoming cue starts there.
        self.assertIn("00:00:01,850", srt)


class FFmpegEditorialTests(unittest.TestCase):
    def setUp(self):
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            self.skipTest("FFmpeg and FFprobe are needed for a real video test")
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data = app.DATA
        app.DATA = Path(self.tmp.name)
        self.root = app.DATA
        self.red = self.root / "red.mp4"
        self.blue = self.root / "blue.mp4"
        source_video(self.red, "red", 440, 2.5)
        source_video(self.blue, "blue", 880, 2.5)

    def tearDown(self):
        if hasattr(self, "old_data"):
            app.DATA = self.old_data
        if hasattr(self, "tmp"):
            self.tmp.cleanup()

    def project_two_scenes(self, effect="fade"):
        project = app.new_series({"storyline": "The girl notices a letter near the door. "
                                      "She opens it and finally learns the truth.",
                                      "format": "9:16"})
        episode = project["episodes"][0]
        shot1 = episode["scenes"][0]
        shot2 = copy.deepcopy(shot1)
        shot2.update(id="editshot-two", number=2,
                     script="She opens it and learns the truth.",
                     clip=str(self.blue), trim_start_seconds=0.1,
                     trim_end_seconds=2.1, transition_to_next="cut", caption_cues=[])
        shot1.update(number=1, clip=str(self.red),
                     trim_start_seconds=.35, trim_end_seconds=2.15,
                     script="The girl notices a letter by the door.",
                     transition_to_next=effect,
                     transition_duration_seconds=.4)
        episode["scenes"] = [shot1, shot2]
        return project, episode, shot1, shot2

    def test_real_video_audio_crossfade_trim_and_matching_mp4_srt(self):
        project, ep, shot1, shot2 = self.project_two_scenes()
        shot1["caption_cues"] = [{"start": .15, "end": 1.3, "text": "Found the letter"}]
        shot2["caption_cues"] = [{"start": .4, "end": 1.55, "text": "She reads it"}]
        ep["caption_mode"] = "sidecar"
        app.save_project(project)
        result = Path(app.render_episode(project["id"], ep["id"]))
        self.assertTrue(result.is_file())
        info = quality.media_info(result)
        self.assertTrue(info["has_audio"])
        self.assertEqual((info["width"], info["height"]), (720, 1280))
        expected = 1.8 + 2.0 - .4
        self.assertAlmostEqual(info["duration"], expected, delta=.5)
        updated = app.read_project(project["id"])["episodes"][0]
        report = json.loads(Path(updated["quality_report_path"]).read_text("utf-8"))
        self.assertEqual(report["status"], "technical_checks_passed")
        self.assertEqual(report["timeline"]["crossfades"], 1)
        self.assertEqual(report["caption_timing_mode"], "manual")
        text = Path(updated["captions_path"]).read_text(encoding="utf-8-sig")
        self.assertIn("Found the letter", text)
        self.assertIn("She reads it", text)
        self.assertIn("00:00:01,400", text)  # Incoming shot begins during overlap.
        self.assertEqual(shot1["clip"], str(self.red))
        self.assertEqual(shot2["clip"], str(self.blue))

    def test_multi_cut_group_and_transition_preserve_sound(self):
        project, ep, shot1, shot2 = self.project_two_scenes(effect="cut")
        shot3 = copy.deepcopy(shot2)
        shot3["id"] = "third-scene"; shot3["number"] = 3
        shot3["clip"] = str(self.red)
        shot3["trim_start_seconds"] = 0
        shot3["trim_end_seconds"] = 1.6
        shot2["transition_to_next"] = "wipeleft"
        shot2["transition_duration_seconds"] = .3
        ep["scenes"].append(shot3)
        app.save_project(project)
        result = Path(app.render_episode(project["id"], ep["id"]))
        info = quality.media_info(result)
        self.assertTrue(info["has_audio"])
        self.assertAlmostEqual(info["duration"], 1.8 + 2.0 + 1.6 - .3, delta=.65)
        qc = json.loads(Path(app.read_project(project["id"])["episodes"][0]["quality_report_path"]).read_text())
        self.assertEqual(qc["timeline"]["crossfades"], 1)

    def test_too_long_narration_with_crossfade_is_blocked(self):
        project, ep, shot1, shot2 = self.project_two_scenes()
        voice = self.root / "narration.wav"
        subprocess.run([
            "ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi",
            "-i", "sine=frequency=550:sample_rate=48000:duration=1.6",
            "-c:a", "pcm_s16le", str(voice)
        ], check=True, capture_output=True, timeout=45)
        shot1["narration"] = str(voice)
        # Shot1 trimmed to 1.8s. Outgoing fade .4 => safe speech room 1.4s.
        report = quality.episode_preflight(project, ep)
        self.assertFalse(report["can_render"])
        self.assertIn("invalid_edit_timeline", [f["code"] for f in report["findings"]])
        app.save_project(project)
        with self.assertRaisesRegex(ValueError, "timeline|narration"):
            app.render_episode(project["id"], ep["id"])

if __name__ == "__main__":
    unittest.main()
