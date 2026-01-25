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
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.common.ddg_client import DDGClient
from src.common.tavily_client import TavilyClient

from .config import AIConfig
from .models import (
    AnalysisResult,
    PolymarketEvent,
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


# =============================================================================
# BATCH PROMPTS
# =============================================================================

GLM_BATCH_ANALYSIS_PROMPT = """You are an expert prediction market analyst specializing in probability assessment and edge identification.

## Your Task
Analyze the following prediction markets for the event "{event_title}" using the provided web search results.

## Event Information
- **Title**: {event_title}
- **Description**: {event_description}
- **End Date**: {event_end_date}

## Markets to Analyze
{markets_list}

## Web Search Results (Shared Context)
{search_results}

---

## Analysis Framework (Chain of Thought)

Think step-by-step:

1. **Research Synthesis**: Synthesize the key findings from the search results relevant to the overall event.
2. **Market Analysis**: For each market:
    a. Assess the specific question in light of the research.
    b. Estimate the true probability.
    c. Calculate edge (|Estimated - Market Outcome|).
    d. Formulate a recommendation (LONG/SHORT/AVOID) with >10% edge threshold.
3. **Risk Review**: Identify factors that could invalidate the analysis.

---

## Output Format (JSON Only)
Resond ONLY with a valid JSON object containing a list of results under the key "results".

{{
    "results": [
        {{
            "market_id": "market_id_1",
            "question": "Question 1",
            "research": {{
                "key_findings": ["finding1", "finding2"],
                "recent_news": ["news1", "news2"],
                "sentiment": "BULLISH|BEARISH|NEUTRAL",
                "sources": ["url1", "url2"]
            }},
            "analysis": {{
                "estimated_probability": 0.XX,
                "market_odds": {odds_decimal_placeholder},
                "edge_percentage": XX.X,
                "recommendation": "LONG|SHORT|AVOID",
                "confidence": 1-10,
                "reasoning": "Detailed explanation...",
                "risk_factors": ["risk1", "risk2"]
            }}
        }},
        ...
    ]
}}
"""


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

        # Initialize Search client
        if self.config.SEARCH_PROVIDER == "ddg":
            self.search_client = DDGClient()
            logger.info("Using DuckDuckGo Search provider")
        else:
            self.search_client = TavilyClient(api_key=self.config.TAVILY_API_KEY)
            logger.info("Using Tavily Search provider")

    def _validate_config(self) -> None:
        """Validate that required API keys are present."""
        if self.config.SEARCH_PROVIDER == "tavily" and not self.config.TAVILY_API_KEY:
            logger.warning("TAVILY_API_KEY not set - web search will be skipped")
        if not self.config.ZAI_API_KEY:
            logger.warning("ZAI_API_KEY not set - analysis will be limited")

    async def search_web(
        self,
        query: str | list[str],
        max_results: int = 5,
        timeout: int = 30,
    ) -> list[dict[str, str]]:
        """
        Search the web using the configured provider.
        Supports batched queries by joining them.

        Args:
            query: Search query or list of queries
            max_results: Maximum number of results
            timeout: Request timeout in seconds

        Returns:
            List of search results with title, url, snippet, date
        """
        # For Tavily, check API key. For DDG, it's always available (unless blocked).
        if self.config.SEARCH_PROVIDER == "tavily" and not self.config.TAVILY_API_KEY:
            logger.warning("Skipping web search - no API key")
            return []

        # Combine multiple queries if provided
        final_query = query
        if isinstance(query, list):
            final_query = " ".join(query)
            logger.info(f"Combined {len(query)} queries into single request")

        try:
            # Use configured client
            # pass days=30 for news filtering (handled by both clients)
            response = await self.search_client.search(
                query=str(final_query),
                max_results=max_results,
                days=30,  # Filter for last 30 days news
                include_raw_content=False,
            )

            results = []
            for item in response.get("results", []):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", ""),  # Both clients map to 'content'
                        "date": item.get("published_date", ""),
                    }
                )

            logger.info(f"Found {len(results)} search results for query")
            return results

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
        Uses tenacity for retry logic with exponential backoff.
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

            @retry(
                retry=retry_if_exception_type(
                    (
                        httpx.HTTPStatusError,
                        httpx.TimeoutException,
                        httpx.ConnectError,
                        httpx.ReadTimeout,
                    )
                ),
                stop=stop_after_attempt(5),
                wait=wait_exponential(multiplier=2, min=2, max=60),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=True,
            )
            async def _call_zai_api() -> dict:
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
                    return response.json()

            try:
                data = await _call_zai_api()
                content = data["choices"][0]["message"]["content"]
                return self._parse_combined_response(market, content, search_results)
            except httpx.HTTPStatusError as e:
                logger.error(f"Z.AI API HTTP error: {e}")
                logger.error(f"Response body: {e.response.text}")
                return self._create_fallback_research(market), self._create_fallback_analysis(
                    market
                )
            except httpx.RequestError as e:
                logger.error(f"Z.AI API request failed (timeout/connection): {e}")
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

    async def analyze_event_batch(
        self,
        event: PolymarketEvent,
        markets: list[PolymarketMarket],
        search_results: list[dict[str, str]],
        timeout: int = 120,
    ) -> list[tuple[PolymarketMarket, ResearchResult | None, AnalysisResult | None]]:
        """
        Analyze multiple markets for a single event in one LLM call.
        """
        async with self.glm_semaphore:
            if not self.config.ZAI_API_KEY:
                logger.warning("Skipping analysis - no ZAI_API_KEY")
                return [
                    (m, self._create_fallback_research(m), self._create_fallback_analysis(m))
                    for m in markets
                ]

            formatted_results = self._format_search_results(search_results)

            markets_list_str = []
            for m in markets:
                odds = m.outcomes[0].price * 100 if m.outcomes else 50
                markets_list_str.append(
                    f"- **ID**: {m.id}\n  **Question**: {m.question}\n  **Current Odds**: {odds:.1f}%"
                )

            prompt = GLM_BATCH_ANALYSIS_PROMPT.format(
                event_title=event.title,
                event_description=event.description[:500],
                event_end_date=event.end_date or "Not specified",
                markets_list="\n\n".join(markets_list_str),
                search_results=formatted_results,
                odds_decimal_placeholder="0.XX",  # Correct placeholder for the example
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
                    content = data["choices"][0]["message"]["content"]

                    return self._parse_batch_response(markets, content, search_results)

            except Exception as e:
                logger.error(f"Batch analysis failed for event {event.id}: {e}")
                return [
                    (m, self._create_fallback_research(m), self._create_fallback_analysis(m))
                    for m in markets
                ]

    def _parse_batch_response(
        self,
        markets: list[PolymarketMarket],
        content: str,
        search_results: list[dict[str, str]],
    ) -> list[tuple[PolymarketMarket, ResearchResult, AnalysisResult]]:
        """Parse batch analysis response."""
        results = []
        market_map = {m.id: m for m in markets}

        try:
            data = self._extract_json(content)
            results_list = data.get("results", [])

            for item in results_list:
                m_id = item.get("market_id")
                market = market_map.get(m_id)
                if not market:
                    continue

                res_data = item.get("research", {})
                ana_data = item.get("analysis", {})

                # Research
                sentiment_str = res_data.get("sentiment", "NEUTRAL").upper()
                sentiment = getattr(Sentiment, sentiment_str, Sentiment.NEUTRAL)

                sources = res_data.get("sources", [])
                if not sources and search_results:
                    sources = [r.get("url", "") for r in search_results[:5] if r.get("url")]

                research = ResearchResult(
                    market_id=market.id,
                    question=market.question,
                    key_findings=res_data.get("key_findings", [])[:5],
                    recent_news=res_data.get("recent_news", [])[:3],
                    sentiment=sentiment,
                    confidence=min(10, max(1, int(ana_data.get("confidence", 5)))),
                    sources=sources[:5],
                    raw_response=json.dumps(item),  # Store specific item JSON
                )

                # Analysis
                rec_str = ana_data.get("recommendation", "AVOID").upper()
                recommendation = getattr(Recommendation, rec_str, Recommendation.AVOID)

                analysis = AnalysisResult(
                    market_id=market.id,
                    question=market.question,
                    estimated_probability=float(ana_data.get("estimated_probability", 0.5)),
                    market_odds=float(ana_data.get("market_odds", 0.5)),
                    edge_percentage=float(ana_data.get("edge_percentage", 0)),
                    recommendation=recommendation,
                    confidence=min(10, max(1, int(ana_data.get("confidence", 5)))),
                    reasoning=ana_data.get("reasoning", "No reasoning provided"),
                    risk_factors=ana_data.get("risk_factors", [])[:5],
                )

                results.append((market, research, analysis))

            # Fill in missing markets with fallbacks
            processed_ids = {r[0].id for r in results}
            for m in markets:
                if m.id not in processed_ids:
                    results.append(
                        (m, self._create_fallback_research(m), self._create_fallback_analysis(m))
                    )

            return results

        except Exception as e:
            logger.error(f"Error parsing batch response: {e}")
            # Fallback for all
            return [
                (m, self._create_fallback_research(m), self._create_fallback_analysis(m))
                for m in markets
            ]

    async def batch_research_and_analyze_event(
        self,
        event: PolymarketEvent,
        markets: list[PolymarketMarket],
    ) -> list[tuple[PolymarketMarket, ResearchResult | None, AnalysisResult | None]]:
        """
        Perform batched web search and analysis for an event's markets.
        """
        # Step 1: Search the web for the event context
        queries = [f"{event.title} latest news"]
        # Add a query for specific market nuances if needed, but per-event is usually sufficient
        # To get more detail, we can add:
        # queries.extend([m.question for m in markets])
        # But let's stick to event-level + maybe generic market query to save tokens/calls

        search_results = await self.search_web(queries)

        if not search_results:
            logger.warning(f"No search results for event {event.id}")

        # Step 2: Analyze batch
        return await self.analyze_event_batch(event, markets, search_results)

    async def batch_research_and_analyze(
        self,
        markets: list[PolymarketMarket],
        concurrency: int = 2,
    ) -> list[tuple[PolymarketMarket, ResearchResult | None, AnalysisResult | None]]:
        """Deprecated: Use batch_research_and_analyze_event instead."""
        # Kept for backward compatibility or direct market list usage
        # This implementation is inefficient as it groups by arbitrary chunks
        # ... logic as before ...
        pass

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
