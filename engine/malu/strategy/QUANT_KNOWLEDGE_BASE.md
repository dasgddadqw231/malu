# Quant Trading Knowledge Base for Crypto Futures
# Target: Bybit USDT Linear Perpetual Contracts
# Last Updated: 2026-04-19

---

## 1. TECHNICAL INDICATORS & SIGNAL GENERATION

### 1.1 Bollinger Bands (BB)

**Parameters:**
- Period: 20 (standard), 10 (scalping), 50 (position)
- StdDev: 2.0 (standard), 1.5 (scalping/tight), 2.5 (wide filter)
- Source: Close price (default), HLC3 for smoothing

**Strategy A: Mean Reversion**
- Entry Long: Price closes below lower band + RSI < 30 + volume spike
- Entry Short: Price closes above upper band + RSI > 70 + volume spike
- Target: Middle band (20 SMA)
- Stop: 1.5x ATR beyond entry band
- Best in: Ranging/consolidation markets
- Win rate expectation: 55-65% with tight R:R of 1:1 to 1:1.5

**Strategy B: Breakout (Squeeze)**
- BandWidth formula: (Upper - Lower) / Middle
- Squeeze detection: BandWidth at 6-week low (daily) or 48-bar low (1H)
- Squeeze threshold: BandWidth < 0.04 for BTC, < 0.06 for altcoins
- Entry: Candle CLOSE (not wick) outside band after squeeze
- Volume confirmation: >= 1.5x 20-period average volume
- Stop: Middle band (20 SMA)
- Target: 2x band width projected from breakout point
- Best in: Post-consolidation, pre-news events

**Strategy C: Band Walk (Trend Continuation)**
- Price consistently closes near/beyond upper band = strong uptrend
- Price consistently closes near/beyond lower band = strong downtrend
- Entry: Pullback to middle band during band walk
- Confirmation: Middle band acts as support/resistance
- Exit: Price closes on opposite side of middle band

**Triple Confirmation Setup:**
1. BB squeeze detected (low BandWidth)
2. RSI near 50 (neutral, coiled)
3. Breakout candle with volume surge
4. Enter direction of first decisive band break

### 1.2 RSI (Relative Strength Index)

**Parameters:**
- Period: 14 (standard), 7 (scalping), 21 (swing)
- Overbought: 70 (standard), 80 (trending), 60 (bearish bias)
- Oversold: 30 (standard), 20 (trending), 40 (bullish bias)

**Strategy A: Regular Divergence (Reversal)**
- Bullish: Price makes Lower Low, RSI makes Higher Low -> Buy signal
- Bearish: Price makes Higher High, RSI makes Lower High -> Sell signal
- Minimum 5 bars between divergence points
- Best on 4H and daily timeframes
- Confirmation: Wait for RSI to cross back above 30 (bullish) or below 70 (bearish)

**Strategy B: Hidden Divergence (Continuation)**
- Bullish Hidden: Price makes Higher Low, RSI makes Lower Low -> Buy (trend continues up)
- Bearish Hidden: Price makes Lower High, RSI makes Higher High -> Sell (trend continues down)
- Trade in direction of prevailing trend only
- Higher probability than regular divergence when trend is established

**Strategy C: Multi-Timeframe RSI**
- Higher TF (Daily/4H): Determine trend direction
- Lower TF (1H/15m): Time entries
- Rule: Only take long signals on lower TF when higher TF RSI > 50
- Rule: Only take short signals on lower TF when higher TF RSI < 50
- Sweet spot entries: Higher TF RSI 40-60 (pullback zone in trend)

**RSI Ranges by Market Regime:**
- Bull trend: RSI oscillates 40-80, treat 40-50 as oversold
- Bear trend: RSI oscillates 20-60, treat 50-60 as overbought
- Ranging: Standard 30-70 levels apply

### 1.3 MACD (Moving Average Convergence Divergence)

**Parameters:**
- Fast EMA: 12 (standard), 8 (aggressive), 5 (scalping)
- Slow EMA: 26 (standard), 21 (aggressive), 13 (scalping)
- Signal: 9 (standard), 5 (aggressive)

**Signal Generation:**
- Bullish: MACD line crosses above signal line
- Bearish: MACD line crosses below signal line
- Strong signal: Cross occurs below zero line (bullish) or above zero line (bearish)
- Histogram divergence: More reliable than line crossover alone
- Zero-line crossover: Trend direction confirmation

**MACD + EMA Filter:**
- Only take MACD buy signals when price > 200 EMA
- Only take MACD sell signals when price < 200 EMA
- Reduces false signals by ~30-40%

### 1.4 EMA Crossovers

**Common Pairs:**
- 9/21 EMA: Scalping/day trading (1m-15m charts)
- 20/50 EMA: Swing trading (1H-4H charts)
- 50/200 EMA: Position trading / Golden Cross / Death Cross (daily)

**Entry Rules:**
- Fast EMA crosses above slow EMA = Long
- Fast EMA crosses below slow EMA = Short
- Price must be on the correct side of both EMAs
- Slope of slow EMA confirms trend strength

**EMA Ribbon (8, 13, 21, 34, 55, 89):**
- All EMAs aligned and fanning = strong trend
- EMAs converging/tangling = consolidation (avoid)
- Entry on pullback to first EMA in the ribbon

### 1.5 VWAP (Volume Weighted Average Price)

**Application in Crypto (24/7 Market):**
- Anchor: Daily reset (UTC 00:00), Weekly, or Monthly
- Crypto-specific: Use rolling 24H VWAP since no session close

**Strategies:**
- Mean Reversion: Price deviates >2 VWAP StdDev bands -> revert to VWAP
- Trend Following: Price consistently above VWAP = bullish bias, below = bearish
- VWAP Bounce: First retest of VWAP after sustained move = high-probability entry
- Institutional level: Anchored VWAP from significant swing high/low

**VWAP + Volume Profile Combo (Triple Combo):**
- Anchored VWAP + Volume Profile HVN + S/R level at same price = strongest setup
- HVN (High Volume Node): Fair value zone, price tends to consolidate
- LVN (Low Volume Node): Price moves through quickly, use as targets
- POC (Point of Control): Highest volume price, strongest magnet

### 1.6 Volume-Based Indicators

**OBV (On-Balance Volume):**
- Rising OBV + rising price = trend confirmed
- Rising OBV + falling price = bullish divergence (accumulation)
- Falling OBV + rising price = bearish divergence (distribution)
- OBV breakout above its own resistance = leading signal

**Volume Profile:**
- Value Area (VA): 70% of volume, defines fair value range
- VAH (Value Area High): Resistance level
- VAL (Value Area Low): Support level
- POC: Strongest magnet for price
- Trading rule: Price above VA = bullish, below = bearish
- Breakout from VA with volume = directional move

**Volume Confirmation Rules:**
- Valid breakout: Volume >= 1.5x 20-period average
- Exhaustion: Spike volume + reversal candle = potential top/bottom
- Declining volume on pullback = healthy trend continuation
- Rising volume on pullback = potential trend reversal

### 1.7 Volatility Indicators

**ATR (Average True Range):**
- Period: 14 (standard), 7 (short-term), 21 (longer-term)
- Uses: Stop-loss placement, position sizing, regime detection
- ATR multiple for stops: 1.5x (tight), 2.0x (standard), 3.0x (wide)
- Volatility filter: ATR/Price ratio indicates regime
  - < 1%: Low volatility (range-bound strategies)
  - 1-3%: Normal volatility (all strategies viable)
  - > 3%: High volatility (reduce size, widen stops)
  - > 5%: Extreme (reduce/avoid, or very wide stops with small size)

**Keltner Channels:**
- Parameters: 20 EMA, 1.5x ATR (standard), 2.0x ATR (wide)
- BB inside Keltner = Squeeze (TTM Squeeze indicator)
- BB outside Keltner = Expansion/Breakout
- Keltner more stable than BB (ATR vs StdDev based)
- Use for: Trend direction, dynamic S/R, mean reversion targets

**ATR Ratio (ATR/Close):**
- BTC typical ranges: 1.5-4% (normal), 5%+ (high vol event)
- Altcoin typical ranges: 3-8% (normal), 10%+ (high vol event)
- Use to normalize volatility across different assets

---

## 2. ENTRY/EXIT STRATEGIES

### 2.1 Mean Reversion

**Core Concept:** Price tends to revert to a statistical mean (SMA, VWAP, equilibrium).

**Setup:**
- Identify mean: 20 SMA, VWAP, or Bollinger midline
- Entry: Price deviates >2 standard deviations from mean
- Direction: Counter to the deviation (buy low, sell high)
- Confirmation: RSI extreme + reversal candle pattern
- Target: Mean (conservative) or opposite band (aggressive)
- Stop: Beyond the extreme + buffer (1x ATR)

**Best Conditions:**
- Ranging/sideways markets
- Well-defined support/resistance channels
- Low-to-moderate volatility
- Assets with high mean reversion speed (OU theta > 0.1)

**Crypto Considerations:**
- Crypto mean reverts less reliably than traditional assets
- Use shorter lookback periods (crypto regimes shift faster)
- Tighter stops required (trends can be violent)
- Filter: Only take mean reversion when ADX < 25

### 2.2 Momentum/Trend Following

**Core Concept:** Strong trends tend to persist. Enter in direction of established trend.

**Setup:**
- Trend identification: Price > 50 EMA + 50 EMA > 200 EMA + ADX > 25
- Entry: Pullback to dynamic support (EMA, trendline) within trend
- Confirmation: Momentum indicator (MACD histogram, RSI) turning back toward trend
- Target: Previous swing high/low or Fibonacci extension (1.272, 1.618)
- Stop: Below last swing low (long) or above last swing high (short)
- Trailing: Move stop to breakeven at 1R, trail at 2x ATR

**Trend Strength Filters:**
- ADX > 25: Trending (trade momentum)
- ADX < 20: Ranging (trade mean reversion)
- ADX 20-25: Transitional (reduce size or wait)
- ADX slope positive + > 25: Strengthening trend (best entries)

### 2.3 Breakout Strategies

**Classic Breakout:**
- Range identification: Minimum 20 bars of consolidation
- Entry: Close above/below range + volume confirmation (>1.5x avg)
- False breakout filter: Wait for retest of breakout level
- Stop: Inside the range (midpoint or opposite side depending on R:R)
- Target: Range height projected from breakout point

**Volume-Confirmed Breakout:**
- Breakout candle volume > 2x average
- Next 3 candles maintain above-average volume
- Pullback on declining volume = legitimate breakout

**Failure Breakout (Fade):**
- Price breaks level but closes back inside range within 3 bars
- Volume on breakout declining (weak conviction)
- Entry: Opposite direction after failed breakout
- Very high probability setup in ranging markets

### 2.4 Scalping (1m-15m)

**Characteristics:**
- Hold time: Seconds to minutes
- Target: 0.1-0.5% per trade
- Stop: 0.05-0.2% per trade
- Frequency: 20-100+ trades/day
- Leverage: 5-20x (small position, tight stops)
- Win rate target: 60-70%

**Key Setups:**
- EMA 9/21 cross on 1m/5m + volume spike
- VWAP bounce/rejection on 1m
- Order book imbalance (bid/ask ratio >2:1)
- Rapid RSI oversold/overbought bounce (RSI 7-period)

**Requirements:**
- Very low latency execution
- Tight spreads (BTC/ETH only for most scalpers)
- Fee optimization (maker rebates critical at this frequency)
- Maker fee on Bybit: -0.025% (rebate), Taker: 0.075%

### 2.5 Swing Trading (4H-Daily)

**Characteristics:**
- Hold time: 2-14 days
- Target: 3-15% per trade
- Stop: 1.5-5% per trade
- Frequency: 2-8 trades/week
- Leverage: 2-5x
- Win rate target: 45-55% with R:R >= 2:1

**Key Setups:**
- Multi-timeframe trend alignment (Daily trend + 4H entry)
- Support/resistance bounce with indicator confirmation
- Fibonacci retracement entry (38.2%, 50%, 61.8%) in trend
- BB squeeze breakout on 4H chart

### 2.6 Position Trading (Daily-Weekly)

**Characteristics:**
- Hold time: Weeks to months
- Target: 15-50%+ per trade
- Stop: 5-15% per trade
- Frequency: 1-4 trades/month
- Leverage: 1-3x (or spot)
- Win rate target: 35-45% with R:R >= 3:1

**Key Setups:**
- Golden Cross / Death Cross (50/200 EMA)
- Major support/resistance levels on weekly chart
- Macro regime shifts (risk-on/risk-off)
- Funding rate regime trades (persistent positive/negative)

### 2.7 Multi-Indicator Confluence

**Confluence Scoring System (example):**
Each signal adds +1 to confluence score. Minimum 3/5 for entry:

| Signal | Weight |
|--------|--------|
| Trend alignment (EMA stack) | +1 |
| Momentum confirmation (RSI/MACD) | +1 |
| Volume confirmation | +1 |
| Key level (S/R, Fib, VWAP) | +1 |
| Volatility context (BB/Keltner) | +1 |

- Score 3: Valid entry, standard size
- Score 4: Strong entry, 1.5x size
- Score 5: High-conviction entry, 2x size
- Score < 3: No trade

---

## 3. RISK MANAGEMENT

### 3.1 Position Sizing

**Fixed Fractional:**
- Risk per trade: 0.5-2% of account equity
- Formula: Position Size = (Account * Risk%) / (Entry - Stop)
- Conservative: 0.5-1%
- Moderate: 1-1.5%
- Aggressive: 1.5-2%
- NEVER exceed 2% per trade for systematic strategies

**Kelly Criterion:**
- Formula: f* = (b*p - q) / b
  - f* = fraction of capital to bet
  - b = win/loss ratio (average win / average loss)
  - p = probability of winning
  - q = probability of losing (1 - p)
- Example: 55% win rate, 1.5:1 R:R -> f* = (1.5*0.55 - 0.45)/1.5 = 25%
- CRITICAL: Use Half-Kelly (f*/2) or Quarter-Kelly (f*/4) in practice
- Full Kelly is theoretically optimal but produces unacceptable drawdowns
- Half-Kelly: ~75% of full Kelly returns with ~50% of the drawdown
- Quarter-Kelly: Recommended for crypto due to fat tails and regime shifts

**Volatility-Based (ATR) Sizing:**
- Formula: Position Size = (Account * Risk%) / (N * ATR)
  - N = ATR multiple for stop distance (typically 2.0-3.0)
- Effect: Automatically reduces size in volatile markets, increases in calm markets
- Normalization: Ensures consistent dollar risk regardless of volatility
- Example: $100k account, 1% risk, BTC ATR = $2,000, N=2
  - Position Size = ($100k * 0.01) / (2 * $2,000) = $1,000 / $4,000 = 0.25 BTC

**Volatility-Adjusted Position Sizing Table:**
| ATR/Price | Vol Regime | Max Risk/Trade | Max Leverage |
|-----------|-----------|----------------|--------------|
| < 1.5% | Low | 2.0% | 10x |
| 1.5-3% | Normal | 1.0% | 5x |
| 3-5% | High | 0.5% | 3x |
| > 5% | Extreme | 0.25% | 1-2x |

### 3.2 Stop-Loss Strategies

**Fixed Percentage:**
- Simple: Set stop at X% below/above entry
- BTC: 1-3% (scalp), 3-5% (swing), 5-10% (position)
- Altcoins: 2-5% (scalp), 5-10% (swing), 10-15% (position)
- Problem: Doesn't adapt to volatility

**ATR-Based (Recommended):**
- Stop distance = N * ATR(14)
- N = 1.5 (tight), 2.0 (standard), 3.0 (wide)
- Adapts to current volatility automatically
- Place stop at: Entry - (N * ATR) for longs, Entry + (N * ATR) for shorts
- Recalculate ATR at entry time only (don't move stop closer)

**Structure-Based:**
- Place stop below last swing low (longs) or above last swing high (shorts)
- Add buffer: Swing point + 0.5x ATR
- Most logical placement but can be wide
- Combine with ATR: Use whichever is tighter (structure or ATR)

**Trailing Stop Methods:**
| Method | Description | Best For |
|--------|-------------|----------|
| ATR Trail | Trail at 2-3x ATR behind price | Trend following |
| Chandelier Exit | ATR from highest high/lowest low | Swing trades |
| Parabolic SAR | Accelerating trail | Strong trends |
| EMA Trail | Trail at 20 EMA or 50 EMA | Position trades |
| Breakeven + Trail | Move to breakeven at 1R, then trail | Risk reduction |

**Time-Based Stop:**
- Exit if trade hasn't hit 0.5R profit within X candles
- Scalp: 5-10 candles of entry timeframe
- Swing: 5-10 days
- Rationale: Good setups tend to work quickly; lingering = thesis wrong

### 3.3 Take-Profit Strategies

**Fixed Percentage:**
- Set TP at X% from entry
- Scale: TP1 at 1-2%, TP2 at 3-5%, TP3 at 7-10% (swing)

**R-Multiple Based:**
- 1R = initial risk amount (entry to stop distance)
- TP1: 1R (breakeven move, take 25-33% off)
- TP2: 2R (take another 33-50%)
- TP3: 3R+ (let remainder ride with trail)
- Minimum acceptable R:R = 1.5:1 for trend, 1:1 for mean reversion

**Partial Exit Strategy (Recommended):**
```
At 1R profit: Close 25%, move stop to breakeven
At 2R profit: Close 25%, trail stop to 1R
At 3R profit: Close 25%, trail stop to 2R
Remainder: Trail with 2x ATR or EMA
```

**Technical Level Exits:**
- Next significant S/R level
- Fibonacci extension levels (1.272, 1.618, 2.618)
- Opposite Bollinger Band
- VWAP bands
- Volume Profile POC/VAH/VAL

### 3.4 Risk-Reward Framework

**Minimum R:R by Strategy Type:**
| Strategy | Min R:R | Target Win Rate | Edge |
|----------|---------|----------------|------|
| Scalping | 1:1 | 60%+ | Volume |
| Mean Reversion | 1:1 | 55%+ | Tight stops |
| Trend Following | 2:1+ | 40%+ | Let winners run |
| Breakout | 2:1+ | 35-45% | Big winners |
| Swing | 2:1 | 45-55% | Balanced |
| Position | 3:1+ | 35-40% | Large moves |

**Expected Value Calculation:**
- EV = (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
- Positive EV required for every strategy
- Example: 45% WR, 2.5R avg win, 1R avg loss
  - EV = (0.45 * 2.5) - (0.55 * 1.0) = 1.125 - 0.55 = +0.575R per trade

### 3.5 Maximum Drawdown Limits

**Account-Level Rules:**
- Daily loss limit: 2-3% of account
- Weekly loss limit: 5-7% of account
- Monthly loss limit: 10-15% of account
- Max drawdown before strategy pause: 15-20%
- Max drawdown before strategy review/halt: 25%

**Drawdown Response Protocol:**
| Drawdown Level | Action |
|---------------|--------|
| 0-5% | Normal operations |
| 5-10% | Reduce position sizes by 50% |
| 10-15% | Reduce to minimum size, review strategy |
| 15-20% | Pause new entries, only manage existing |
| 20%+ | Full stop, comprehensive review |

**Recovery Mathematics:**
| Drawdown | Required Recovery |
|----------|------------------|
| 5% | 5.3% |
| 10% | 11.1% |
| 20% | 25.0% |
| 30% | 42.9% |
| 50% | 100.0% |

### 3.6 Correlation and Portfolio Risk

**Portfolio-Level Position Limits:**
- Maximum correlated positions: 3 (e.g., BTC + ETH + SOL all long)
- Maximum total exposure: 3-5x account (across all positions with leverage)
- Sector concentration: No more than 50% in one sector (L1, DeFi, etc.)

**Correlation Management:**
- BTC/ETH correlation: ~0.85 (treat as ~1 position)
- Major alts to BTC: 0.6-0.8 (high correlation)
- In risk-off events, all crypto correlations -> 1.0
- Hedging: Short BTC futures to reduce portfolio beta during uncertainty

**Portfolio Heat:**
- Total portfolio risk = Sum of individual position risks
- Maximum portfolio heat: 5-6% of account at any time
- Example: 4 positions at 1.5% risk each = 6% portfolio heat (maximum)

---

## 4. CRYPTO-SPECIFIC CONSIDERATIONS

### 4.1 Funding Rate Arbitrage

**Mechanism:**
- Funding rate keeps perpetual price anchored to spot
- Bybit formula: F = Premium Index + clamp(Interest Rate - Premium Index, -0.05%, 0.05%)
- Funding interval: Every 8 hours (00:00, 08:00, 16:00 UTC on Bybit)
- Positive rate: Longs pay shorts
- Negative rate: Shorts pay longs

**Cash-and-Carry Arbitrage:**
- Setup: Buy spot + Short perpetual (equal size)
- Profit: Collect funding payments (delta-neutral)
- 2025 average annual return: ~19.26% (up from 14.39% in 2024)
- Sharpe Ratio: 5-10 (very high risk-adjusted returns)
- Risks: Exchange risk, spot-perp basis risk, liquidation risk on perp leg

**Directional Funding Strategy:**
- High positive funding (>0.05%/8h): Market overheated, bias short
- High negative funding (<-0.05%/8h): Market oversold, bias long
- Extreme funding (>0.1%/8h): Strong contrarian signal
- Combine with technical analysis for timing

**Implementation on Bybit:**
- Use Unified Trading Account for cross-margin between spot and perp
- Monitor funding rate history: https://www.bybit.com/data/basic/linear/funding-history
- Calculate effective APY: Rate * 3 * 365 (for 8h funding)
- Threshold: Only enter when APY > 15% (after fees)

### 4.2 Liquidation Levels and Leverage Management

**Liquidation Price Calculation (Bybit Linear):**
- Long: Liquidation = Entry * (1 - 1/Leverage + Maintenance Margin Rate)
- Short: Liquidation = Entry * (1 + 1/Leverage - Maintenance Margin Rate)
- Bybit BTC maintenance margin: 0.5% (for positions < 500 BTC)

**Leverage Guidelines:**
| Strategy | Max Leverage | Recommended | Margin Mode |
|----------|-------------|-------------|-------------|
| Scalping | 20x | 5-10x | Isolated |
| Day Trading | 10x | 3-5x | Isolated |
| Swing Trading | 5x | 2-3x | Cross |
| Position | 3x | 1-2x | Cross |
| Funding Arb | 3x | 1-2x | Cross |

**Liquidation Protection:**
- Set liquidation alerts at 150% of maintenance margin
- Cross-margin mode uses full account balance (more buffer)
- Isolated margin limits loss to position margin only
- Rule: Liquidation price must be > 2x ATR away from current price
- Never let liquidation price be within normal volatility range

**Leverage Sizing Formula:**
```
Effective Leverage = (Position Size * Entry Price) / Account Equity
Safe Leverage = 1 / (2 * ATR_Ratio)
Example: ATR/Price = 3% -> Safe Leverage = 1/(2*0.03) = 16.7x maximum
Recommended: Use 50% of safe leverage = 8x in this example
```

### 4.3 24/7 Market Considerations

**Session-Based Volatility Patterns:**
- Asia session (00:00-08:00 UTC): Lower volatility, range-bound
- Europe session (08:00-16:00 UTC): Increasing volatility, trend initiation
- US session (13:00-21:00 UTC): Highest volatility, major moves
- Overlap (13:00-16:00 UTC): Peak liquidity and volatility

**Weekend Effects:**
- Lower liquidity (30-50% of weekday)
- Wider spreads
- Flash crash risk higher
- Reduce position size or close positions before weekend
- Monday opens often gap from Friday levels (even though 24/7)

**Automation Requirements:**
- 24/7 monitoring impossible for humans
- Bot must handle: Stop-loss execution, trailing stops, funding payments
- Alert systems for: Liquidation proximity, drawdown limits, unusual volume
- Health checks: Exchange connectivity, position sync, balance verification

### 4.4 Volatility Regime Detection

**Simple Regime Classifier:**
```
ATR_ratio = ATR(14) / Close
SMA_ATR = SMA(ATR_ratio, 20)

Low Vol:    ATR_ratio < 0.7 * SMA_ATR
Normal Vol: 0.7 * SMA_ATR <= ATR_ratio <= 1.5 * SMA_ATR
High Vol:   ATR_ratio > 1.5 * SMA_ATR
Extreme:    ATR_ratio > 2.5 * SMA_ATR
```

**BB Width Regime:**
```
BBW = (Upper - Lower) / Middle
Squeeze:    BBW < 20th percentile of last 100 bars
Normal:     20th - 80th percentile
Expansion:  > 80th percentile
```

**Strategy Selection by Regime:**
| Regime | Primary Strategy | Leverage | Position Size |
|--------|-----------------|----------|---------------|
| Low Vol / Squeeze | Breakout, Mean Reversion | Normal | Normal-Large |
| Normal | Trend Following, Swing | Normal | Normal |
| High Vol | Wider stops, reduced size | Reduced | Half |
| Extreme | Defensive only or flat | Minimum | Quarter or none |

### 4.5 Market Microstructure

**Order Book Analysis:**
- Bid/Ask spread: BTC typically 0.01-0.05% on Bybit
- Depth imbalance: Bid volume >> Ask volume = short-term bullish
- Spoofing detection: Large orders that disappear = fake levels
- Absorption: Large sell wall eaten by buyers = bullish

**Bybit Fee Structure (VIP 0):**
- Maker: 0.02% (some tiers get rebate)
- Taker: 0.055%
- Funding: Variable (every 8 hours)
- Impact on strategies: Scalping needs maker orders to be profitable
- Break-even calculation: Include round-trip fees + slippage (0.03-0.05%)

**Slippage Estimation:**
- BTC: 0.01-0.03% for <$500k positions
- ETH: 0.02-0.05% for <$200k positions
- Altcoins: 0.05-0.2% depending on liquidity
- Always use limit orders where possible
- Market orders during high vol: Slippage can be 0.5%+

---

## 5. ADVANCED QUANT CONCEPTS

### 5.1 Regime Detection

**Markov Regime Switching:**
- 2-state model: Trending vs. Ranging
- 3-state model: Bull Trend, Bear Trend, Range
- Hidden Markov Model estimates transition probabilities
- Implementation: Use `hmmlearn` or `statsmodels` in Python
- Update regime estimate on each new bar

**ADX-Based Regime (Simple, Effective):**
```python
def detect_regime(adx, adx_slope, price, ema200):
    if adx > 25 and adx_slope > 0:
        if price > ema200:
            return "STRONG_UPTREND"
        else:
            return "STRONG_DOWNTREND"
    elif adx > 25:
        return "WEAKENING_TREND"
    elif adx < 20:
        return "RANGE"
    else:
        return "TRANSITIONAL"
```

**Hurst Exponent:**
- H > 0.5: Trending (use momentum strategies)
- H = 0.5: Random walk (no edge)
- H < 0.5: Mean reverting (use mean reversion strategies)
- Calculate over rolling window (100-500 bars)
- Crypto BTC typically H = 0.45-0.55 (varies by regime)

### 5.2 Volatility Clustering (GARCH)

**GARCH(1,1) Model:**
```
sigma_t^2 = omega + alpha * epsilon_{t-1}^2 + beta * sigma_{t-1}^2
```
- omega: Long-run variance constant
- alpha: Reaction to recent shocks (crypto: 0.09-0.37, higher than equities)
- beta: Persistence of volatility (crypto: typically 0.5-0.85)
- alpha + beta: Persistence measure (closer to 1 = more persistent)
- Crypto exhibits stronger volatility clustering than equities
- Volatility clusters can last months in crypto (vs days/weeks in equities)

**Practical Application:**
- Forecast next-period volatility for position sizing
- High forecast vol -> reduce position size, widen stops
- Low forecast vol -> increase position size, tighter stops
- GARCH VaR: Better tail risk estimation than normal distribution
- Use EGARCH for asymmetric volatility (leverage effect)

**Enhanced Models for Crypto:**
- GJR-GARCH: Captures asymmetric shocks (larger for negative returns)
- MSGARCH (Markov-Switching GARCH): Regime-aware volatility
- GRU-GARCH: Neural network enhanced (best empirical performance 2025)
- Use for: Options pricing, VaR, dynamic position sizing

### 5.3 Statistical Arbitrage

**Pairs Trading in Crypto:**
- Identify cointegrated pairs (e.g., BTC/ETH, SOL/AVAX)
- Test with Engle-Granger or Johansen test
- Spread = Asset1 - beta * Asset2
- Entry: Spread > 2 standard deviations from mean
- Exit: Spread returns to mean
- Stop: Spread > 3 standard deviations (divergence)
- Retest cointegration monthly (crypto relationships break faster)

**Cross-Exchange Arbitrage:**
- Price differences between Bybit, Binance, OKX
- Typical opportunity: 0.01-0.1% (often < fees)
- Requires: Co-located infrastructure, API optimization
- Latency-sensitive: Opportunities disappear in milliseconds

**Basis Trading:**
- Spread between spot and perpetual (or quarterly futures)
- Positive basis (contango): Short futures, long spot
- Negative basis (backwardation): Long futures, short spot
- Converges at settlement (quarterly) or via funding (perpetual)

### 5.4 Mean Reversion Speed (Ornstein-Uhlenbeck)

**OU Process:**
```
dX = theta * (mu - X) * dt + sigma * dW
```
- theta: Speed of mean reversion (higher = faster reversion)
- mu: Long-run mean level
- sigma: Volatility of the process

**Practical Application:**
- Estimate theta on price spreads or indicator values
- theta > 0.1 (daily): Fast mean reversion, viable for trading
- theta < 0.01 (daily): Slow reversion, not tradeable
- Half-life of mean reversion: ln(2) / theta
  - Half-life < 5 days: Scalping/day trading candidate
  - Half-life 5-30 days: Swing trading candidate
  - Half-life > 30 days: Too slow for most strategies

**Parameter Estimation:**
```python
# Simple OLS estimation
# X_t - X_{t-1} = a + b * X_{t-1} + error
# theta = -b (annualized: -b * bars_per_year)
# mu = -a / b
# sigma = std(residuals) * sqrt(bars_per_year)
import numpy as np
def estimate_ou_params(series, dt=1):
    x = series[:-1]
    dx = np.diff(series)
    b, a = np.polyfit(x, dx, 1)
    theta = -b / dt
    mu = -a / b
    sigma = np.std(dx - (a + b * x)) / np.sqrt(dt)
    half_life = np.log(2) / theta
    return theta, mu, sigma, half_life
```

### 5.5 Sharpe Ratio & Performance Metrics

**Sharpe Ratio:**
- Formula: (Annualized Return - Risk Free Rate) / Annualized Volatility
- Crypto risk-free rate: Use USDT lending rate (~5-10%) or 0% for simplicity
- Annualization: Multiply daily Sharpe by sqrt(365) for crypto (24/7 market)
- Good: SR > 1.0
- Very Good: SR > 2.0
- Suspicious if backtested: SR > 3.0 (likely overfit)
- Live SR typically 30-50% lower than backtest SR

**Sortino Ratio (Preferred for Crypto):**
- Uses downside deviation instead of total volatility
- Better for crypto where upside volatility is desirable
- Formula: (Return - MAR) / Downside Deviation
- Prefer Sortino > 2.0

**Calmar Ratio:**
- Return / Max Drawdown
- Good: > 1.0
- Target for systematic strategies: > 2.0
- Funding arbitrage typically achieves 5-10

**Other Key Metrics:**
| Metric | Target | Red Flag |
|--------|--------|----------|
| Win Rate | 40-65% | > 80% (overfit) |
| Profit Factor | 1.5-3.0 | > 5.0 (overfit) |
| Max Drawdown | < 15% | > 25% |
| Avg Win/Avg Loss | > 1.5 | < 0.8 |
| Recovery Factor | > 3.0 | < 1.0 |
| Trade Count | > 100 | < 30 (insufficient) |

### 5.6 Backtesting Pitfalls

**Look-Ahead Bias:**
- Using future data in calculations (e.g., full-bar OHLC at bar open)
- Fix: Only use data available at decision time
- Common in: Feature engineering, normalization, regime labels
- Test: Run strategy bar-by-bar, verify each signal uses only past data

**Survivorship Bias:**
- Only testing on assets that still exist/trade
- Fix: Include delisted coins in universe
- Impact: Overstates returns by 1-5% annually
- Crypto-specific: Many altcoins go to zero; ignoring them inflates backtests

**Overfitting:**
- Too many parameters relative to data
- Rule of thumb: Maximum 1 parameter per 100 trades in sample
- 20+ parameters = almost certainly overfit
- Fix: Walk-forward analysis, out-of-sample testing, cross-validation

**Walk-Forward Analysis (Gold Standard):**
```
Total Data: [========================================]
Step 1: [TRAIN==========][TEST===]
Step 2:     [TRAIN==========][TEST===]
Step 3:         [TRAIN==========][TEST===]
Step 4:             [TRAIN==========][TEST===]
...

Train: 70-80% of window
Test:  20-30% of window
Roll forward by test period length
Aggregate OOS results = realistic performance estimate
```

**Realistic Simulation Checklist:**
- [ ] Include exchange fees (maker/taker)
- [ ] Include slippage (0.01-0.1% depending on asset/size)
- [ ] Include funding rate payments (for perpetuals)
- [ ] Use limit order fill model (not guaranteed fills)
- [ ] Account for execution latency (1-5 seconds for API)
- [ ] Test across different market regimes
- [ ] Minimum 200+ trades in sample
- [ ] Out-of-sample period >= 6 months
- [ ] Walk-forward validation
- [ ] Monte Carlo simulation for drawdown distribution
- [ ] Expect live performance 30-50% worse than backtest

**Data Quality:**
- Use clean OHLCV data from exchange API
- Handle gaps, outliers, exchange maintenance periods
- Verify OHLCV consistency (High >= Open, Close, Low)
- Minimum data: 1 year for swing, 3 months for scalping
- Recommended: 2+ years covering multiple regimes

---

## 6. STRATEGY ARCHETYPES WITH PARAMETER RANGES

### 6.1 Conservative / Defensive

**Goal:** Capital preservation with steady returns. Minimize drawdowns.

**Parameters:**
```yaml
Risk Management:
  risk_per_trade: 0.3-0.5%
  max_daily_loss: 1.5%
  max_weekly_loss: 3%
  max_drawdown_halt: 8%
  max_open_positions: 2
  max_leverage: 2x
  margin_mode: cross

Entry Criteria:
  min_confluence_score: 4/5
  trend_filter: price > 200 EMA on daily
  volume_filter: > 1.2x 20-period avg
  regime_filter: ADX > 20 (trending only)

Indicators:
  primary: EMA 50/200 crossover on daily
  confirmation: RSI(14) 40-60 zone pullback
  volatility: BB(20,2) not in squeeze
  volume: OBV trending with price

Exit Strategy:
  stop_loss: 2.5x ATR(14)
  take_profit_1: 1.5R (close 50%)
  take_profit_2: 3.0R (close 30%)
  trailing: 3x ATR on remainder
  time_stop: 20 days max hold

Expected Performance:
  annual_return: 15-30%
  max_drawdown: 5-10%
  sharpe_ratio: 1.5-2.5
  win_rate: 50-60%
  trades_per_month: 3-6
```

### 6.2 Moderate / Balanced

**Goal:** Balance between growth and risk. Consistent returns with controlled drawdowns.

**Parameters:**
```yaml
Risk Management:
  risk_per_trade: 0.5-1.0%
  max_daily_loss: 2%
  max_weekly_loss: 5%
  max_drawdown_halt: 12%
  max_open_positions: 3
  max_leverage: 3-5x
  margin_mode: isolated

Entry Criteria:
  min_confluence_score: 3/5
  trend_filter: price > 50 EMA on 4H
  volume_filter: > 1.0x average
  regime_filter: ADX > 15

Indicators:
  primary: EMA 20/50 crossover on 4H
  confirmation: RSI(14) divergence or extreme
  volatility: BB(20,2) squeeze breakout
  volume: Volume spike on breakout candle
  secondary: MACD histogram confirmation

Exit Strategy:
  stop_loss: 2.0x ATR(14)
  take_profit_1: 1R (close 25%)
  take_profit_2: 2R (close 25%)
  take_profit_3: 3R (close 25%)
  trailing: 2x ATR on remainder
  time_stop: 10 days max hold

Expected Performance:
  annual_return: 30-60%
  max_drawdown: 10-18%
  sharpe_ratio: 1.0-2.0
  win_rate: 45-55%
  trades_per_month: 6-15
```

### 6.3 Aggressive / Growth

**Goal:** Maximize returns. Accept higher drawdowns for higher gains.

**Parameters:**
```yaml
Risk Management:
  risk_per_trade: 1.0-2.0%
  max_daily_loss: 3%
  max_weekly_loss: 7%
  max_drawdown_halt: 20%
  max_open_positions: 5
  max_leverage: 5-10x
  margin_mode: isolated

Entry Criteria:
  min_confluence_score: 2/5
  trend_filter: EMA 9 > EMA 21 on 1H
  volume_filter: any
  regime_filter: none (trade all regimes)

Indicators:
  primary: EMA 9/21 crossover on 1H
  confirmation: RSI(7) momentum
  volatility: Keltner Channel breakout
  volume: OBV confirmation
  additional: Funding rate extreme as contrarian signal

Exit Strategy:
  stop_loss: 1.5x ATR(14)
  take_profit_1: 1R (close 20%)
  take_profit_2: 2R (close 30%)
  take_profit_3: 4R+ (close 30%)
  trailing: 1.5x ATR on remainder
  time_stop: 5 days max hold

Expected Performance:
  annual_return: 60-150%+
  max_drawdown: 15-30%
  sharpe_ratio: 0.8-1.5
  win_rate: 40-50%
  trades_per_month: 15-30
```

### 6.4 Scalping

**Goal:** High-frequency small gains. Profit from bid-ask spread and micro-moves.

**Parameters:**
```yaml
Risk Management:
  risk_per_trade: 0.1-0.3%
  max_daily_loss: 2%
  max_trade_loss: 0.15% of account
  daily_trade_limit: 50-100
  max_leverage: 10-20x
  margin_mode: isolated
  mandatory_break_after: 3 consecutive losses

Entry Criteria:
  min_confluence_score: 2/3
  spread_filter: < 0.02%
  volume_filter: active session (US/EU)
  latency_requirement: < 100ms

Indicators:
  primary: EMA 9/21 on 1m or 5m
  confirmation: RSI(7) extreme bounce
  volatility: ATR for stop sizing
  microstructure: Order book imbalance > 2:1
  volume: Volume spike detection

Exit Strategy:
  stop_loss: 0.5x ATR(7) or 0.1-0.2%
  take_profit: 0.8-1.5x ATR(7) or 0.1-0.5%
  time_stop: 5-15 candles (1m-5m chart)
  no_partial_exits: too small for scaling

Execution:
  order_type: Limit (maker) whenever possible
  fee_sensitivity: Critical (must net maker rebates)
  pairs: BTC/USDT, ETH/USDT only (liquidity)

Expected Performance:
  annual_return: 50-200%+
  max_drawdown: 5-15%
  sharpe_ratio: 2.0-4.0
  win_rate: 58-70%
  trades_per_day: 20-80
```

### 6.5 Swing Trading

**Goal:** Capture medium-term price swings. Best risk-adjusted returns for most traders.

**Parameters:**
```yaml
Risk Management:
  risk_per_trade: 0.5-1.5%
  max_weekly_loss: 4%
  max_drawdown_halt: 15%
  max_open_positions: 3-5
  max_leverage: 2-5x
  margin_mode: isolated or cross
  max_correlated_positions: 2

Entry Criteria:
  min_confluence_score: 3/5
  trend_filter: Daily trend alignment (50 EMA direction)
  volume_filter: > 1.2x average on signal candle
  regime_filter: ADX > 20 on daily

Indicators:
  primary: Fibonacci retracement in trend (38.2%, 50%, 61.8%)
  confirmation: RSI(14) divergence on 4H
  volatility: BB(20,2) squeeze then breakout on 4H
  trend: MACD on daily for direction
  volume: Volume Profile for S/R levels
  timing: Multi-TF RSI alignment

Exit Strategy:
  stop_loss: Below swing low + 0.5x ATR (structure-based)
  take_profit_1: Previous swing high/low (close 33%)
  take_profit_2: Fib extension 1.272 (close 33%)
  take_profit_3: Fib extension 1.618 (close 34%)
  trailing: 20 EMA on 4H chart
  time_stop: 14 days max hold

Expected Performance:
  annual_return: 40-80%
  max_drawdown: 10-20%
  sharpe_ratio: 1.2-2.5
  win_rate: 45-55%
  trades_per_month: 4-12
```

### 6.6 Marathon / Position Holding

**Goal:** Capture major trends. Ride macro moves with patience.

**Parameters:**
```yaml
Risk Management:
  risk_per_trade: 0.5-1.0%
  max_monthly_loss: 5%
  max_drawdown_halt: 15%
  max_open_positions: 2-3
  max_leverage: 1-3x
  margin_mode: cross
  funding_rate_budget: Include in cost calculation

Entry Criteria:
  min_confluence_score: 4/5
  trend_filter: Golden Cross (50/200 EMA) on daily
  macro_filter: BTC dominance trend, total market cap trend
  volume_filter: Weekly volume confirmation
  regime_filter: Confirmed trend on weekly chart

Indicators:
  primary: 50/200 EMA crossover on daily
  confirmation: Weekly RSI(14) > 50 (long) or < 50 (short)
  volatility: Monthly ATR for stop sizing
  trend: Ichimoku Cloud on daily/weekly
  macro: Funding rate trend, open interest trend
  volume: Weekly OBV trend

Exit Strategy:
  stop_loss: Weekly swing low + 1x ATR(14, weekly)
  take_profit_1: Major S/R level (close 25%)
  take_profit_2: Fibonacci extension 1.618 (close 25%)
  trailing: 50 EMA on daily chart
  time_stop: None (let macro thesis play out)
  invalidation: Weekly close below 200 EMA

Special Considerations:
  funding_costs: Track cumulative funding (can erode returns)
  rebalance: Monthly review of thesis
  hedge: Use options or short hedge if available
  dca_on_dips: Add to position at key levels within risk limits

Expected Performance:
  annual_return: 30-100%+
  max_drawdown: 15-30%
  sharpe_ratio: 0.8-1.5
  win_rate: 35-45%
  trades_per_quarter: 1-4
```

---

## 7. IMPLEMENTATION CHECKLIST

### Pre-Trade System
- [ ] Real-time market data feed (Bybit WebSocket)
- [ ] Indicator calculation engine (TA-Lib or custom)
- [ ] Signal generation with confluence scoring
- [ ] Regime detection module
- [ ] Position sizing calculator (volatility-adjusted)

### Execution System
- [ ] Order management (limit, market, stop, trailing)
- [ ] Slippage estimation and fee tracking
- [ ] Position tracking and PnL calculation
- [ ] Risk checks before order placement
- [ ] Circuit breakers (daily/weekly loss limits)

### Post-Trade System
- [ ] Trade logging and analytics
- [ ] Performance metrics dashboard
- [ ] Drawdown monitoring and alerts
- [ ] Strategy performance attribution
- [ ] Regular strategy review (weekly/monthly)

### Backtesting System
- [ ] Historical data pipeline (clean OHLCV)
- [ ] Walk-forward optimization framework
- [ ] Realistic fee/slippage model
- [ ] Out-of-sample testing protocol
- [ ] Monte Carlo simulation for robustness

---

## 8. QUICK REFERENCE: DECISION MATRIX

```
Market Condition Assessment:
1. Check regime (ADX, Hurst, BB Width)
2. Check volatility (ATR ratio, GARCH forecast)
3. Check trend (EMA stack, price vs 200 EMA)
4. Check sentiment (funding rate, OI)
5. Select strategy archetype based on above

Entry Decision:
1. Does signal match regime? (trend signal in trending market?)
2. Confluence score >= minimum?
3. Risk/reward >= minimum for strategy type?
4. Portfolio heat within limits?
5. No upcoming known events (CPI, FOMC, etc.)?
6. If all YES -> Execute with calculated position size

Position Management:
1. Stop-loss set immediately (ATR-based or structure-based)
2. Monitor against time-stop threshold
3. Scale out at pre-defined R-multiples
4. Trail stop on remainder
5. Track funding costs for perpetual positions
6. Review thesis if held > expected duration
```

---

*This knowledge base is designed for systematic implementation in Python-based trading engines
targeting Bybit USDT Linear Perpetual contracts. All parameter ranges should be validated
through backtesting before live deployment. Expect live performance to be 30-50% lower
than backtested results.*
