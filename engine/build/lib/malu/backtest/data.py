from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from malu.exchange.bybit_client import BybitClient
from malu.exchange.models import Category
from malu.utils.logger import get_logger

log = get_logger("backtest.data")


@dataclass
class HistoricalCandle:
    timestamp: int  # ms
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass
class FundingRecord:
    timestamp: int  # ms
    funding_rate: Decimal


class HistoricalDataFetcher:
    """Fetches and paginates historical OHLCV and funding rate data from Bybit."""

    def __init__(self, client: BybitClient):
        self.client = client

    async def fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
    ) -> list[HistoricalCandle]:
        """Fetch all kline candles for the given date range.

        Bybit returns max 200 candles per call, newest first.
        We paginate backward from end_ms.
        """
        all_candles: list[HistoricalCandle] = []
        cursor_end = end_ms

        while cursor_end > start_ms:
            raw = await self.client.get_kline(
                category=Category.LINEAR,
                symbol=symbol,
                interval=interval,
                limit=200,
                start=start_ms,
                end=cursor_end,
            )

            if not raw:
                break

            for c in raw:
                ts = int(c[0])
                if ts < start_ms:
                    continue
                all_candles.append(
                    HistoricalCandle(
                        timestamp=ts,
                        open=Decimal(c[1]),
                        high=Decimal(c[2]),
                        low=Decimal(c[3]),
                        close=Decimal(c[4]),
                        volume=Decimal(c[5]),
                    )
                )

            # Bybit returns newest-first; last item is the oldest in this batch
            oldest_ts = int(raw[-1][0])
            if oldest_ts >= cursor_end:
                break  # no progress
            cursor_end = oldest_ts - 1

        # Sort oldest-first
        all_candles.sort(key=lambda c: c.timestamp)

        # Deduplicate by timestamp
        seen: set[int] = set()
        unique: list[HistoricalCandle] = []
        for c in all_candles:
            if c.timestamp not in seen:
                seen.add(c.timestamp)
                unique.append(c)

        log.info("klines_fetched", symbol=symbol, count=len(unique))
        return unique

    async def fetch_funding_rates(
        self,
        symbol: str,
        start_ms: int,
        end_ms: int,
    ) -> list[FundingRecord]:
        """Fetch all historical funding rates for the given date range."""
        all_rates: list[FundingRecord] = []
        cursor_end = end_ms

        while cursor_end > start_ms:
            raw = await self.client.get_funding_rate_history(
                category=Category.LINEAR,
                symbol=symbol,
                limit=200,
                start_time=start_ms,
                end_time=cursor_end,
            )

            if not raw:
                break

            for r in raw:
                ts = int(r["fundingRateTimestamp"])
                if ts < start_ms:
                    continue
                all_rates.append(
                    FundingRecord(
                        timestamp=ts,
                        funding_rate=Decimal(r["fundingRate"]),
                    )
                )

            oldest_ts = int(raw[-1]["fundingRateTimestamp"])
            if oldest_ts >= cursor_end:
                break
            cursor_end = oldest_ts - 1

        all_rates.sort(key=lambda r: r.timestamp)

        # Deduplicate
        seen: set[int] = set()
        unique: list[FundingRecord] = []
        for r in all_rates:
            if r.timestamp not in seen:
                seen.add(r.timestamp)
                unique.append(r)

        log.info("funding_rates_fetched", symbol=symbol, count=len(unique))
        return unique
