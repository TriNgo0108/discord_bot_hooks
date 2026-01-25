"""Research analyzer using Perplexity Search API and Z.AI SDK (GLM-4.7).

Architecture:
1. Perplexity Search API - Returns raw web search results (titles, URLs, snippets)
2. Z.AI GLM-4.7 - Analyzes search results and provides trading recommendations
"""

import asyncio
import json
import logging
from typing import Any

import httpx

from .config import AIConfig
from .models import (
    AnalysisResult,
    PolymarketMarket,
    Recommendation,
    ResearchResult,
    Sentiment,
)

logger = logging.getLogger(__name__)


# =============================================================================
# OPTIMIZED PROMPTS (Using prompt-engineering-patterns skill)
# =============================================================================

# GLM-4.7 prompt for analyzing search results and providing recommendations
GLM_ANALYSIS_PROMPT = """You are an expert prediction market analyst specializing in probability assessment and edge identification.

## Your Task
Analyze the following prediction market using the provided web search results.

## Market Information
- **Question**: {question}
- **Description**: {description}
- **Current Market Odds**: {odds}%
- **End Date**: {end_date}

## Web Search Results
{search_results}

---

## Analysis Framework

Think step-by-step:

### Step 1: Research Summary
Summarize the key findings from the search results that are relevant to this prediction market.

### Step 2: Probability Assessment
Based on the research, what is your estimated true probability for this outcome?

### Step 3: Edge Calculation
- Edge = |Estimated Probability - Market Odds|
- Minimum edge for action: 10%

### Step 4: Recommendation
- LONG: Your estimate > Market Odds + 10%
- SHORT: Your estimate < Market Odds - 10%
- AVOID: Edge < 10% or high uncertainty

### Step 5: Risk Assessment
What could invalidate this analysis?

---

## Examples of Good Analysis

### Example 1
**Question**: "Will the Federal Reserve cut rates in March 2024?"
**Market Odds**: 65%
**Research**: Fed officials signaling caution, inflation still above target
**Analysis**: Market overestimates cut probability. True probability ~40%.
**Recommendation**: SHORT (edge: 25%)

### Example 2
**Question**: "Will Company X announce layoffs by Q1?"
**Market Odds**: 30%
**Research**: Internal sources report restructuring plans, hiring freeze confirmed
**Analysis**: Market underestimates. True probability ~55%.
**Recommendation**: LONG (edge: 25%)

---

## Self-Verification Checklist
Before responding, verify:
- [ ] Analysis uses only factual information from search results
- [ ] Probability estimate is justified with specific evidence
- [ ] Contrary viewpoints have been considered
- [ ] Risk factors are realistic, not generic

---

## Output Format (JSON only)
{{
    "key_findings": ["finding1", "finding2", "finding3"],
    "recent_news": ["news1", "news2"],
    "sentiment": "BULLISH|BEARISH|NEUTRAL",
    "sources": ["url1", "url2"],
    "estimated_probability": 0.XX,
    "market_odds": {odds_decimal},
    "edge_percentage": XX.X,
    "recommendation": "LONG|SHORT|AVOID",
    "confidence": 1-10,
    "reasoning": "Detailed explanation of your analysis...",
    "risk_factors": ["risk1", "risk2", "risk3"]
}}

Respond ONLY with valid JSON. No additional text."""


class ResearchAnalyzer:
    """Research and analysis engine using Perplexity Search API and Z.AI GLM-4.7.

    Pipeline:
    1. Use Perplexity Search API to get web search results (Batchable)
    2. Pass search results to GLM-4.7 for analysis and recommendations (Concurrency limited to 2)
    """

    def __init__(self, config: AIConfig | None = None):
        """Initialize with AI configuration."""
        self.config = config or AIConfig.from_env()
        self._validate_config()
        # GLM-4.7 concurrency limit (user specified limit of 2)
        self.glm_semaphore = asyncio.Semaphore(2)

    def _validate_config(self) -> None:
        """Validate that required API keys are present."""
        if not self.config.PERPLEXITY_API_KEY:
            logger.warning("PERPLEXITY_API_KEY not set - web search will be limited")
        if not self.config.ZAI_API_KEY:
            logger.warning("ZAI_API_KEY not set - analysis will be limited")

    async def search_web(
        self,
        query: str | list[str],
        max_results: int = 5,
        timeout: int = 30,
    ) -> list[dict[str, str]]:
        """
        Search the web using Perplexity Search API.
        Supports batched queries to optimize API usage.

        Args:
            query: Search query or list of queries
            max_results: Maximum number of results
            timeout: Request timeout in seconds

        Returns:
            List of search results with title, url, snippet, date
        """
        if not self.config.PERPLEXITY_API_KEY:
            logger.warning("Skipping web search - no API key")
            return []

        # Optimize: Combine multiple queries into one prompt if list provided
        final_query = query
        if isinstance(query, list):
            # Formulate a multi-topic research query
            # "Research the following topics: 1. ... 2. ... "
            numbered_topics = "\n".join([f"{i + 1}. {q}" for i, q in enumerate(query)])
            final_query = (
                f"Research detailed information for the following topics:\n{numbered_topics}"
            )
            logger.info(f"Batched {len(query)} queries into single request")

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.config.PERPLEXITY_BASE_URL}/search",
                    headers={
                        "Authorization": f"Bearer {self.config.PERPLEXITY_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": final_query,
                        "max_results": max_results,  # Perplexity usually handles 5-10 well
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Extract results
                results = []
                for item in data.get("results", []):
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("snippet", ""),
                            "date": item.get("date", ""),
                        }
                    )

                logger.info(f"Found {len(results)} search results for: {str(query)[:50]}...")
                return results

        except httpx.HTTPError as e:
            logger.error(f"Perplexity Search API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    async def analyze_with_glm(
        self,
        market: PolymarketMarket,
        search_results: list[dict[str, str]],
        timeout: int = 60,
    ) -> tuple[ResearchResult | None, AnalysisResult | None]:
        """
        Analyze market using GLM-4.7 with search results.
        """
        # Acquire semaphore to respect concurrency limit
        async with self.glm_semaphore:
            if not self.config.ZAI_API_KEY:
                logger.warning("Skipping analysis - no ZAI_API_KEY")
                return self._create_fallback_research(market), self._create_fallback_analysis(
                    market
                )

            # Format search results for the prompt
            formatted_results = self._format_search_results(search_results)

            # Calculate current odds
            odds = market.outcomes[0].price * 100 if market.outcomes else 50
            odds_decimal = odds / 100

            prompt = GLM_ANALYSIS_PROMPT.format(
                question=market.question,
                description=market.description[:500],
                odds=f"{odds:.1f}",
                odds_decimal=f"{odds_decimal:.2f}",
                end_date=market.end_date or "Not specified",
                search_results=formatted_results,
            )

            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{self.config.ZAI_BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.config.ZAI_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.config.ZAI_MODEL,
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "You are an expert prediction market analyst. Analyze web search results and provide trading recommendations. Always respond with valid JSON only.",
                                },
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": 0.3,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Extract content from response
                    content = data["choices"][0]["message"]["content"]
                    return self._parse_combined_response(market, content, search_results)

            except httpx.HTTPError as e:
                logger.error(f"Z.AI API error for market {market.id}: {e}")
                return self._create_fallback_research(market), self._create_fallback_analysis(
                    market
                )
            except Exception as e:
                logger.error(f"Analysis failed for market {market.id}: {e}")
                return self._create_fallback_research(market), self._create_fallback_analysis(
                    market
                )

    def _format_search_results(self, results: list[dict[str, str]]) -> str:
        """Format search results for the prompt."""
        if not results:
            return "No search results available."

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"""
### Result {i}
- **Title**: {r.get("title", "N/A")}
- **URL**: {r.get("url", "N/A")}
- **Date**: {r.get("date", "N/A")}
- **Content**: {r.get("snippet", "N/A")[:500]}
""")
        return "\n".join(formatted)

    async def research_and_analyze(
        self,
        market: PolymarketMarket,
    ) -> tuple[ResearchResult | None, AnalysisResult | None]:
        """
        Perform web search and analysis for a single market.
        Wrapper around simplified pipeline.
        """
        # Step 1: Search the web
        search_query = f"{market.question} latest news predictions"
        search_results = await self.search_web(search_query)

        if not search_results:
            logger.warning(f"No search results for market {market.id}")

        # Step 2: Analyze with GLM-4.7 (concurrency limited inside the method)
        research, analysis = await self.analyze_with_glm(market, search_results)

        return research, analysis

    async def batch_research_and_analyze(
        self,
        markets: list[PolymarketMarket],
        concurrency: int = 2,  # Default reduced to 2 as per user request
    ) -> list[tuple[PolymarketMarket, ResearchResult | None, AnalysisResult | None]]:
        """
        Batch process multiple markets with optimized API usage.

        Strategy:
        1. Group markets into chunks (batch size 3).
        2. Perform batched search for each chunk (1 API call per 3 markets).
        3. Perform analysis for all markets (concurrency limited to 2 by semaphore).

        Args:
            markets: List of markets to process
            concurrency: Ignored for GLM (enforced by semaphore), serves as chunk size for search batching.
                        (Repurposing arg to stay API compatible but optimize internally)

        Returns:
            List of (market, research, analysis) tuples
        """
        # Create chunks for batched search
        batch_size = 3  # Optimal batch size for Perplexity prompt context
        chunks = [markets[i : i + batch_size] for i in range(0, len(markets), batch_size)]

        results_map = {}  # map market_id -> research results

        # Phase 1: Batched Search
        logger.info(
            f"Starting batched search for {len(markets)} markets in {len(chunks)} batches..."
        )

        async def process_search_chunk(chunk):
            queries = [f"{m.question} latest news" for m in chunk]
            # Combined search
            search_results = await self.search_web(queries)
            # Assign same results to all markets in chunk (context sharing)
            # Note: Ideally we'd map specific results, but broadly related markets or comprehensive search
            # often returns results covering multiple topics if prompted.
            # Or we assume the user groups related markets.
            # Even if unrelated, Perplexity usually returns segmented results.
            # We'll pass the full context to GLM and let it pick relevant info.
            return chunk, search_results

        search_tasks = [process_search_chunk(chunk) for chunk in chunks]
        chunk_results = await asyncio.gather(*search_tasks)

        # Phase 2: Analysis (Semaphored)
        logger.info("Starting semaphored analysis...")

        async def process_analysis(market, results):
            research, analysis = await self.analyze_with_glm(market, results)
            return market, research, analysis

        analysis_tasks = []
        for chunk, search_results in chunk_results:
            for market in chunk:
                analysis_tasks.append(process_analysis(market, search_results))

        # Run all analysis tasks - semaphore inside analyze_with_glm controls concurrency
        results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Batch processing error: {result}")
            else:
                valid_results.append(result)

        return valid_results

    def _parse_combined_response(
        self,
        market: PolymarketMarket,
        content: str,
        search_results: list[dict[str, str]],
    ) -> tuple[ResearchResult, AnalysisResult]:
        """Parse GLM-4.7 response into ResearchResult and AnalysisResult."""
        try:
            data = self._extract_json(content)

            # Parse research part
            sentiment_str = data.get("sentiment", "NEUTRAL").upper()
            sentiment = (
                Sentiment[sentiment_str]
                if sentiment_str in Sentiment.__members__
                else Sentiment.NEUTRAL
            )

            # Extract sources from search results if not in response
            sources = data.get("sources", [])
            if not sources and search_results:
                sources = [r.get("url", "") for r in search_results[:5] if r.get("url")]

            research = ResearchResult(
                market_id=market.id,
                question=market.question,
                key_findings=data.get("key_findings", [])[:5],
                recent_news=data.get("recent_news", [])[:3],
                sentiment=sentiment,
                confidence=min(10, max(1, int(data.get("confidence", 5)))),
                sources=sources[:5],
                raw_response=content,
            )

            # Parse analysis part
            rec_str = data.get("recommendation", "AVOID").upper()
            recommendation = (
                Recommendation[rec_str]
                if rec_str in Recommendation.__members__
                else Recommendation.AVOID
            )

            analysis = AnalysisResult(
                market_id=market.id,
                question=market.question,
                estimated_probability=float(data.get("estimated_probability", 0.5)),
                market_odds=float(data.get("market_odds", 0.5)),
                edge_percentage=float(data.get("edge_percentage", 0)),
                recommendation=recommendation,
                confidence=min(10, max(1, int(data.get("confidence", 5)))),
                reasoning=data.get("reasoning", "No reasoning provided"),
                risk_factors=data.get("risk_factors", [])[:5],
            )

            return research, analysis

        except Exception as e:
            logger.error(f"Error parsing GLM response: {e}")
            raise

    def _extract_json(self, content: str) -> dict[str, Any]:
        """Extract JSON from response content."""
        # Try direct parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block in content
        import re

        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {}

    def _create_fallback_research(self, market: PolymarketMarket) -> ResearchResult:
        """Create a fallback research result when API fails."""
        return ResearchResult(
            market_id=market.id,
            question=market.question,
            key_findings=["Research unavailable - API key not configured or request failed"],
            recent_news=[],
            sentiment=Sentiment.NEUTRAL,
            confidence=1,
            sources=[],
            raw_response="",
        )

    def _create_fallback_analysis(self, market: PolymarketMarket) -> AnalysisResult:
        """Create a fallback analysis result when API fails."""
        odds = market.outcomes[0].price if market.outcomes else 0.5
        return AnalysisResult(
            market_id=market.id,
            question=market.question,
            estimated_probability=odds,
            market_odds=odds,
            edge_percentage=0,
            recommendation=Recommendation.AVOID,
            confidence=1,
            reasoning="Analysis unavailable - using market odds as estimate",
            risk_factors=["No AI analysis available"],
        )
