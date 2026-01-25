"""Data models for Polymarket integration."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Recommendation(Enum):
    """Trading recommendation types."""

    LONG = "LONG"
    SHORT = "SHORT"
    AVOID = "AVOID"


class Sentiment(Enum):
    """Market sentiment types."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass(slots=True)
class MarketOutcome:
    """Represents a single outcome in a market."""

    name: str
    price: float  # 0.0 to 1.0 representing probability
    token_id: str = ""


@dataclass(slots=True)
class PolymarketMarket:
    """Represents a prediction market."""

    id: str
    question: str
    description: str
    outcomes: list[MarketOutcome]
    volume: float = 0.0
    liquidity: float = 0.0
    end_date: str = ""
    slug: str = ""
    active: bool = True


@dataclass(slots=True)
class PolymarketEvent:
    """Represents an event containing multiple markets."""

    id: str
    title: str
    description: str
    slug: str
    end_date: str
    markets: list[PolymarketMarket] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResearchResult:
    """Research findings from Perplexity AI."""

    market_id: str
    question: str
    key_findings: list[str]
    recent_news: list[str]
    sentiment: Sentiment
    confidence: int  # 1-10
    sources: list[str]
    raw_response: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(slots=True)
class AnalysisResult:
    """Analysis result from Z.AI."""

    market_id: str
    question: str
    estimated_probability: float  # 0.0 to 1.0
    market_odds: float
    edge_percentage: float
    recommendation: Recommendation
    confidence: int  # 1-10
    reasoning: str
    risk_factors: list[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(slots=True)
class TradingSuggestion:
    """Final trading suggestion combining research and analysis."""

    event_id: str
    event_title: str
    market_id: str
    market_question: str
    current_odds: float
    estimated_probability: float
    edge: float
    recommendation: Recommendation
    confidence: int
    reasoning: str
    risk_factors: list[str]
    key_findings: list[str]
    sources: list[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "event_id": self.event_id,
            "event_title": self.event_title,
            "market_id": self.market_id,
            "market_question": self.market_question,
            "current_odds": self.current_odds,
            "estimated_probability": self.estimated_probability,
            "edge_percentage": round(self.edge * 100, 2),
            "recommendation": self.recommendation.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "risk_factors": self.risk_factors,
            "key_findings": self.key_findings,
            "sources": self.sources,
            "timestamp": self.timestamp,
        }
