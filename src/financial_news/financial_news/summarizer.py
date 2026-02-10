import logging
import os
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

logger = logging.getLogger(__name__)

# =============================================================================
# OPTIMIZED PROMPT (Using prompt-engineering-patterns skill)
# =============================================================================

FINANCIAL_ANALYSIS_PROMPT = """
# CONTEXT
You are a senior financial analyst at a top-tier securities firm in Vietnam. You specialize in synthesizing complex market data into actionable insights for retail investors.

# OBJECTIVE
Generate a high-value "Daily Financial Briefing" (Bản tin Tài chính) for Vietnamese retail investors. Synthesize the provided market data and news.

# CRITICAL CONSTRAINTS
-   **LANGUAGE**: ALL output must be in **Vietnamese** (Tiếng Việt). Do not use English headers or phrases.
-   **NO HALLUCINATIONS**: Do not invent data. If data is missing (e.g., no gold price), skip that section.

# RESPONSE FORMAT
Use GitHub-flavored Markdown. Structure:

1.  **📊 Bức Tranh 12 Tháng & Xu Hướng**: Focus on Funds and Gold 12-month performance.
2.  **📰 Điểm Tin & Tác Động**: Top news and its specific impact.
3.  **💡 Khuyến Nghị Hành Động**: Specific advice for:
    -   *Quỹ (Funds)*: Buy/Hold/Sell advice based on returns.
    -   *Cổ phiếu (Stocks)*: Key tickers to watch.
    -   *Vàng (Gold)*: Accumulate or Wait.

# CHAIN OF THOUGHT & VERIFICATION (Internal Monologue)
Before generating the final response, perform this checklist:
1.  [ ] **Language Check**: Is every word in Vietnamese? (Translate concepts like "Buy", "Hold" to "Mua", "Nắm giữ").
2.  [ ] **Data Check**: Did I cite specific numbers from the Input Data?
3.  [ ] **Actionable Check**: Did I give at least one specific ticker or fund name to recommendation?
4.  [ ] **Tone Check**: Is it professional yet decisive?
5.  [ ] **Structure Check**: Did I follow the structure of the response?
6.  [ ] **No Hallucination Check**: Did I invent data? If data is missing, skip that section.
7.  [ ] **No English Check**: Did I use any English or chinese words? If so, translate them to Vietnamese.
8.  [ ] **Did I follow Discord markdown formatting?**: Is the response formatted correctly for Discord?

*Instructions: Perform the analysis steps, verify against the checklist, and then output ONLY the final Vietnamese response.*

# INPUT DATA
## Market Data
{market_data}

## News Headlines
{news_headlines}
"""


class NewsSummarizer:
    """Summarizes financial news using Z.AI GLM-4.7 with optimized prompts."""

    def __init__(self):
        self.api_key = os.getenv("ZAI_API_KEY")
        self.model_name = "glm-4.7"
        self.base_url = "https://api.z.ai/api/coding/paas/v4"
        self.max_retries = 5

    @retry(
        stop=stop_after_attempt(10),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _call_zai_api(self, messages: list[dict[str, str]]) -> str:
        """Call Z.AI API with tenacity retry logic."""
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.3,
            },
            timeout=180.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    def summarize(
        self, news_items: list[dict[str, Any]], market_stats: dict[str, Any] = None
    ) -> str:
        if not self.api_key:
            logger.warning("ZAI_API_KEY not found. Using fallback summary.")
            return self._generate_fallback_summary(news_items, market_stats)

        if not news_items:
            return ""

        market_stats = market_stats or {}

        # Prepare news text
        news_text = ""
        for i, item in enumerate(news_items, 1):
            news_text += f"{i}. [{item['source']}] {item['title']}: {item['summary'][:200]}\n"

        # Format Market Data
        market_data = self._format_all_market_data(market_stats)

        # Build prompt from template
        prompt = FINANCIAL_ANALYSIS_PROMPT.format(
            market_data=market_data,
            news_headlines=news_text,
        )

        messages = [
            {
                "role": "system",
                "content": "You are a specialized financial analysis AI. Follow the provided CO-STAR framework and instructions exactly.",
            },
            {"role": "user", "content": prompt},
        ]

        return self._call_zai_api(messages)

    def _format_all_market_data(self, market_stats: dict[str, Any]) -> str:
        """Format all market data into a single string for the prompt."""
        parts = []

        # VN30 Current Index (Real-time)
        if "vn30_current" in market_stats and market_stats["vn30_current"]:
            vn30 = market_stats["vn30_current"]
            parts.append(
                f"VN30 Index: {vn30.get('current', 0):,.2f} ({vn30.get('change_percent', 0):+.2f}%), Volume: {vn30.get('volume', 0):,}"
            )
        # Fallback to historical data if current not available
        elif "vn30_index" in market_stats and market_stats["vn30_index"]:
            vn30_data = market_stats["vn30_index"]
            if len(vn30_data) >= 2:
                latest = vn30_data[-1]
                prev = vn30_data[-2]
                change = latest["close"] - prev["close"]
                change_pct = (change / prev["close"]) * 100 if prev["close"] > 0 else 0
                parts.append(
                    f"VN30 Index: {latest['close']:,.2f} ({change_pct:+.2f}%), Volume: {latest['volume']:,}"
                )

        # Top Movers
        if "top_movers" in market_stats and market_stats["top_movers"]:
            movers = market_stats["top_movers"]
            gainers = movers.get("gainers", [])[:3]
            losers = movers.get("losers", [])[:3]

            if gainers:
                gainer_str = ", ".join(
                    [f"{g['symbol']} ({g['change_percent']:+.2f}%)" for g in gainers]
                )
                parts.append(f"Top Gainers: {gainer_str}")

            if losers:
                loser_str = ", ".join(
                    [f"{loser['symbol']} ({loser['change_percent']:+.2f}%)" for loser in losers]
                )
                parts.append(f"Top Losers: {loser_str}")

        # Gold Prices & History
        if "gold_prices" in market_stats and market_stats["gold_prices"]:
            g = market_stats["gold_prices"]
            parts.append(
                f"Market Gold Rates (Latest): SJC {g.get('sjc_buy')}/{g.get('sjc_sell')}, "
                f"Ring {g.get('ring_buy')}/{g.get('ring_sell')}, "
                f"World: {g.get('world_gold')}, USD/VND: {g.get('usd_vnd')}"
            )

            # Format History Logic
            history = g.get("history", [])
            if history:
                # History items have keys: date (YYYY-MM-DD), sjc_buy, sjc_sell
                # Sort by date
                history.sort(key=lambda x: x.get("date", ""))

                # Helper to format date and price
                def fmt_item(item):
                    date_str = item.get("date", "N/A")
                    price = item.get("sjc_sell")
                    price_str = f"{price:,.0f}" if price else "N/A"
                    return f"{date_str}: {price_str}"

                start = history[0]
                end = history[-1]

                # Find min/max in history
                prices = [x.get("sjc_sell", 0) for x in history if x.get("sjc_sell")]
                min_p = min(prices) if prices else 0
                max_p = max(prices) if prices else 0

                parts.append(
                    f"Gold 12-Month Trend (SJC Sell): Start {fmt_item(start)} -> End {fmt_item(end)}"
                )
                parts.append(f"12-Month Range: Low {min_p:,.0f} - High {max_p:,.0f}")

        # Watchlist Funds
        if "watchlist_funds" in market_stats and market_stats["watchlist_funds"]:
            funds = market_stats["watchlist_funds"]
            fund_lines = []
            for f in funds:
                line = (
                    f"- {f['name']}: 6M {f.get('nav_6m', 0):.1f}%, 12M {f.get('nav_12m', 0):.1f}%"
                )
                if "top_holdings" in f and f["top_holdings"]:
                    top_3 = [h["stock_code"] for h in f["top_holdings"][:3]]
                    line += f" | Holdings: {', '.join(top_3)}"
                fund_lines.append(line)
            if fund_lines:
                parts.append("Watchlist Funds:\n" + "\n".join(fund_lines))

        # Top Funds

        if "top_funds" in market_stats:
            funds = market_stats["top_funds"]
            fund_lines = []
            for f in funds[:5]:
                # Avoid duplicates if in watchlist
                if "watchlist_funds" in market_stats and any(
                    w["id"] == f["id"] for w in market_stats["watchlist_funds"]
                ):
                    continue

                line = (
                    f"- {f['name']}: 6M {f.get('nav_6m', 0):.1f}%, 12M {f.get('nav_12m', 0):.1f}%"
                )
                if "top_holdings" in f and f["top_holdings"]:
                    top_3 = [h["stock_code"] for h in f["top_holdings"][:3]]
                    line += f" | Holdings: {', '.join(top_3)}"
                fund_lines.append(line)
            if fund_lines:
                parts.append("Top Performing Funds:\n" + "\n".join(fund_lines))

        # Bank Rates
        if "bank_rates" in market_stats and market_stats["bank_rates"]:
            rates = [f"{r['bank']}: {r['rate_12m']}%" for r in market_stats["bank_rates"][:3]]
            parts.append(f"Interest Rates (12m): {', '.join(rates)}")

        # VN30 Symbols
        if "vn30_symbols" in market_stats and market_stats["vn30_symbols"]:
            symbols = market_stats["vn30_symbols"][:10]
            parts.append(f"VN30 Components: {', '.join(symbols)}")

        # Perplexity AI Context (Web Research)
        if "perplexity_context" in market_stats and market_stats["perplexity_context"]:
            ctx = market_stats["perplexity_context"]
            context_parts = []

            if ctx.get("vn30_context"):
                context_parts.append(f"**VN30 Analysis (AI):**\n{ctx['vn30_context']}")

            if ctx.get("stocks_context"):
                context_parts.append(f"**Top Stocks Analysis (AI):**\n{ctx['stocks_context']}")

            if ctx.get("funds_context"):
                context_parts.append(f"**Fund Analysis (AI):**\n{ctx['funds_context']}")

            if context_parts:
                parts.append("\n---\n**Web Research Context:**\n" + "\n\n".join(context_parts))

        # Political/Policy News Context
        if "political_context" in market_stats and market_stats["political_context"]:
            parts.append(
                "\n---\n**Political & Policy News:**\n" + market_stats["political_context"]
            )

        return "\n\n".join(parts) if parts else "Market data unavailable"

    def _generate_fallback_summary(
        self, news_items: list[dict[str, Any]], market_stats: dict[str, Any] = None
    ) -> str:
        """Generate a simple fallback summary when AI is unavailable."""
        market_stats = market_stats or {}

        summary_parts = ["**📊 Daily Financial Briefing (Auto-Generated)**\n"]

        # Add gold/rates if available
        if "gold_prices" in market_stats and market_stats["gold_prices"]:
            g = market_stats["gold_prices"]
            summary_parts.append(
                f"**Vàng & Tỷ giá:**\n"
                f"- SJC Mua/Bán: {g.get('sjc_buy')}/{g.get('sjc_sell')}\n"
                f"- USD/VND: {g.get('usd_vnd')}\n"
            )

        # Add top news headlines
        if news_items:
            summary_parts.append("\n**Tin nổi bật:**\n")
            for item in news_items[:5]:
                summary_parts.append(f"• {item['title'][:100]}\n")

        summary_parts.append("\n*⚠️ AI summary unavailable - showing raw data*")

        return "".join(summary_parts)
