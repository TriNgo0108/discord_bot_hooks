"""Selects topics for financial knowledge generation."""

import random

# Curated list of high-value financial topics for Vietnamese investors
FINANCIAL_TOPICS = [
    # Fundamental Concepts
    "P/E Ratio (Price-to-Earnings)",
    "P/B Ratio (Price-to-Book)",
    "ROE (Return on Equity)",
    "EPS (Earnings Per Share)",
    "Compound Interest (Lãi suất kép)",
    "Inflation (Lạm phát)",
    "GDP vs GNP",
    # Investment Strategies
    "DCA (Dollar-Cost Averaging - Trung bình giá)",
    "Value Investing (Đầu tư giá trị)",
    "Growth Investing (Đầu tư tăng trưởng)",
    "Dividend Investing (Đầu tư cổ tức)",
    "Asset Allocation (Phân bổ tài sản)",
    "Portfolio Rebalancing (Tái cân bằng danh mục)",
    # Funds & Instruments
    "ETF vs Mutual Fund (Quỹ mở vs Quỹ hoán đổi danh mục)",
    "Bonds (Trái phiếu) basics",
    "Stocks (Cổ phiếu) basics",
    "Derivatives (Phái sinh) basics",
    "REITs (Quỹ tín thác bất động sản)",
    # Risk Management
    "Diversification (Đa dạng hóa)",
    "Margin Trading (Giao dịch ký quỹ) risks",
    "Stop Loss & Take Profit",
    "Risk/Reward Ratio",
    "Psychology of Investing (Tâm lý đầu tư)",
    # Market Mechanics
    "Market Cycles (Chu kỳ thị trường)",
    "Bull vs Bear Market",
    "IPO (Initial Public Offering)",
    "Dividends (Cổ tức tiền mặt vs Cổ phiếu)",
    # Advanced
    "Technical Analysis vs Fundamental Analysis",
    "MACD Indicator",
    "RSI Indicator",
    "Moving Averages (MA, EMA)",
    "Candlestick Patterns (Mô hình nến)",
]


class TopicSelector:
    """Selects a topic for the knowledge drop."""

    def get_random_topic(self) -> str:
        """Return a random topic from the curated list."""
        return random.choice(FINANCIAL_TOPICS)
