"""Data models for derivatives market data."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass
class OptionsContract:
    """Standardized options contract model."""

    symbol: str
    strike: float
    expiry: datetime
    contract_type: Literal["CALL", "PUT"]
    bid: float
    ask: float
    last_price: float
    volume: int
    open_interest: int
    implied_volatility: float | None = None
    greeks: dict[str, float] = field(default_factory=dict)  # delta, gamma, theta, vega
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FuturesContract:
    """Standardized futures/perpetual contract model."""

    symbol: str  # e.g., "BTCUSDT"
    underlying: str  # e.g., "BTC"
    last_price: float
    open_interest: float  # In base asset or USD depending on source
    volume_24h: float
    expiry: datetime | None = None  # None for perpetuals
    mark_price: float | None = None
    funding_rate: float | None = None  # For perpetuals
    liquidation_24h: float | None = None
    source: str = "unknown"
    data_date: datetime | None = None
    is_stale: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MarketStructure:
    """Market structure data (COT, etc)."""

    instrument: str
    report_date: datetime
    # Commitment of Traders data
    non_commercial_long: int = 0
    non_commercial_short: int = 0
    commercial_long: int = 0
    commercial_short: int = 0
    net_position: int = 0  # Non-commercial net
    open_interest: int = 0
    source: str = "cftc"


@dataclass
class TradingRecommendation:
    """Actionable trading recommendation."""

    instrument: str
    direction: Literal["LONG", "SHORT", "NEUTRAL", "AVOID"]
    confidence: int  # 1-10
    timeframe: str  # e.g., "1 week", "intraday"
    reasoning: str
    key_levels: dict[str, float] = field(default_factory=dict)  # support, resistance, stop_loss
    risk_factors: list[str] = field(default_factory=list)


@dataclass
class DerivativesAnalysis:
    """Final analysis result."""

    timestamp: datetime
    market_data: dict[str, Any]  # Raw summaries of fetched data
    key_findings: list[str]
    market_sentiment: Literal["BULLISH", "BEARISH", "NEUTRAL", "MIXED"]
    notable_flows: list[str]
    risk_factors: list[str]
    recommendations: list[TradingRecommendation]
    sources: list[str]

    def to_discord_embed(self) -> dict[str, Any]:
        """Convert to Discord embed format."""
        color_map = {
            "BULLISH": 0x00FF00,  # Green
            "BEARISH": 0xFF0000,  # Red
            "NEUTRAL": 0x808080,  # Gray
            "MIXED": 0xFFA500,  # Orange
        }

        fields = []

        # Recommendations
        rec_text = ""
        for rec in self.recommendations[:3]:  # Top 3
            rec_text += f"**{rec.instrument}**: {rec.direction} ({rec.confidence}/10)\n"
            rec_text += f"_{rec.reasoning[:100]}..._\n\n"

        if rec_text:
            fields.append({"name": "🚀 Top Recommendations", "value": rec_text, "inline": False})

        # Key Findings
        findings_text = "\n".join([f"• {f}" for f in self.key_findings[:5]])
        if findings_text:
            fields.append({"name": "🔍 Key Findings", "value": findings_text, "inline": False})

        # Flows
        flows_text = "\n".join([f"• {f}" for f in self.notable_flows[:3]])
        if flows_text:
            fields.append({"name": "🌊 Notable Flows", "value": flows_text, "inline": False})

        # Check for stale data in market_data
        stale_warning = ""
        data_date_str = ""

        # We need to peek into the market data structure to find dates
        # "market_structure" list contains the contract dicts
        futures_data = self.market_data.get("market_structure", [])
        for item in futures_data:
            if isinstance(item, dict):
                if item.get("is_stale"):
                    stale_warning = "⚠️ **WARNING: DATA MAY BE STALE** ⚠️"

                d_date = item.get("data_date")
                if d_date:
                    data_date_str = f"Data Date: {d_date}"
                    if item.get("is_stale"):
                        data_date_str += " (OLD)"
                    # Just grab the first one for the footer
                    break

        description = f"Analysis generated at {self.timestamp.strftime('%Y-%m-%d %H:%M UTC')}"
        if stale_warning:
            description = f"{stale_warning}\n{description}"

        footer_text = "Powered by Perplexity & GLM-4.7"
        if data_date_str:
            footer_text += f" | {data_date_str}"

        return {
            "title": f"Derivatives Market Analysis ({self.market_sentiment})",
            "description": description,
            "color": color_map.get(self.market_sentiment, 0x808080),
            "fields": fields,
            "footer": {"text": footer_text},
        }
