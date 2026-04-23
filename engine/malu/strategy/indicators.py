"""Shared technical indicator calculations.

All functions are pure: they take price/volume data and return computed values.
No I/O, no API calls. Used by judgment, defense, filter, and sizing modules.
"""

from __future__ import annotations

from decimal import Decimal


def calc_sma(values: list[Decimal], period: int) -> Decimal:
    """Simple Moving Average of the last `period` values."""
    if len(values) < period:
        return Decimal("0")
    window = values[-period:]
    return sum(window) / period


def calc_ema(values: list[Decimal], period: int) -> list[Decimal]:
    """Exponential Moving Average over the full series.

    Returns a list the same length as input. Early values (before enough data)
    are seeded with SMA.
    """
    if len(values) < period:
        return [Decimal("0")] * len(values)

    multiplier = Decimal("2") / (Decimal(str(period)) + Decimal("1"))

    # Seed with SMA of first `period` values
    sma = sum(values[:period]) / period
    result: list[Decimal] = [Decimal("0")] * (period - 1) + [sma]

    for i in range(period, len(values)):
        ema_val = (values[i] - result[-1]) * multiplier + result[-1]
        result.append(ema_val)

    return result


def calc_rsi(closes: list[Decimal], period: int = 14) -> float:
    """RSI using Wilder's smoothed method. Returns current RSI value."""
    if len(closes) < period + 1:
        return 50.0

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Initial averages
    gains = [max(d, Decimal("0")) for d in deltas[:period]]
    losses = [abs(min(d, Decimal("0"))) for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Wilder's smoothing for remaining deltas
    for d in deltas[period:]:
        gain = max(d, Decimal("0"))
        loss = abs(min(d, Decimal("0")))
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = float(avg_gain / avg_loss)
    return 100.0 - (100.0 / (1.0 + rs))


def calc_bb(
    closes: list[Decimal], period: int = 20, num_std: float = 2.0
) -> tuple[Decimal, Decimal, Decimal]:
    """Bollinger Bands. Returns (upper, middle, lower)."""
    if len(closes) < period:
        mid = closes[-1] if closes else Decimal("0")
        return mid, mid, mid

    window = closes[-period:]
    middle = sum(window) / period
    variance = sum((x - middle) ** 2 for x in window) / period
    std = variance ** Decimal("0.5")
    ns = Decimal(str(num_std))
    return middle + ns * std, middle, middle - ns * std


def calc_bb_width(closes: list[Decimal], period: int = 20, num_std: float = 2.0) -> Decimal:
    """Bollinger BandWidth = (Upper - Lower) / Middle."""
    upper, middle, lower = calc_bb(closes, period, num_std)
    if middle == 0:
        return Decimal("0")
    return (upper - lower) / middle


def calc_macd(
    closes: list[Decimal],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> tuple[Decimal, Decimal, Decimal]:
    """MACD. Returns (macd_line, signal_line, histogram)."""
    if len(closes) < slow + signal_period:
        return Decimal("0"), Decimal("0"), Decimal("0")

    fast_ema = calc_ema(closes, fast)
    slow_ema = calc_ema(closes, slow)

    # MACD line = fast EMA - slow EMA
    macd_series = [f - s for f, s in zip(fast_ema, slow_ema)]

    # Signal line = EMA of MACD line (use only valid portion)
    valid_macd = macd_series[slow - 1:]  # from where slow EMA is valid
    signal_ema = calc_ema(valid_macd, signal_period)

    if not signal_ema or signal_ema[-1] == 0 and not valid_macd:
        return Decimal("0"), Decimal("0"), Decimal("0")

    macd_val = valid_macd[-1] if valid_macd else Decimal("0")
    signal_val = signal_ema[-1] if signal_ema else Decimal("0")
    histogram = macd_val - signal_val

    return macd_val, signal_val, histogram


def calc_atr(
    highs: list[Decimal], lows: list[Decimal], closes: list[Decimal], period: int = 14
) -> Decimal:
    """Average True Range."""
    if len(closes) < 2 or len(highs) < period or len(lows) < period:
        return Decimal("0")

    true_ranges: list[Decimal] = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges) if true_ranges else Decimal("0")

    # Wilder's smoothing
    atr = sum(true_ranges[:period]) / period
    for tr in true_ranges[period:]:
        atr = (atr * (period - 1) + tr) / period

    return atr


def calc_adx(
    highs: list[Decimal], lows: list[Decimal], closes: list[Decimal], period: int = 14
) -> float:
    """Average Directional Index. Returns current ADX value."""
    if len(closes) < period * 2 or len(highs) < period * 2:
        return 0.0

    plus_dm_list: list[Decimal] = []
    minus_dm_list: list[Decimal] = []
    tr_list: list[Decimal] = []

    for i in range(1, len(closes)):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]

        plus_dm = up_move if (up_move > down_move and up_move > 0) else Decimal("0")
        minus_dm = down_move if (down_move > up_move and down_move > 0) else Decimal("0")
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)

        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        tr_list.append(tr)

    if len(tr_list) < period:
        return 0.0

    # Wilder's smoothed averages
    atr = sum(tr_list[:period]) / period
    plus_di_smooth = sum(plus_dm_list[:period]) / period
    minus_di_smooth = sum(minus_dm_list[:period]) / period

    dx_list: list[float] = []

    for i in range(period, len(tr_list)):
        atr = (atr * (period - 1) + tr_list[i]) / period
        plus_di_smooth = (plus_di_smooth * (period - 1) + plus_dm_list[i]) / period
        minus_di_smooth = (minus_di_smooth * (period - 1) + minus_dm_list[i]) / period

        if atr == 0:
            continue

        plus_di = float(plus_di_smooth / atr) * 100
        minus_di = float(minus_di_smooth / atr) * 100

        di_sum = plus_di + minus_di
        if di_sum == 0:
            dx_list.append(0.0)
        else:
            dx_list.append(abs(plus_di - minus_di) / di_sum * 100)

    if len(dx_list) < period:
        return sum(dx_list) / len(dx_list) if dx_list else 0.0

    # ADX = smoothed average of DX
    adx = sum(dx_list[:period]) / period
    for dx in dx_list[period:]:
        adx = (adx * (period - 1) + dx) / period

    return adx


def calc_obv(closes: list[Decimal], volumes: list[Decimal]) -> list[Decimal]:
    """On-Balance Volume. Returns OBV series."""
    if not closes or not volumes or len(closes) != len(volumes):
        return []

    obv = [volumes[0]]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    return obv


# Type alias for return values (avoid circular import with Signal enum)
Signal_str = str  # "long", "short", "hold"


def find_swing_highs(
    highs: list[Decimal], left_bars: int = 5, right_bars: int = 2
) -> list[tuple[int, Decimal]]:
    """Find swing high points (local maxima).

    A swing high at index i requires:
      highs[i] >= all highs in [i-left_bars, i+right_bars]

    Returns list of (index, price) sorted by index.
    """
    results: list[tuple[int, Decimal]] = []
    for i in range(left_bars, len(highs) - right_bars):
        is_swing = True
        for j in range(i - left_bars, i + right_bars + 1):
            if j == i:
                continue
            if highs[j] > highs[i]:
                is_swing = False
                break
        if is_swing:
            results.append((i, highs[i]))
    return results


def find_swing_lows(
    lows: list[Decimal], left_bars: int = 5, right_bars: int = 2
) -> list[tuple[int, Decimal]]:
    """Find swing low points (local minima).

    A swing low at index i requires:
      lows[i] <= all lows in [i-left_bars, i+right_bars]

    Returns list of (index, price) sorted by index.
    """
    results: list[tuple[int, Decimal]] = []
    for i in range(left_bars, len(lows) - right_bars):
        is_swing = True
        for j in range(i - left_bars, i + right_bars + 1):
            if j == i:
                continue
            if lows[j] < lows[i]:
                is_swing = False
                break
        if is_swing:
            results.append((i, lows[i]))
    return results


def detect_ema_cross(
    closes: list[Decimal], fast_period: int, slow_period: int
) -> tuple[Signal_str, bool]:
    """Detect EMA crossover. Returns (direction, just_crossed).

    direction: "long" if fast > slow, "short" if fast < slow, "hold" otherwise
    just_crossed: True if the cross happened on the latest bar
    """
    if len(closes) < slow_period + 2:
        return "hold", False

    fast_ema = calc_ema(closes, fast_period)
    slow_ema = calc_ema(closes, slow_period)

    curr_diff = fast_ema[-1] - slow_ema[-1]
    prev_diff = fast_ema[-2] - slow_ema[-2]

    if curr_diff > 0 and prev_diff <= 0:
        return "long", True
    elif curr_diff < 0 and prev_diff >= 0:
        return "short", True
    elif curr_diff > 0:
        return "long", False
    elif curr_diff < 0:
        return "short", False
    return "hold", False
