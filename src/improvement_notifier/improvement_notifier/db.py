import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from collections.abc import Generator
from contextlib import contextmanager

from .config import settings
from .models import Improvement

logger = logging.getLogger(__name__)


@contextmanager
def get_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """Context manager for database connection."""
    conn = None
    try:
        conn = psycopg2.connect(settings.DB_URL)
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def fetch_incomplete_improvements() -> list[Improvement]:
    """Fetch all incomplete improvements from the database."""
    query = """
        SELECT id, user_aggregate_id, content, created_at, completed
        FROM public.improvement_read_model
        WHERE completed = false
        ORDER BY created_at ASC;
    """

    improvements = []

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                improvements.append(Improvement(**row))

    return improvements
