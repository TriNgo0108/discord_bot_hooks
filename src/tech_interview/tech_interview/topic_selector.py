"""Selects topics for tech interview question generation."""

import random
from typing import TypedDict

from tech_interview.constants import CODING_TOPICS, GENERAL_TOPICS


class Topic(TypedDict):
    content: str
    type: str


class TopicSelector:
    """Selects a topic for the interview question."""

    def get_random_topic(self) -> Topic:
        """Return a random topic from the curated list."""
        # 50% chance for Coding Question, 50% for General/System Design
        if random.random() < 0.5:
            return {"content": random.choice(CODING_TOPICS), "type": "coding"}
        return {"content": random.choice(GENERAL_TOPICS), "type": "general"}
