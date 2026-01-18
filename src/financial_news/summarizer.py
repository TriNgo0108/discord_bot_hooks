import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class NewsSummarizer:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = "google/gemma-3-27b-it:free"
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def summarize(
        self, news_items: list[dict[str, Any]], market_stats: dict[str, Any] = None
    ) -> str:
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not found. Skipping summarization.")
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
            funds_text = "\nTop Funds:\n" + "\n".join(
                [
                    f"- {f['name']} ({f['type']}): 1Y {f['nav_12m']}%, YTD {f['nav_ytd']}%, 3Y {f['nav_3y']}%"
                    for f in funds
                ]
            )

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

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "top_p": 1,
            "temperature": 0.7,
            "repetition_penalty": 1,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(
                self.api_url, headers=headers, content=json.dumps(payload), timeout=60.0
            )
            response.raise_for_status()
            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"Unexpected API response: {data}")
                return ""

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return ""
