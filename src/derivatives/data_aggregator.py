import logging
from typing import Any

from .clients.vnstock_client import VNStockClient

logger = logging.getLogger(__name__)


class DataAggregator:
    """Aggregates data from multiple derivatives sources."""

    def __init__(self):
        self.vnstock = VNStockClient()

    async def fetch_all_market_data(self, instruments: list[str]) -> dict[str, Any]:
        """
        Fetch and aggregate all available data for instruments.
        """
        data_collection = {"market_structure": [], "options": []}

        # Parallel fetch if we had multiple sources, but now mainly vnstock
        # keeping structure for extensibility
        await self._fetch_market_structure(instruments, data_collection)

        return data_collection

    async def close(self):
        """Close all clients."""
        await self.vnstock.close()

    async def _fetch_market_structure(self, instruments: list[str], collection: dict):
        for inst in instruments:
            try:
                # Use VNStock to get latest price/structure
                data = await self.vnstock.get_market_snapshot(inst)
                if data:
                    collection["market_structure"].append(data)
            except Exception as e:
                logger.error(f"Error fetching structure for {inst}: {e}")

    async def _fetch_options(self, instruments: list[str], collection: dict):
        # VN30F options are not fully supported/liquid in same way, or not prioritized yet
        pass
