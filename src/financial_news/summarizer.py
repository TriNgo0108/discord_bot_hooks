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
Generate a daily briefing for Vietnamese retail investors based on market data and news.

## Analysis Framework (Think step-by-step)

### Step 1: Market Snapshot
Analyze VN30 index trend, gold prices (SJC vs world), USD/VND movement, and fund performance.

### Step 2: VN30 Stock Analysis  
Identify notable stocks from fund holdings. Note concentration patterns and sector rotation.

### Step 3: News Synthesis
Group news by theme (macro, sectors, company-specific). Identify bullish/bearish signals.

### Step 4: Investment Suggestions
Give 2-3 specific, actionable recommendations with price levels when possible. Include risk warnings.

---

## Example Output

**📊 Tổng Quan Thị Trường**
VN30 tăng nhẹ 0.3% lên 1,245 điểm trong phiên giao dịch hôm nay. Thanh khoản đạt 15,000 tỷ. Vàng SJC ổn định quanh 92tr/lượng, chênh lệch với giá thế giới thu hẹp. Tỷ giá USD/VND đi ngang ở 25,450.

**📈 Phân Tích VN30**
- FPT và VIC chiếm 25% danh mục các quỹ top → Dòng tiền tập trung công nghệ & BĐS
- HPG giảm tỷ trọng trong quỹ DCDS → Tín hiệu thận trọng với ngành thép
- VCB duy trì vị thế số 1 trong nhóm ngân hàng

**📰 Tin Nổi Bật**
- **Macro**: Fed giữ nguyên lãi suất → dòng vốn ngoại có thể quay lại EM
- **Ngân hàng**: BIDV công bố lãi Q4 vượt kỳ vọng 15%, NIM cải thiện
- **Bất động sản**: Luật Đất đai mới có hiệu lực tháng 1, kỳ vọng tháo gỡ pháp lý

**💡 Khuyến Nghị**
1. **Mua**: FPT (momentum tốt, quỹ ngoại mua ròng, target 145k)
2. **Theo dõi**: VCB (chờ điều chỉnh về vùng hỗ trợ 88k để tích lũy)
3. **Rủi ro lưu ý**: Tỷ giá có thể gây áp lực nếu Fed hawkish trở lại

---

## Self-Verification Checklist
Before responding, verify:
- [ ] All numbers come from provided data (do not fabricate)
- [ ] Recommendations mention specific stock codes
- [ ] At least one risk warning is included
- [ ] Output is 100% Vietnamese

## Output Requirements
- **Language**: Vietnamese (Tiếng Việt)
- **Format**: Clear Markdown with emoji headers (📊📈📰💡)
- **Length**: 300-500 words
- **Tone**: Professional but accessible to retail investors

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
        self.max_retries = 2

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

        # Gold Prices
        if "gold_prices" in market_stats and market_stats["gold_prices"]:
            g = market_stats["gold_prices"]
            parts.append(
                f"Gold: SJC {g.get('sjc_buy')}/{g.get('sjc_sell')}, "
                f"Ring {g.get('ring_buy')}/{g.get('ring_sell')}, "
                f"World: {g.get('world_gold')}, USD/VND: {g.get('usd_vnd')}"
            )

        # Top Funds
        if "top_funds" in market_stats:
            funds = market_stats["top_funds"]
            fund_lines = []
            for f in funds[:5]:
                line = (
                    f"- {f['name']}: 6M {f.get('nav_6m', 0):.1f}%, 12M {f.get('nav_12m', 0):.1f}%"
                )
                if "top_holdings" in f and f["top_holdings"]:
                    top_3 = [h["stock_code"] for h in f["top_holdings"][:3]]
                    line += f" | Holdings: {', '.join(top_3)}"
                fund_lines.append(line)
            if fund_lines:
                parts.append("Top Funds:\n" + "\n".join(fund_lines))

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
