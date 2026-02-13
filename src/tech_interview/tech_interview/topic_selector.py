"""Selects topics for tech interview question generation."""

import random

from tech_interview.constants import INTERVIEW_TOPICS


class TopicSelector:
    """Selects a topic for the interview question."""

    def get_random_topic(self) -> str:
        """Return a random topic from the curated list."""
        return random.choice(INTERVIEW_TOPICS)
