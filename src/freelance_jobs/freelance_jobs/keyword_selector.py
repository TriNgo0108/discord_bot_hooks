"""Selects keywords for job search."""

import random

from freelance_jobs.constants import JOB_KEYWORDS


class KeywordSelector:
    """Selects a keyword for the job search."""

    def get_random_keyword(self) -> str:
        """Return a random keyword from the curated list."""
        return random.choice(JOB_KEYWORDS)
