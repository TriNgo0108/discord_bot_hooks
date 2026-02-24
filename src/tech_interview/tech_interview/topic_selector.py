"""Selects topics for tech interview question generation."""

import random
from typing import TypedDict

from tech_interview.constants import GENERAL_TOPICS


class Topic(TypedDict):
    content: str
    type: str


class TopicSelector:
    """Selects a topic for the interview question."""

    def get_random_topic(self) -> Topic:
        """Return a random topic from the curated list."""
        return {"content": random.choice(GENERAL_TOPICS), "type": "general"}
