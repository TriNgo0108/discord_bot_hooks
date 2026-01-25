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
    1. Use Perplexity Search API to get web search results
    2. Pass search results to GLM-4.7 for analysis and recommendations
    """

    def __init__(self, config: AIConfig | None = None):
        """Initialize with AI configuration."""
        self.config = config or AIConfig.from_env()
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate that required API keys are present."""
        if not self.config.PERPLEXITY_API_KEY:
            logger.warning("PERPLEXITY_API_KEY not set - web search will be limited")
        if not self.config.ZAI_API_KEY:
            logger.warning("ZAI_API_KEY not set - analysis will be limited")

    async def search_web(
        self,
        query: str,
        max_results: int = 5,
        timeout: int = 30,
    ) -> list[dict[str, str]]:
        """
        Search the web using Perplexity Search API.

        Args:
            query: Search query
            max_results: Maximum number of results
            timeout: Request timeout in seconds

        Returns:
            List of search results with title, url, snippet, date
        """
        if not self.config.PERPLEXITY_API_KEY:
            logger.warning("Skipping web search - no API key")
            return []

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.config.PERPLEXITY_BASE_URL}/search",
                    headers={
                        "Authorization": f"Bearer {self.config.PERPLEXITY_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": query,
                        "max_results": max_results,
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

                logger.info(f"Found {len(results)} search results for: {query[:50]}...")
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

        Args:
            market: The market to analyze
            search_results: Web search results from Perplexity
            timeout: Request timeout in seconds

        Returns:
            Tuple of (ResearchResult, AnalysisResult)
        """
        if not self.config.ZAI_API_KEY:
            logger.warning("Skipping analysis - no ZAI_API_KEY")
            return self._create_fallback_research(market), self._create_fallback_analysis(market)

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
                        "max_tokens": 2048,
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
            return self._create_fallback_research(market), self._create_fallback_analysis(market)
        except Exception as e:
            logger.error(f"Analysis failed for market {market.id}: {e}")
            return self._create_fallback_research(market), self._create_fallback_analysis(market)

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
        Perform web search and analysis for a market.

        Pipeline:
        1. Search web using Perplexity Search API
        2. Analyze results with GLM-4.7

        Returns:
            Tuple of (ResearchResult, AnalysisResult)
        """
        # Step 1: Search the web
        search_query = f"{market.question} latest news predictions"
        search_results = await self.search_web(search_query)

        if not search_results:
            logger.warning(f"No search results for market {market.id}")
            # Still try to analyze with just market info

        # Step 2: Analyze with GLM-4.7
        research, analysis = await self.analyze_with_glm(market, search_results)

        return research, analysis

    async def batch_research_and_analyze(
        self,
        markets: list[PolymarketMarket],
        concurrency: int = 3,
    ) -> list[tuple[PolymarketMarket, ResearchResult | None, AnalysisResult | None]]:
        """
        Batch process multiple markets with rate limiting.

        Args:
            markets: List of markets to process
            concurrency: Maximum concurrent requests

        Returns:
            List of (market, research, analysis) tuples
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def process_market(
            market: PolymarketMarket,
        ) -> tuple[PolymarketMarket, ResearchResult | None, AnalysisResult | None]:
            async with semaphore:
                # Add delay between requests to respect rate limits
                await asyncio.sleep(2)
                research, analysis = await self.research_and_analyze(market)
                return market, research, analysis

        tasks = [process_market(m) for m in markets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

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
            logger.warning(f"Failed to parse response: {e}")
            return self._create_fallback_research(market), self._create_fallback_analysis(market)

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
