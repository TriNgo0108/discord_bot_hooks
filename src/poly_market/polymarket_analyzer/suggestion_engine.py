"""Suggestion engine for generating trading recommendations."""

import logging
from collections.abc import Generator

from .models import (
    AnalysisResult,
    PolymarketEvent,
    PolymarketMarket,
    Recommendation,
    ResearchResult,
    TradingSuggestion,
)

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """Generate and rank trading suggestions from research and analysis."""

    def __init__(
        self,
        min_confidence: int = 5,
        min_edge: float = 0.10,
        min_volume: float = 1000,
    ):
        """
        Initialize the suggestion engine.

        Args:
            min_confidence: Minimum confidence score (1-10) to include
            min_edge: Minimum edge percentage to include (0.10 = 10%)
            min_volume: Minimum market volume to consider
        """
        self.min_confidence = min_confidence
        self.min_edge = min_edge
        self.min_volume = min_volume

    def generate_suggestion(
        self,
        event: PolymarketEvent,
        market: PolymarketMarket,
        research: ResearchResult,
        analysis: AnalysisResult,
    ) -> TradingSuggestion | None:
        """
        Generate a trading suggestion from research and analysis.

        Returns:
            TradingSuggestion or None if criteria not met
        """
        # Skip if recommendation is AVOID
        if analysis.recommendation == Recommendation.AVOID:
            logger.debug(f"Skipping market {market.id}: recommendation is AVOID")
            return None

        # Check minimum edge
        edge = abs(analysis.estimated_probability - analysis.market_odds)
        if edge < self.min_edge:
            logger.debug(f"Skipping market {market.id}: edge {edge:.2%} below threshold")
            return None

        # Check minimum confidence
        if analysis.confidence < self.min_confidence:
            logger.debug(
                f"Skipping market {market.id}: confidence {analysis.confidence} below threshold"
            )
            return None

        # Check minimum volume
        if market.volume < self.min_volume:
            logger.debug(f"Skipping market {market.id}: volume {market.volume} below threshold")
            return None

        return TradingSuggestion(
            event_id=event.id,
            event_title=event.title,
            market_id=market.id,
            market_question=market.question,
            current_odds=analysis.market_odds,
            estimated_probability=analysis.estimated_probability,
            edge=edge,
            recommendation=analysis.recommendation,
            confidence=analysis.confidence,
            reasoning=analysis.reasoning,
            risk_factors=analysis.risk_factors,
            key_findings=research.key_findings,
            sources=research.sources,
        )

    def generate_suggestions_batch(
        self,
        results: list[
            tuple[
                PolymarketEvent,
                PolymarketMarket,
                ResearchResult | None,
                AnalysisResult | None,
            ]
        ],
    ) -> list[TradingSuggestion]:
        """
        Generate suggestions from a batch of results.

        Args:
            results: List of (event, market, research, analysis) tuples

        Returns:
            List of TradingSuggestion objects, sorted by edge descending
        """
        suggestions = []

        for event, market, research, analysis in results:
            if research is None or analysis is None:
                continue

            suggestion = self.generate_suggestion(event, market, research, analysis)
            if suggestion:
                suggestions.append(suggestion)

        # Sort by edge descending (best opportunities first)
        suggestions.sort(key=lambda s: s.edge, reverse=True)

        logger.info(f"Generated {len(suggestions)} trading suggestions")
        return suggestions

    def filter_suggestions(
        self,
        suggestions: list[TradingSuggestion],
        max_suggestions: int = 10,
        recommendation_filter: Recommendation | None = None,
    ) -> list[TradingSuggestion]:
        """
        Filter and limit suggestions.

        Args:
            suggestions: List of suggestions to filter
            max_suggestions: Maximum number to return
            recommendation_filter: Optional filter for specific recommendation type

        Returns:
            Filtered list of suggestions
        """
        filtered = suggestions

        if recommendation_filter:
            filtered = [s for s in filtered if s.recommendation == recommendation_filter]

        return filtered[:max_suggestions]

    def suggestions_generator(
        self,
        results: list[
            tuple[
                PolymarketEvent,
                PolymarketMarket,
                ResearchResult | None,
                AnalysisResult | None,
            ]
        ],
    ) -> Generator[TradingSuggestion, None, None]:
        """
        Memory-efficient generator for suggestions.

        Yields suggestions one at a time without building full list.
        """
        for event, market, research, analysis in results:
            if research is None or analysis is None:
                continue

            suggestion = self.generate_suggestion(event, market, research, analysis)
            if suggestion:
                yield suggestion

    def format_suggestions_report(
        self,
        suggestions: list[TradingSuggestion],
    ) -> str:
        """
        Format suggestions as a readable report.

        Args:
            suggestions: List of suggestions to format

        Returns:
            Formatted report string
        """
        if not suggestions:
            return "No trading suggestions meet the criteria."

        lines = [
            "=" * 60,
            "POLYMARKET TRADING SUGGESTIONS",
            "=" * 60,
            "",
        ]

        for i, s in enumerate(suggestions, 1):
            lines.extend(
                [
                    f"#{i} - {s.recommendation.value}",
                    f"Event: {s.event_title}",
                    f"Question: {s.market_question}",
                    f"Current Odds: {s.current_odds:.1%}",
                    f"Estimated Probability: {s.estimated_probability:.1%}",
                    f"Edge: {s.edge:.1%}",
                    f"Confidence: {s.confidence}/10",
                    "",
                    f"Reasoning: {s.reasoning[:200]}...",
                    "",
                    "Key Findings:",
                    *[f"  • {f}" for f in s.key_findings[:3]],
                    "",
                    "Risk Factors:",
                    *[f"  ⚠ {r}" for r in s.risk_factors[:3]],
                    "",
                    "-" * 60,
                    "",
                ]
            )

        return "\n".join(lines)

    def to_json_report(
        self,
        suggestions: list[TradingSuggestion],
    ) -> list[dict]:
        """
        Convert suggestions to JSON-serializable format.

        Returns:
            List of suggestion dictionaries
        """
        return [s.to_dict() for s in suggestions]
