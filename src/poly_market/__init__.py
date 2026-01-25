"""Polymarket integration module."""

from .models import (
    AnalysisResult,
    MarketOutcome,
    PolymarketEvent,
    PolymarketMarket,
    Recommendation,
    ResearchResult,
    Sentiment,
    TradingSuggestion,
)
from .polymarket_client import PolymarketClient
from .research_analyzer import ResearchAnalyzer
from .suggestion_engine import SuggestionEngine

__all__ = [
    # Config
    "AIConfig",
    "PolymarketConfig",
    "POLYMARKET_CONFIG",
    # Models
    "AnalysisResult",
    "MarketOutcome",
    "PolymarketEvent",
    "PolymarketMarket",
    "Recommendation",
    "ResearchResult",
    "Sentiment",
    "TradingSuggestion",
    # Clients
    "PolymarketClient",
    "ResearchAnalyzer",
    "SuggestionEngine",
]
