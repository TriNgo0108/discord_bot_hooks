"""DuckDuckGo Search API Client."""

import logging
from typing import Any

from ddgs import DDGS
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class DDGClient:
    """Client for DuckDuckGo Search (via duckduckgo_search library)."""

    def __init__(self):
        """Initialize DDGS."""
        pass

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def search(
        self,
        query: str,
        max_results: int = 5,
        days: int | None = None,
        include_raw_content: bool = False,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Perform a search using DuckDuckGo.

        Args:
            query: Search query.
            max_results: Max results.
            days: Filter by time.
                  < 2 -> 'd' (past day)
                  < 8 -> 'w' (past week)
                  > 8 -> 'm' (past month)
                  None -> no time filter
            include_raw_content: Ignored (DDGS returns snippets)

        Returns:
            Dict with "results" list.
        """
        # Map days to DDG time filter
        time_filter = None
        if days is not None:
            if days <= 1:
                time_filter = "d"
            elif days <= 7:
                time_filter = "w"
            else:
                time_filter = "m"  # past month

        results = []
        try:
            # DDGS is synchronous by default unless using AsyncDDGS (which is available in newer versions)
            # For simplicity and compatibility, we wrap the sync call or use AsyncDDGS if available.
            # Assuming standard DDGS.text() usage.

            # Note: duckduckgo_search >= 4.0 uses DDGS().text()
            # We'll use synchronous DDGS for now as it's robust.
            # If async is needed, we can wrap in asyncio.to_thread
            import asyncio

            def _do_search():
                with DDGS() as ddgs:
                    return list(
                        ddgs.text(
                            query=query,
                            region="wt-wt",
                            safesearch="off",
                            timelimit=time_filter,
                            max_results=max_results,
                        )
                    )

            ddg_results = await asyncio.to_thread(_do_search)

            for r in ddg_results:
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "content": r.get("body", ""),
                        "published_date": "",  # DDG text search often doesn't return date
                    }
                )

        except Exception as e:
            logger.error(f"DDG search failed: {e}")
            raise

        return {"results": results}

    async def get_search_context(
        self,
        query: str,
        max_results: int = 5,
        days: int | None = None,
        **kwargs,
    ) -> str:
        """Get context string for LLM."""
        try:
            data = await self.search(query=query, max_results=max_results, days=days)

            results = data.get("results", [])
            if not results:
                return ""

            context_parts = []
            for i, result in enumerate(results, 1):
                part = f"Source {i}: {result['title']}\nURL: {result['url']}\nContent: {result['content']}"
                context_parts.append(part)

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"DDG context failed: {e}")
            return ""
