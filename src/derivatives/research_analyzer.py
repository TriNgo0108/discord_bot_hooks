"""Research analyzer for derivatives using Perplexity and GLM-4.7."""

import json
import logging
from typing import Any

import httpx

from src.common.tavily_client import TavilyClient
from .config import DERIVATIVES_CONFIG
from .models import DerivativesAnalysis, TradingRecommendation

logger = logging.getLogger(__name__)

# System prompt for GLM-4.7 analysis
GLM_ANALYSIS_PROMPT = """You are a senior derivatives trading analyst at a quantitative hedge fund. 
Your task is to analyze aggregated derivatives market data and web research to provide actionable trading intelligence.

## Market Data
{derivatives_data}

## Web Research Results
{search_results}

---

## Analysis Framework

Think step-by-step:

### Step 1: Data Synthesis
Combine the quantitative data (funding rates, open interest, options flow, COT) with qualitative research findings (news, sentiment).

### Step 2: Key Patterns
Identify significant patterns such as:
- Divergences between price and Open Interest
- Anomalous funding rates (e.g., highly negative funding in uptrend)
- Unusual options activity (heavy call buying, put skew)
- Institutional positioning changes (COT data)

### Step 3: Risk Assessment
Evaluate potential risks, upcoming events, and volatility catalysts.

### Step 4: Recommendations
Provide specific, actionable suggestions. For each recommendation, specify:
- Direction (LONG/SHORT/NEUTRAL)
- Confidence (1-10)
- Timeframe (Intraday, Weekly, Monthly)
- Reasoning based on data
- Key levels (Support/Resistance)

---

## Output Format (JSON only)

{{
    "key_findings": ["finding1", "finding2", "finding3"],
    "market_sentiment": "BULLISH|BEARISH|NEUTRAL|MIXED",
    "notable_flows": ["flow1", "flow2"],
    "risk_factors": ["risk1", "risk2"],
    "recommendations": [
        {{
            "instrument": "BTC Perpetual",
            "direction": "LONG",
            "confidence": 8,
            "timeframe": "1 week",
            "reasoning": "Negative funding with rising OI suggests short squeeze potential...",
            "key_levels": {{"support": 42000, "resistance": 45000}},
            "risk_factors": ["SEC announcement"]
        }}
    ],
    "sources": ["url1", "url2"]
}}

Respond ONLY with valid JSON. No additional text."""


class ResearchAnalyzer:
    """Analyzer using Perplexity and Z.AI."""

    def __init__(self, http_client: httpx.AsyncClient):
        self.config = DERIVATIVES_CONFIG
        self.client = http_client
        self.tavily = TavilyClient(api_key=self.config.TAVILY_API_KEY)

    async def analyze(self, market_data: dict[str, Any]) -> DerivativesAnalysis | None:
        """
        Full analysis pipeline: Research -> Analyze.
        """
        # 1. Web Research
        search_query = self._generate_search_query(market_data)
        search_results = await self.search_web(search_query)

        # 2. AI Analysis
        analysis = await self.analyze_with_glm(market_data, search_results)
        return analysis

    def _generate_search_query(self, market_data: dict[str, Any]) -> str:
        """Generate a search query based on active instruments."""
        # Extract unique instruments
        instruments = {i.get("instrument", "") for i in market_data.get("market_structure", [])}

        params = " ".join(instruments)
        if not params:
            params = "SPY QQQ"

        return f"{params} derivatives market sentiment options flow cftc positioning"

    async def search_web(self, query: str) -> list[dict[str, str]]:
        """Tavily web search."""
        if not self.config.TAVILY_API_KEY:
            logger.warning("No TAVILY_API_KEY")
            return []

        try:
            results = await self.tavily.search(query=query, max_results=5)
            # Normalize to list of dicts with url, title, snippet (content)
            return [
                {
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "snippet": r.get("content", "")[:300],  # Truncate content for snippet
                }
                for r in results.get("results", [])
            ]

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _create_fallback_analysis(self, market_data: dict[str, Any]) -> DerivativesAnalysis:
        """Create a fallback analysis when AI service is unavailable."""
        timestamp = __import__("datetime").datetime.utcnow()

        # Extract basic info
        futures = market_data.get("market_structure", [])
        findings = []
        recommendations = []

        for f in futures:
            symbol = f.get("symbol", "Unknown")
            price = f.get("last_price", 0)
            findings.append(f"Auto-Report: {symbol} trading at {price}")

            # Simple dummy recommendation to ensure structure exists
            recommendations.append(
                TradingRecommendation(
                    instrument=symbol,
                    direction="NEUTRAL",
                    confidence=5,
                    timeframe="Intraday",
                    reasoning=f"Automated data report. Price: {price}",
                    key_levels={},
                    risk_factors=["AI Analysis Unavailable"],
                )
            )

        return DerivativesAnalysis(
            timestamp=timestamp,
            market_data={},
            key_findings=findings if findings else ["No data available"],
            market_sentiment="NEUTRAL",
            notable_flows=["AI analysis skipped"],
            risk_factors=["Trading on raw data only"],
            recommendations=recommendations,
            sources=["vnstock"],
        )

    async def analyze_with_glm(
        self, market_data: dict[str, Any], search_results: list[dict[str, str]] | None
    ) -> DerivativesAnalysis | None:
        """Analyze with GLM-4.7."""
        if not self.config.ZAI_API_KEY:
            logger.warning("No ZAI_API_KEY. Using fallback analysis.")
            return self._create_fallback_analysis(market_data)

        # Summarize data for prompt to avoid token limits
        data_summary = json.dumps(market_data, default=str)[:8000]  # Truncate if too huge

        search_text = "\n".join([f"- {r['url']}" for r in search_results])

        prompt = GLM_ANALYSIS_PROMPT.format(
            derivatives_data=data_summary, search_results=search_text
        )

        try:
            response = await self.client.post(
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",  # Official Zhipu URL usually
                # Use config base url if set, otherwise default
                headers={
                    "Authorization": f"Bearer {self.config.ZAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "glm-4",  # Or glm-4.7 if available
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return self._parse_response(content)

        except Exception as e:
            logger.error(f"GLM analysis failed: {e}")
            return self._create_fallback_analysis(market_data)

    def _parse_response(self, content: str) -> DerivativesAnalysis | None:
        """Parse JSON response."""
        try:
            # Extract JSON
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "{" in content:
                json_str = content[content.find("{") : content.rfind("}") + 1]

            data = json.loads(json_str)

            # Map recommendations
            recs = []
            for r in data.get("recommendations", []):
                recs.append(
                    TradingRecommendation(
                        instrument=r.get("instrument", "Unknown"),
                        direction=r.get("direction", "NEUTRAL"),
                        confidence=r.get("confidence", 5),
                        timeframe=r.get("timeframe", "intraday"),
                        reasoning=r.get("reasoning", ""),
                        key_levels=r.get("key_levels", {}),
                        risk_factors=r.get("risk_factors", []),
                    )
                )

            return DerivativesAnalysis(
                timestamp=__import__("datetime").datetime.utcnow(),
                market_data={},  # Don't store full raw data in analysis object to save space
                key_findings=data.get("key_findings", []),
                market_sentiment=data.get("market_sentiment", "NEUTRAL"),
                notable_flows=data.get("notable_flows", []),
                risk_factors=data.get("risk_factors", []),
                recommendations=recs,
                sources=data.get("sources", []),
            )

        except Exception as e:
            logger.error(f"Failed to parse analysis response: {e}")
            return None
