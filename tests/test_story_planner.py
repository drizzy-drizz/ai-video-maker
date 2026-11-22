"""Story-world source preservation and natural episode boundary regression tests."""
import unittest

import app
import story_planner


class StoryPlannerTests(unittest.TestCase):
    def test_paragraph_boundary_beats_dumb_word_slicing(self):
        first = ("Maria woke up to find the empty market. " * 5).strip()
        second = ("At noon, she discovered the letter. " * 5).strip()
        script = first + "\n\n" + second
        episodes = story_planner.plan_story(script, target_episode_words=45)
        self.assertGreaterEqual(len(episodes), 2)
        self.assertIn("empty market.", episodes[0]["scenes"][-1])
        self.assertIn("At noon", episodes[1]["scenes"][0])
        self.assertEqual(
            [w for episode in episodes for scene in episode["scenes"] for w in scene.split()],
            script.split(),
        )

    def test_tagalog_unicode_coverage_with_dialogue(self):
        script = ("“Hindi puwede,” sabi ni Ana. Pero lumaban pa rin siya. " * 9 +
                  "\n\nSa huli, natutunan niyang magtiwala.").strip()
        episodes = story_planner.plan_story(script, 35)
        produced = " ".join(scene for ep in episodes for scene in ep["scenes"])
        self.assertEqual(produced.split(), script.split())
        self.assertTrue(all(ep["hook_excerpt"] and ep["ending_excerpt"] for ep in episodes))

    def test_short_final_remainder_not_many_tiny_episodes(self):
        script = ("A traveler crosses a bridge. " * 18).strip()
        episodes = story_planner.plan_story(script, 85)
        self.assertLessEqual(len(episodes), 3)
        self.assertEqual(sum(e["words"] for e in episodes), len(script.split()))

    def test_long_runon_does_not_break_coverage(self):
        script = " ".join(f"word{i}" for i in range(250))
        episodes = story_planner.plan_story(script, 70)
        words = " ".join(shot for ep in episodes for shot in ep["scenes"])
        self.assertEqual(words.split(), script.split())
        self.assertGreater(len(episodes), 2)

    def test_new_series_uses_narrative_planner_only_on_creation(self):
        script = "Today Mara opened the new shop. Tomorrow Mara will call her sister. " * 7
        project = app.new_series({"storyline": script, "episode_word_target": 35})
        self.assertIn("narrative-boundary", project["planner"])
        episode = project["episodes"][0]
        self.assertTrue(episode["hook_excerpt"])
        self.assertEqual(episode["scenes"][0]["beat_position"], "opening")
        self.assertEqual(sum(e["word_count"] for e in project["episodes"]), len(script.split()))


if __name__ == "__main__":
    unittest.main()
