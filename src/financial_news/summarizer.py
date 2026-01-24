import logging
import os
from typing import Any

from google import genai

logger = logging.getLogger(__name__)


class NewsSummarizer:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.model_name = "gemini-3-flash-preview"

    def summarize(
        self, news_items: list[dict[str, Any]], market_stats: dict[str, Any] = None
    ) -> str:
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. Skipping summarization.")
            return ""

        if not news_items:
            return ""

        market_stats = market_stats or {}

        # Prepare the input text for the LLM
        news_text = ""
        for i, item in enumerate(news_items, 1):
            news_text += f"{i}. [{item['source']}] {item['title']}: {item['summary']}\n"

        # Format Market Data
        funds_text = ""
        if "top_funds" in market_stats:
            funds = market_stats["top_funds"]
            fund_lines = []
            for f in funds:
                fund_line = f"- {f['name']} ({f.get('type', 'N/A')}): 6M {f.get('nav_6m', 0):.1f}%, 1Y {f.get('nav_12m', 0):.1f}%"
                # Add top holdings if available
                if "top_holdings" in f and f["top_holdings"]:
                    top_3 = f["top_holdings"][:3]
                    holdings_str = ", ".join(
                        [f"{h['stock_code']} ({h.get('portfolio_weight', 0):.1f}%)" for h in top_3]
                    )
                    fund_line += f" | Top: {holdings_str}"
                fund_lines.append(fund_line)
            funds_text = "\nTop Funds:\n" + "\n".join(fund_lines)

        gold_text = ""
        if "gold_prices" in market_stats and market_stats["gold_prices"]:
            g = market_stats["gold_prices"]
            gold_text = f"\nGold/Rates:\n- SJC Buy/Sell: {g.get('sjc_buy')}/{g.get('sjc_sell')}\n- Ring Buy/Sell: {g.get('ring_buy')}/{g.get('ring_sell')}\n- World Gold: {g.get('world_gold')}\n- USD/VND: {g.get('usd_vnd')}"

        rates_text = ""
        if "bank_rates" in market_stats:
            rates_text = "\nInterest Rates (12m):\n" + "\n".join(
                [f"- {r['bank']}: {r['rate_12m']}%" for r in market_stats["bank_rates"]]
            )

        prompt = (
            "You are a professional financial analyst for the Vietnamese market.\n"
            "Analyze the following financial news headlines and market data.\n"
            "Write a concise, professional daily financial briefing for a Vietnamese investor.\n"
            "The briefing must include:\n"
            "1. **Market Snapshot**: Brief comment on key market indicators (Gold, USD, Funds performance).\n"
            "2. **Key News**: Synthesize the most important news trends.\n"
            "3. **Investment Suggestions**: Give specific actionable advice based on the data (e.g., if gold is high, what to do? if specific fund types are performing well, suggest them? Savings vs Investment?).\n\n"
            "The output should be in Vietnamese (Tiếng Việt) and formatted as a clear Markdown summary.\n\n"
            f"--- Market Data ---\n{funds_text}\n{gold_text}\n{rates_text}\n\n"
            f"--- News ---\n{news_text}"
        )

        try:
            if not self.client:
                logger.warning("Client not initialized. Skipping.")
                return ""

            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            return response.text.strip()

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return ""
