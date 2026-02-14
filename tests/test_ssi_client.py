"""Unit tests for SSI iBoard API client."""

from unittest.mock import MagicMock, patch

import httpx
from financial_news.ssi_client import SSIClient, SSIIndexData, SSIStockData

# ---- Fixtures ----

SAMPLE_STOCK_ITEM = {
    "stockSymbol": "VNM",
    "companyNameEn": "Vinamilk",
    "exchange": "hose",
    "matchedPrice": 72500,
    "refPrice": 72000,
    "ceiling": 77100,
    "floor": 66900,
    "openPrice": 72200,
    "highest": 73000,
    "lowest": 71500,
    "avgPrice": 72300,
    "priceChange": 500,
    "priceChangePercent": 0.69,
    "nmTotalTradedQty": 1500000,
    "nmTotalTradedValue": 108750000000,
    "buyForeignQtty": 50000,
    "buyForeignValue": 3625000000,
    "sellForeignQtty": 30000,
    "sellForeignValue": 2175000000,
    "best1Bid": 72400,
    "best1BidVol": 5000,
    "best1Offer": 72600,
    "best1OfferVol": 3000,
}

SAMPLE_INDEX_RESPONSE = {
    "code": "SUCCESS",
    "message": "Call API successful",
    "data": {
        "indexId": "VN30",
        "indexValue": 2018.64,
        "prevIndexValue": 2016.47,
        "change": 2.17,
        "changePercent": 0.11,
        "advances": 19,
        "declines": 7,
        "nochanges": 4,
        "chartOpen": 2014.9,
        "chartHigh": 2022.65,
        "chartLow": 1997.23,
        "totalQtty": 259621089,
        "totalValue": 11165974633400,
        "totalBuyForeignQtty": 166334827,
        "totalSellForeignQtty": 146040843,
        "history": [
            {"indexValue": 2016.82, "time": 1770948905013, "vol": 2174177, "totalQtty": 2174177},
            {"indexValue": 2014.73, "time": 1770948970016, "vol": 42510, "totalQtty": 2781514},
        ],
    },
}


def _make_stock_response(items: list) -> dict:
    return {"code": "SUCCESS", "message": "ok", "data": items}


def _make_ssi_client_with_mock(mock_response: MagicMock) -> SSIClient:
    """Create an SSIClient with a mocked httpx.Client."""
    client = SSIClient.__new__(SSIClient)
    client.timeout = 30
    mock_http = MagicMock()
    mock_http.get.return_value = mock_response
    client._client = mock_http
    return client


def _make_ssi_client_with_error(error: Exception) -> SSIClient:
    """Create an SSIClient whose HTTP calls raise the given error."""
    client = SSIClient.__new__(SSIClient)
    client.timeout = 30
    mock_http = MagicMock()
    mock_http.get.side_effect = error
    client._client = mock_http
    return client


def _mock_response(json_data: dict) -> MagicMock:
    """Create a mock httpx response."""
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


# ---- SSIStockData Tests ----


class TestSSIStockData:
    """Tests for SSIStockData dataclass."""

    def test_foreign_net_qtty_positive(self):
        stock = SSIStockData(
            stock_symbol="VNM",
            company_name="Vinamilk",
            exchange="hose",
            matched_price=72500,
            ref_price=72000,
            ceiling=77100,
            floor=66900,
            open_price=72200,
            highest=73000,
            lowest=71500,
            avg_price=72300,
            price_change=500,
            price_change_percent=0.69,
            total_volume=1500000,
            total_value=108750000000,
            buy_foreign_qtty=50000,
            buy_foreign_value=3625000000,
            sell_foreign_qtty=30000,
            sell_foreign_value=2175000000,
        )
        assert stock.foreign_net_qtty == 20000
        assert stock.foreign_net_value == 1450000000

    def test_foreign_net_qtty_negative(self):
        stock = SSIStockData(
            stock_symbol="HPG",
            company_name="Hoaphat",
            exchange="hose",
            matched_price=30000,
            ref_price=30500,
            ceiling=32600,
            floor=28400,
            open_price=30500,
            highest=30500,
            lowest=29800,
            avg_price=30100,
            price_change=-500,
            price_change_percent=-1.64,
            total_volume=5000000,
            total_value=150500000000,
            buy_foreign_qtty=10000,
            buy_foreign_value=300000000,
            sell_foreign_qtty=80000,
            sell_foreign_value=2400000000,
        )
        assert stock.foreign_net_qtty == -70000
        assert stock.foreign_net_value == -2100000000


# ---- SSIIndexData Tests ----


class TestSSIIndexData:
    """Tests for SSIIndexData dataclass."""

    def test_foreign_net_qtty(self):
        idx = SSIIndexData(
            index_id="VN30",
            index_value=2018.64,
            prev_index_value=2016.47,
            change=2.17,
            change_percent=0.11,
            advances=19,
            declines=7,
            nochanges=4,
            chart_open=2014.9,
            chart_high=2022.65,
            chart_low=1997.23,
            total_qtty=259621089,
            total_value=11165974633400,
            total_buy_foreign_qtty=166334827,
            total_sell_foreign_qtty=146040843,
        )
        assert idx.foreign_net_qtty == 166334827 - 146040843


# ---- SSIClient Tests ----


class TestSSIClientGetVN30Stocks:
    """Tests for SSIClient.get_vn30_stocks()."""

    def test_success_returns_stock_list(self):
        """Should return list of SSIStockData on success."""
        resp = _mock_response(_make_stock_response([SAMPLE_STOCK_ITEM]))
        client = _make_ssi_client_with_mock(resp)

        stocks = client.get_vn30_stocks()

        assert len(stocks) == 1
        assert stocks[0].stock_symbol == "VNM"
        assert stocks[0].matched_price == 72500
        assert stocks[0].buy_foreign_qtty == 50000

    def test_network_error_returns_empty(self):
        """Should return empty list on network error."""
        client = _make_ssi_client_with_error(httpx.ConnectError("Connection refused"))

        stocks = client.get_vn30_stocks()

        assert stocks == []

    def test_malformed_stock_still_parses_with_defaults(self):
        """Items with missing fields parse with default values (0, empty str)."""
        bad_item = {"stockSymbol": "BAD"}
        good_item = SAMPLE_STOCK_ITEM.copy()

        resp = _mock_response(_make_stock_response([bad_item, good_item]))
        client = _make_ssi_client_with_mock(resp)

        stocks = client.get_vn30_stocks()

        # Both parse since .get() provides defaults
        assert len(stocks) == 2
        assert stocks[0].stock_symbol == "BAD"
        assert stocks[0].matched_price == 0

    def test_api_error_returns_empty(self):
        """Should return empty list when API returns error code."""
        resp = _mock_response({"code": "ERROR", "message": "Rate limited"})
        client = _make_ssi_client_with_mock(resp)

        stocks = client.get_vn30_stocks()

        assert stocks == []


class TestSSIClientGetVN30Index:
    """Tests for SSIClient.get_vn30_index()."""

    def test_success_returns_index_data(self):
        """Should return SSIIndexData on success."""
        resp = _mock_response(SAMPLE_INDEX_RESPONSE)
        client = _make_ssi_client_with_mock(resp)

        idx = client.get_vn30_index()

        assert idx is not None
        assert idx.index_value == 2018.64
        assert idx.change_percent == 0.11
        assert idx.advances == 19
        assert idx.declines == 7
        assert len(idx.history) == 2

    def test_timeout_returns_none(self):
        """Should return None on timeout."""
        client = _make_ssi_client_with_error(httpx.TimeoutException("Timeout"))

        idx = client.get_vn30_index()

        assert idx is None


class TestSSIClientGetMarketSummary:
    """Tests for SSIClient.get_market_summary()."""

    @patch.object(SSIClient, "get_vn30_index")
    @patch.object(SSIClient, "get_vn30_stocks")
    def test_aggregation_logic(self, mock_stocks, mock_index):
        """Should correctly aggregate stock and index data."""
        mock_index.return_value = SSIIndexData(
            index_id="VN30",
            index_value=2018.64,
            prev_index_value=2016.47,
            change=2.17,
            change_percent=0.11,
            advances=19,
            declines=7,
            nochanges=4,
            chart_open=2014.9,
            chart_high=2022.65,
            chart_low=1997.23,
            total_qtty=259621089,
            total_value=11165974633400,
            total_buy_foreign_qtty=166334827,
            total_sell_foreign_qtty=146040843,
        )

        mock_stocks.return_value = [
            SSIStockData(
                stock_symbol="VNM",
                company_name="Vinamilk",
                exchange="hose",
                matched_price=72500,
                ref_price=72000,
                ceiling=77100,
                floor=66900,
                open_price=72200,
                highest=73000,
                lowest=71500,
                avg_price=72300,
                price_change=500,
                price_change_percent=0.69,
                total_volume=1500000,
                total_value=108750000000,
                buy_foreign_qtty=50000,
                buy_foreign_value=3625000000,
                sell_foreign_qtty=30000,
                sell_foreign_value=2175000000,
            ),
            SSIStockData(
                stock_symbol="HPG",
                company_name="Hoaphat",
                exchange="hose",
                matched_price=30000,
                ref_price=30500,
                ceiling=32600,
                floor=28400,
                open_price=30500,
                highest=30500,
                lowest=29800,
                avg_price=30100,
                price_change=-500,
                price_change_percent=-1.64,
                total_volume=5000000,
                total_value=150500000000,
                buy_foreign_qtty=10000,
                buy_foreign_value=300000000,
                sell_foreign_qtty=80000,
                sell_foreign_value=2400000000,
            ),
        ]

        client = SSIClient.__new__(SSIClient)
        client.timeout = 30
        client._client = MagicMock()
        summary = client.get_market_summary()

        # Index data
        assert summary["index"]["value"] == 2018.64
        assert summary["index"]["advances"] == 19

        # Stocks
        assert len(summary["stocks"]) == 2

        # Foreign summary
        assert summary["foreign_summary"]["total_buy_value"] == 3625000000 + 300000000
        assert summary["foreign_summary"]["total_sell_value"] == 2175000000 + 2400000000

        # Top gainers (VNM +0.69%) should be first
        assert summary["top_gainers"][0]["symbol"] == "VNM"

        # Top losers (HPG -1.64%) should be last
        assert summary["top_losers"][-1]["symbol"] == "HPG"

        # Top foreign buy (VNM net +20000)
        assert len(summary["top_foreign_buy"]) == 1
        assert summary["top_foreign_buy"][0]["symbol"] == "VNM"

        # Top foreign sell (HPG net -70000)
        assert len(summary["top_foreign_sell"]) == 1
        assert summary["top_foreign_sell"][0]["symbol"] == "HPG"

    @patch.object(SSIClient, "get_vn30_index")
    @patch.object(SSIClient, "get_vn30_stocks")
    def test_empty_data_returns_structure(self, mock_stocks, mock_index):
        """Should return valid structure even when both endpoints fail."""
        mock_stocks.return_value = []
        mock_index.return_value = None

        client = SSIClient.__new__(SSIClient)
        client.timeout = 30
        client._client = MagicMock()
        summary = client.get_market_summary()

        assert summary["index"] is None
        assert summary["stocks"] == []
        assert summary["top_gainers"] == []
        assert summary["top_losers"] == []
        assert summary["foreign_summary"] == {}
