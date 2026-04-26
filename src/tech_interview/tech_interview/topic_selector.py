"""Selects topics for English grammar lesson generation."""

import random

from tech_interview.constants import GRAMMAR_TOPICS


class TopicSelector:
    """Selects a grammar topic for the lesson."""

    def get_random_topic(self) -> str:
        """Return a random topic from the curated list."""
        return random.choice(GRAMMAR_TOPICS)
