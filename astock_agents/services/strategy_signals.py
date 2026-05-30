"""策略信号生成器

内置多种经典技术分析策略，自动根据K线数据生成买卖信号。
支持与回测引擎无缝对接，无需手动输入交易信号。

策略列表：
1. MA金叉死叉 - 短期均线上穿/下穿长期均线
2. MACD策略 - DIF与DEA金叉/死叉
3. RSI超买超卖 - RSI低于超卖线买入，高于超买线卖出
4. 布林带策略 - 价格触及下轨买入，触及上轨卖出
5. KDJ策略 - K线上穿D线买入，下穿卖出
6. 组合策略 - 多策略投票综合信号
"""

from typing import List, Dict, Any, Optional
from loguru import logger


def generate_ma_signals(
    prices: List[Dict[str, Any]],
    short_period: int = 5,
    long_period: int = 20,
) -> List[Dict[str, str]]:
    """MA金叉死叉策略

    短期均线上穿长期均线=买入(金叉)，下穿=卖出(死叉)

    Args:
        prices: 价格数据列表，每个元素需包含 close 字段
        short_period: 短期均线周期
        long_period: 长期均线周期

    Returns:
        信号列表 [{"date": "...", "action": "buy/sell"}, ...]
    """
    signals = []
    if len(prices) < long_period + 1:
        return signals

    closes = [p["close"] for p in prices]

    for i in range(long_period, len(closes)):
        ma_short = sum(closes[i - short_period:i]) / short_period
        ma_short_prev = sum(closes[i - short_period - 1:i - 1]) / short_period
        ma_long = sum(closes[i - long_period:i]) / long_period
        ma_long_prev = sum(closes[i - long_period - 1:i - 1]) / long_period

        if ma_short_prev <= ma_long_prev and ma_short > ma_long:
            signals.append({"date": prices[i]["date"], "action": "buy"})
        elif ma_short_prev >= ma_long_prev and ma_short < ma_long:
            signals.append({"date": prices[i]["date"], "action": "sell"})

    logger.debug(f"[策略] MA({short_period}/{long_period}) 生成{len(signals)}个信号")
    return signals


def generate_macd_signals(
    prices: List[Dict[str, Any]],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> List[Dict[str, str]]:
    """MACD策略

    DIF上穿DEA=买入(金叉)，下穿=卖出(死叉)

    Args:
        prices: 价格数据列表
        fast_period: 快线EMA周期
        slow_period: 慢线EMA周期
        signal_period: 信号线EMA周期

    Returns:
        信号列表
    """
    signals = []
    if len(prices) < slow_period + signal_period + 1:
        return signals

    closes = [p["close"] for p in prices]

    def ema(data: List[float], period: int) -> List[float]:
        result = [data[0]]
        multiplier = 2 / (period + 1)
        for val in data[1:]:
            result.append(val * multiplier + result[-1] * (1 - multiplier))
        return result

    ema_fast = ema(closes, fast_period)
    ema_slow = ema(closes, slow_period)
    dif = [f - s for f, s in zip(ema_fast, ema_slow)]
    dea = ema(dif, signal_period)
    macd_hist = [(d - e) * 2 for d, e in zip(dif, dea)]

    for i in range(signal_period + 1, len(macd_hist)):
        if macd_hist[i - 1] <= 0 and macd_hist[i] > 0:
            signals.append({"date": prices[i]["date"], "action": "buy"})
        elif macd_hist[i - 1] >= 0 and macd_hist[i] < 0:
            signals.append({"date": prices[i]["date"], "action": "sell"})

    logger.debug(f"[策略] MACD({fast_period}/{slow_period}/{signal_period}) 生成{len(signals)}个信号")
    return signals


def generate_rsi_signals(
    prices: List[Dict[str, Any]],
    period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> List[Dict[str, str]]:
    """RSI超买超卖策略

    RSI低于超卖线=买入，高于超买线=卖出

    Args:
        prices: 价格数据列表
        period: RSI计算周期
        oversold: 超卖阈值
        overbought: 超买阈值

    Returns:
        信号列表
    """
    signals = []
    if len(prices) < period + 1:
        return signals

    closes = [p["close"] for p in prices]

    gains = []
    losses = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    rsi_values = []
    for i in range(period - 1, len(gains)):
        window_gains = gains[i - period + 1:i + 1]
        window_losses = losses[i - period + 1:i + 1]
        avg_gain = sum(window_gains) / period
        avg_loss = sum(window_losses) / period
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - 100 / (1 + rs))

    rsi_start_idx = period
    for i, rsi in enumerate(rsi_values):
        price_idx = rsi_start_idx + i
        if price_idx >= len(prices):
            break
        if rsi < oversold:
            signals.append({"date": prices[price_idx]["date"], "action": "buy"})
        elif rsi > overbought:
            signals.append({"date": prices[price_idx]["date"], "action": "sell"})

    logger.debug(f"[策略] RSI({period}) 生成{len(signals)}个信号")
    return signals


def generate_boll_signals(
    prices: List[Dict[str, Any]],
    period: int = 20,
    num_std: float = 2.0,
) -> List[Dict[str, str]]:
    """布林带策略

    价格触及下轨=买入，触及上轨=卖出

    Args:
        prices: 价格数据列表
        period: 布林带周期
        num_std: 标准差倍数

    Returns:
        信号列表
    """
    signals = []
    if len(prices) < period:
        return signals

    closes = [p["close"] for p in prices]

    for i in range(period, len(closes)):
        window = closes[i - period:i]
        ma = sum(window) / period
        variance = sum((x - ma) ** 2 for x in window) / period
        std = variance ** 0.5

        upper = ma + num_std * std
        lower = ma - num_std * std

        if closes[i] <= lower:
            signals.append({"date": prices[i]["date"], "action": "buy"})
        elif closes[i] >= upper:
            signals.append({"date": prices[i]["date"], "action": "sell"})

    logger.debug(f"[策略] BOLL({period},{num_std}) 生成{len(signals)}个信号")
    return signals


def generate_kdj_signals(
    prices: List[Dict[str, Any]],
    period: int = 9,
) -> List[Dict[str, str]]:
    """KDJ策略

    K线上穿D线=买入，下穿=卖出

    Args:
        prices: 价格数据列表，需包含 high/low/close 字段
        period: KDJ周期

    Returns:
        信号列表
    """
    signals = []
    if len(prices) < period + 1:
        return signals

    k_values = [50.0]
    d_values = [50.0]

    for i in range(period - 1, len(prices)):
        window = prices[i - period + 1:i + 1]
        highest = max(p["high"] for p in window)
        lowest = min(p["low"] for p in window)
        close = prices[i]["close"]

        if highest == lowest:
            rsv = 50.0
        else:
            rsv = (close - lowest) / (highest - lowest) * 100

        k = 2 / 3 * k_values[-1] + 1 / 3 * rsv
        d = 2 / 3 * d_values[-1] + 1 / 3 * k
        k_values.append(k)
        d_values.append(d)

    for i in range(2, len(k_values)):
        price_idx = period - 1 + i - 1
        if price_idx >= len(prices):
            break
        if k_values[i - 1] <= d_values[i - 1] and k_values[i] > d_values[i]:
            signals.append({"date": prices[price_idx]["date"], "action": "buy"})
        elif k_values[i - 1] >= d_values[i - 1] and k_values[i] < d_values[i]:
            signals.append({"date": prices[price_idx]["date"], "action": "sell"})

    logger.debug(f"[策略] KDJ({period}) 生成{len(signals)}个信号")
    return signals


def generate_combo_signals(
    prices: List[Dict[str, Any]],
    strategies: Optional[List[str]] = None,
    min_agreement: int = 2,
) -> List[Dict[str, str]]:
    """组合策略 - 多策略投票综合信号

    多个策略同时发出相同信号时才触发交易

    Args:
        prices: 价格数据列表
        strategies: 参与投票的策略名称列表，默认全部
        min_agreement: 最少需要几个策略同意才触发信号

    Returns:
        信号列表
    """
    all_strategies = {
        "ma": generate_ma_signals(prices),
        "macd": generate_macd_signals(prices),
        "rsi": generate_rsi_signals(prices),
        "boll": generate_boll_signals(prices),
        "kdj": generate_kdj_signals(prices),
    }

    active_strategies = strategies or list(all_strategies.keys())

    # 按日期汇总各策略信号
    date_signals: Dict[str, Dict[str, int]] = {}
    for strat_name in active_strategies:
        strat_signals = all_strategies.get(strat_name, [])
        for sig in strat_signals:
            date = sig["date"]
            if date not in date_signals:
                date_signals[date] = {"buy": 0, "sell": 0}
            date_signals[date][sig["action"]] += 1

    # 筛选达到最低同意数的信号
    combo_signals = []
    for date, counts in sorted(date_signals.items()):
        if counts["buy"] >= min_agreement:
            combo_signals.append({"date": date, "action": "buy"})
        elif counts["sell"] >= min_agreement:
            combo_signals.append({"date": date, "action": "sell"})

    logger.debug(f"[策略] 组合策略({len(active_strategies)}个, 最低{min_agreement}票) 生成{len(combo_signals)}个信号")
    return combo_signals


# 策略注册表
STRATEGY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "ma": {
        "name": "MA金叉死叉",
        "description": "短期均线上穿长期均线买入，下穿卖出",
        "generator": generate_ma_signals,
        "params": [
            {"key": "short_period", "label": "短期均线", "type": "int", "default": 5, "min": 2, "max": 30},
            {"key": "long_period", "label": "长期均线", "type": "int", "default": 20, "min": 5, "max": 120},
        ],
    },
    "macd": {
        "name": "MACD策略",
        "description": "DIF与DEA金叉买入，死叉卖出",
        "generator": generate_macd_signals,
        "params": [
            {"key": "fast_period", "label": "快线周期", "type": "int", "default": 12, "min": 5, "max": 30},
            {"key": "slow_period", "label": "慢线周期", "type": "int", "default": 26, "min": 10, "max": 60},
            {"key": "signal_period", "label": "信号线周期", "type": "int", "default": 9, "min": 3, "max": 20},
        ],
    },
    "rsi": {
        "name": "RSI超买超卖",
        "description": "RSI低于超卖线买入，高于超买线卖出",
        "generator": generate_rsi_signals,
        "params": [
            {"key": "period", "label": "RSI周期", "type": "int", "default": 14, "min": 5, "max": 30},
            {"key": "oversold", "label": "超卖阈值", "type": "float", "default": 30.0, "min": 10.0, "max": 40.0},
            {"key": "overbought", "label": "超买阈值", "type": "float", "default": 70.0, "min": 60.0, "max": 90.0},
        ],
    },
    "boll": {
        "name": "布林带策略",
        "description": "价格触及下轨买入，触及上轨卖出",
        "generator": generate_boll_signals,
        "params": [
            {"key": "period", "label": "布林带周期", "type": "int", "default": 20, "min": 5, "max": 60},
            {"key": "num_std", "label": "标准差倍数", "type": "float", "default": 2.0, "min": 1.0, "max": 3.0},
        ],
    },
    "kdj": {
        "name": "KDJ策略",
        "description": "K线上穿D线买入，下穿卖出",
        "generator": generate_kdj_signals,
        "params": [
            {"key": "period", "label": "KDJ周期", "type": "int", "default": 9, "min": 5, "max": 30},
        ],
    },
    "combo": {
        "name": "组合策略(多策略投票)",
        "description": "多个策略同时发出相同信号时才触发交易",
        "generator": generate_combo_signals,
        "params": [
            {"key": "min_agreement", "label": "最低同意数", "type": "int", "default": 2, "min": 2, "max": 5},
        ],
    },
}


def get_available_strategies() -> List[Dict[str, Any]]:
    """获取所有可用策略列表

    Returns:
        策略信息列表
    """
    result = []
    for key, info in STRATEGY_REGISTRY.items():
        result.append({
            "id": key,
            "name": info["name"],
            "description": info["description"],
            "params": info["params"],
        })
    return result


def generate_strategy_signals(
    strategy_id: str,
    prices: List[Dict[str, Any]],
    params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """根据策略ID和参数生成交易信号

    Args:
        strategy_id: 策略ID（ma/macd/rsi/boll/kdj/combo）
        prices: 价格数据列表
        params: 策略参数（可选，使用默认值）

    Returns:
        交易信号列表

    Raises:
        ValueError: 策略ID不存在
    """
    if strategy_id not in STRATEGY_REGISTRY:
        raise ValueError(f"未知策略: {strategy_id}，可用策略: {list(STRATEGY_REGISTRY.keys())}")

    strategy = STRATEGY_REGISTRY[strategy_id]
    generator = strategy["generator"]

    # 合并默认参数和用户参数
    kwargs: Dict[str, Any] = {}
    for param_def in strategy["params"]:
        key = param_def["key"]
        if params and key in params:
            value = params[key]
            if param_def["type"] == "int":
                value = int(value)
            elif param_def["type"] == "float":
                value = float(value)
            kwargs[key] = value
        else:
            kwargs[key] = param_def["default"]

    # 组合策略需要特殊处理
    if strategy_id == "combo":
        kwargs["prices"] = prices
    else:
        # 确保只传递该策略需要的参数
        sig = generator.__code__.co_varnames[1:generator.__code__.co_argcount]
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in sig}
        kwargs = filtered_kwargs

    signals = generator(prices, **kwargs)
    logger.info(f"[策略信号] {strategy['name']} 生成{len(signals)}个信号")
    return signals
