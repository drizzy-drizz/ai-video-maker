"""Deterministic narrative-aware episode boundary proposal.

No AI claims: original script is unchanged, words remain in source order.
Prefer paragraph/scene and sentence boundaries near the requested episode size.
A later Ollama director can override proposals only after user approval.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Signals are modest hints, not a semantic proof of a cliffhanger.
_TURNING_EN = re.compile(
    r"\b(but|however|suddenly|until|then|instead|finally|realized|revealed|discovered|"
    r"the truth|unexpected|before|what if)\b", re.IGNORECASE)
_TURNING_TL = re.compile(
    r"\b(pero|ngunit|subalit|bigla|hanggang|napagtanto|natuklasan|nalaman|"
    r"sa huli|hindi niya|bakit|paano)\b", re.IGNORECASE)


@dataclass
class Unit:
    text: str
    paragraph_end: bool = False

    @property
    def count(self) -> int:
        return len(self.text.split())


def story_units(story: str, limit: int = 65) -> list[Unit]:
    """Split on sentence/scene boundaries; huge sentences become word chunks."""
    paragraphs = re.split(r"\n\s*\n+", story.strip())
    result: list[Unit] = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        sentences = re.split(r"(?<=[.!?…])\s+|\n+", paragraph.strip())
        for sentence in sentences:
            if not sentence.strip():
                continue
            words = sentence.split()
            # Keep ordinary sentences intact. Abnormally long run-ons may split
            # on whitespace; this preserves order/coverage and avoids huge shots.
            if len(words) <= limit:
                result.append(Unit(" ".join(words)))
            else:
                for i in range(0, len(words), limit):
                    result.append(Unit(" ".join(words[i:i + limit])))
        if result:
            result[-1].paragraph_end = True
    return result


def boundary_score(unit: Unit, count: int, target: int) -> float:
    closeness = -abs(count - target) / max(1, target)
    bonus = 1.1 if unit.paragraph_end else 0.0
    if unit.text.endswith("?") or unit.text.endswith("!"):
        bonus += 0.2
    if _TURNING_EN.search(unit.text) or _TURNING_TL.search(unit.text):
        bonus += 0.22
    return closeness + bonus


def episode_unit_groups(units: list[Unit], target: int) -> list[list[Unit]]:
    if not units:
        return []
    output = []
    start = 0
    min_words = max(15, round(target * 0.62))
    max_words = max(min_words + 10, round(target * 1.38))
    while start < len(units):
        total = 0
        candidates: list[tuple[float, int]] = []
        for end in range(start, len(units)):
            total += units[end].count
            if total >= min_words and total <= max_words:
                candidates.append((boundary_score(units[end], total, target), end + 1))
            if total > max_words:
                break
        if not candidates:
            # One single unit can exceed max_words; never lose it.
            end_at = min(start + 1, len(units))
        else:
            _, end_at = max(candidates, key=lambda item: (item[0], item[1]))
            if end_at == start:
                end_at = start + 1
        output.append(units[start:end_at])
        start = end_at

    if len(output) > 1:
        tiny_last = sum(unit.count for unit in output[-1]) < max(12, round(target * 0.3))
        previous = sum(unit.count for unit in output[-2])
        if tiny_last and previous + sum(unit.count for unit in output[-1]) <= round(target * 1.55):
            output[-2].extend(output.pop())
    return output


def shot_groups(units: list[Unit], target_shot_words: int = 20) -> list[str]:
    """Keep screenplay sentences together where possible; split overlong shots."""
    parts: list[str] = []
    working: list[str] = []
    words_used = 0
    for unit in units:
        text = unit.text
        count = unit.count
        if working and words_used + count > target_shot_words:
            parts.append(" ".join(working))
            working, words_used = [], 0
        if count > target_shot_words * 1.5:
            # Split run-on sentences into short visual beats, not a single 1-minute shot.
            words = text.split()
            for start in range(0, len(words), target_shot_words):
                if working:
                    parts.append(" ".join(working))
                    working, words_used = [], 0
                parts.append(" ".join(words[start:start + target_shot_words]))
        else:
            working.append(text)
            words_used += count
    if working:
        parts.append(" ".join(working))
    return parts


def plan_story(story: str, target_episode_words: int) -> list[dict]:
    """Episode structure with exact normalized-word coverage, no invented plot."""
    if target_episode_words < 30:
        raise ValueError("Episode word target must be at least 30")
    units = story_units(story, limit=max(35, round(target_episode_words * 0.7)))
    groups = episode_unit_groups(units, target_episode_words)
    planned = []
    for i, group in enumerate(groups, 1):
        scripts = shot_groups(group, target_shot_words=max(12, min(24, target_episode_words // 8)))
        if not scripts:
            continue
        planned.append({
            "number": i,
            "scenes": scripts,
            "hook_excerpt": scripts[0][:260],
            "ending_excerpt": scripts[-1][-260:],
            "words": sum(len(text.split()) for text in scripts),
            "boundary_reason": "paragraph/turning-point weighted deterministic heuristic",
        })
    source_words = story.split()
    produced = [word for episode in planned for scene in episode["scenes"] for word in scene.split()]
    if source_words != produced:
        raise ValueError("Story planner coverage check failed; source text was not preserved in shot plan")
    return planned
