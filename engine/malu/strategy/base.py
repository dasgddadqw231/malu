from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from malu.exchange.models import PositionInfo, Side


class Signal(StrEnum):
    LONG = "long"
    SHORT = "short"
    CLOSE = "close"
    HOLD = "hold"


@dataclass
class JudgmentResult:
    signal: Signal
    confidence: float = 0.0
    reason: str = ""


@dataclass
class ActionResult:
    order_link_id: str = ""
    side: Side | None = None
    qty: Decimal = Decimal("0")
    executed: bool = False
    reason: str = ""


@dataclass
class DefenseResult:
    should_close: bool = False
    reason: str = ""


class JudgmentModule(ABC):
    """Evaluates market conditions and produces a trading signal."""

    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    async def evaluate(self, symbol: str, client: object, market_data: object | None = None) -> JudgmentResult:
        ...


class ActionModule(ABC):
    """Executes trades based on judgment signals."""

    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    async def execute(
        self,
        signal: Signal,
        symbol: str,
        available_budget: Decimal,
        client: object,
        rate_limiter: object,
        order_tagger: object,
    ) -> ActionResult:
        ...


class DefenseModule(ABC):
    """Monitors positions and triggers protective actions."""

    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    async def check(self, position: PositionInfo | None, client: object, market_data: object | None = None) -> DefenseResult:
        ...


@dataclass
class FilterResult:
    allowed: bool = True
    reason: str = ""


@dataclass
class SizingResult:
    trade_amount: Decimal = Decimal("0")
    reason: str = ""


class FilterModule(ABC):
    """Checks market conditions before entry."""

    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    async def check(self, symbol: str, signal: Signal, client: object, market_data: object | None = None) -> FilterResult:
        ...


class SizingModule(ABC):
    """Calculates position size."""

    def __init__(self, params: dict):
        self.params = params

    @abstractmethod
    async def calculate(self, symbol: str, available_budget: Decimal, signal: Signal, client: object, market_data: object | None = None) -> SizingResult:
        ...
