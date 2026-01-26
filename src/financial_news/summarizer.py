import datetime
import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# =============================================================================
# OPTIMIZED PROMPT (Using prompt-engineering-patterns skill)
# =============================================================================

FINANCIAL_ANALYSIS_PROMPT = """You are a senior Vietnamese financial analyst at a top securities firm.

## Your Task
Generate a daily briefing for Vietnamese retail investors based on market data (Funds, Stocks, Gold, Derivatives) and news.

## Analysis Framework (Think step-by-step)

### Step 1: Market Snapshot & Trends (12-Month focus)
- **Funds**: Analyze top funds based on *12-month return*. Identify which sectors (Tech, Bank, etc.) are leading over the long term.
- **Gold**: Analyze the 1-year price trend. Is the current price high or low relative to the 12-month range? Check the SJC vs World spread.
- **Derivatives**: Check VN30F1M trend and basis (Futures - Index). Positive basis = bullish, Negative = bearish.

### Step 2: News Integration
Group news by theme (Macro, Corporate, Policy). Identify potential catalysts for the next week.

### Step 3: Strategic Suggestions (CRITICAL)
Provide specific, actionable advice for 4 categories:
1.  **Funds**: Suggest *specific* funds to buy/hold based on 12M performance. (e.g., "Buy DCDS for growth").
2.  **Gold**: Action (Buy/Sell/Hold) based on spread and trend.
3.  **Stocks**: Pick 1-2 VN30 stocks to watch based on news or flow.
4.  **Derivatives**: Suggest Long/Short bias based on basis and trend.

---

## Example Output

**📊 Bức Tranh Thị Trường (12 Tháng)**
- **Quỹ**: DCDS và FUEVFVND dẫn đầu với hiệu suất 12T > 15%, cho thấy xu hướng tích dòng vốn vào nhóm vốn hóa lớn.
- **Vàng**: Đang ở vùng đỉnh 12 tháng. Spread SJC/World thu hẹp còn 2tr (thấp nhất năm) -> Cơ hội tích lũy.
- **Phái sinh**: Basis dương 5 điểm -> Tâm lý trớn tăng tốt.

**📰 Tin Tức & Động Lực**
- Fed hạ lãi suất -> Tích cực cho chứng khoán cận biên.
- FPT ra mắt chip mới -> Động lực cho nhóm công nghệ.

**💡 Khuyến Nghị Đầu Tư**
1.  **Chuyển đổi Quỹ**: Tăng tỷ trọng quỹ cổ phiếu (DCDS, VESAF) do kỳ vọng hồi phục kinh tế 2025.
2.  **Vàng**: **MUA TÍCH SẢN** (Nhẫn trơn). Spread thấp là lợi thế an toàn.
3.  **Cổ phiếu**: Canh mua HPG vùng 28.x (Hưởng lợi đầu tư công).
4.  **Phái sinh**: **LONG** khi VN30F1M test lại hỗ trợ 1240.

---

## Check & Verify
- [ ] Did I mention 12-month fund performance?
- [ ] Is there a specific Derivative suggestion?
- [ ] Is the Gold suggestion based on the spread?

## Output Requirements
- Language: Vietnamese
- Tone: Professional, insightful, actionable.
- Format: Markdown with emojis.

---

## Market Data
{market_data}

---

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

        # Call GLM-4.7 with retry
        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a senior Vietnamese financial analyst. Follow the analysis framework exactly and output in Vietnamese.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()

            except Exception as e:
                logger.warning(f"GLM-4.7 attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(2)
                continue

        logger.error("All GLM-4.7 attempts failed. Using fallback summary.")
        return self._generate_fallback_summary(news_items, market_stats)

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
                    [f"{l['symbol']} ({l['change_percent']:+.2f}%)" for l in losers]
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
                # History items have keys: reportDate (ms timestamp), askSjc, bidSjc
                # Sort by date
                history.sort(key=lambda x: x.get("reportDate", 0))

                # Helper to format date and price
                def fmt_item(item):
                    ts = item.get("reportDate", 0)
                    date_str = "N/A"
                    if ts:
                        # timestamp in ms
                        dt = datetime.datetime.fromtimestamp(ts / 1000)
                        date_str = dt.strftime("%Y-%m-%d")

                    price = item.get("askSjc")
                    price_str = f"{price:,.0f}" if price else "N/A"
                    return f"{date_str}: {price_str}"

                start = history[0]
                end = history[-1]

                # Find min/max in history
                prices = [x.get("askSjc", 0) for x in history if x.get("askSjc")]
                min_p = min(prices) if prices else 0
                max_p = max(prices) if prices else 0

                parts.append(
                    f"Gold 12-Month Trend (SJC Sell): Start {fmt_item(start)} -> End {fmt_item(end)}"
                )
                parts.append(f"12-Month Range: Low {min_p:,.0f} - High {max_p:,.0f}")

        # Derivatives Data
        if "derivatives" in market_stats and market_stats["derivatives"]:
            deriv = market_stats["derivatives"]
            futures = deriv.get("futures", [])
            for f in futures[:1]:  # Top 1 usually VN30F1M
                parts.append(
                    f"Derivatives: {f.get('symbol')} Price {f.get('price')} (Change {f.get('changePercent')}%) - Basis: {f.get('basis', 'N/A')}"
                )

            # Market Structure (Foreign flow etc if available)
            if "market_structure" in deriv:
                parts.append(
                    f"Derivatives Market Structure: {str(deriv['market_structure'])[:200]}..."
                )

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
