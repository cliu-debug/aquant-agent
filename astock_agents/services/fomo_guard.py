"""FOMO检测与情绪隔离模块

核心能力：
1. 追高行为检测 - 检测用户是否在高位追涨
2. 过度交易防护 - 限制交易频率，防止频繁买卖
3. 情绪隔离层 - 确保智能体分析不受市场情绪过度影响
4. 反FOMO信号校准 - 在市场狂热时自动降低信号强度
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger


class FOMODetector:
    """FOMO（Fear Of Missing Out）行为检测器

    检测场景：
    1. 连续买入同一股票（追高）
    2. 短时间内频繁交易
    3. 在市场狂热时加大仓位
    4. 在高点附近买入
    """

    MAX_DAILY_TRADES: int = 3
    MAX_WEEKLY_TRADES: int = 10
    MAX_SAME_STOCK_DAILY_BUYS: int = 2
    HIGH_POSITION_THRESHOLD: float = 0.8
    NEAR_HIGH_THRESHOLD: float = 0.95

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._trade_history: List[Dict[str, Any]] = []
        logger.info("[FOMO检测] 初始化完成")

    def record_trade(self, trade_info: Dict[str, Any]) -> None:
        """记录交易行为

        Args:
            trade_info: 交易信息字典，包含 stock_code, direction, price, quantity, timestamp
        """
        trade_info["recorded_at"] = datetime.now().isoformat()
        self._trade_history.append(trade_info)
        if len(self._trade_history) > 1000:
            self._trade_history = self._trade_history[-500:]

    def detect_chasing_high(
        self,
        stock_code: str,
        current_price: float,
        recent_high: float,
        position_pct: float,
    ) -> Dict[str, Any]:
        """检测追高行为

        Args:
            stock_code: 股票代码
            current_price: 当前价格
            recent_high: 近期最高价
            position_pct: 当前持仓比例

        Returns:
            检测结果字典
        """
        alerts = []

        price_ratio = current_price / recent_high if recent_high > 0 else 1.0

        if price_ratio >= self.NEAR_HIGH_THRESHOLD:
            alerts.append(
                f"当前价格接近近期高点（{price_ratio:.1%}），存在追高风险"
            )

        if position_pct >= self.HIGH_POSITION_THRESHOLD:
            alerts.append(
                f"该股仓位已达{position_pct:.1%}，高位加仓风险较大"
            )

        recent_buys = self._count_recent_buys(stock_code, hours=24)
        if recent_buys >= self.MAX_SAME_STOCK_DAILY_BUYS:
            alerts.append(
                f"24小时内已买入该股{recent_buys}次，存在追涨倾向"
            )

        is_fomo = len(alerts) > 0
        severity = "high" if len(alerts) >= 2 else "medium" if alerts else "none"

        if is_fomo:
            logger.warning(f"[FOMO检测] 发现追高行为: {stock_code}, {alerts}")

        return {
            "is_fomo": is_fomo,
            "severity": severity,
            "alerts": alerts,
            "stock_code": stock_code,
            "price_vs_high": round(price_ratio, 4),
        }

    def detect_overtrading(self, user_id: str = "default") -> Dict[str, Any]:
        """检测过度交易

        Args:
            user_id: 用户ID

        Returns:
            检测结果字典
        """
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())

        daily_trades = 0
        weekly_trades = 0

        for trade in self._trade_history:
            try:
                trade_time = datetime.fromisoformat(
                    trade.get("recorded_at", trade.get("timestamp", ""))
                )
                if trade_time >= today_start:
                    daily_trades += 1
                if trade_time >= week_start:
                    weekly_trades += 1
            except (ValueError, TypeError):
                continue

        alerts = []
        if daily_trades >= self.MAX_DAILY_TRADES:
            alerts.append(
                f"今日已交易{daily_trades}次，超过日限{self.MAX_DAILY_TRADES}次"
            )
        if weekly_trades >= self.MAX_WEEKLY_TRADES:
            alerts.append(
                f"本周已交易{weekly_trades}次，超过周限{self.MAX_WEEKLY_TRADES}次"
            )

        is_overtrading = len(alerts) > 0

        if is_overtrading:
            logger.warning(f"[FOMO检测] 发现过度交易: user={user_id}, {alerts}")

        return {
            "is_overtrading": is_overtrading,
            "daily_trades": daily_trades,
            "weekly_trades": weekly_trades,
            "daily_limit": self.MAX_DAILY_TRADES,
            "weekly_limit": self.MAX_WEEKLY_TRADES,
            "alerts": alerts,
        }

    def _count_recent_buys(self, stock_code: str, hours: int = 24) -> int:
        """统计近期对同一股票的买入次数

        Args:
            stock_code: 股票代码
            hours: 时间窗口（小时）

        Returns:
            买入次数
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        count = 0
        for trade in self._trade_history:
            if trade.get("stock_code") != stock_code:
                continue
            direction = trade.get("direction", "")
            if direction not in ("买入", "buy", "强烈买入", "strong_buy"):
                continue
            try:
                trade_time = datetime.fromisoformat(
                    trade.get("recorded_at", trade.get("timestamp", ""))
                )
                if trade_time >= cutoff:
                    count += 1
            except (ValueError, TypeError):
                continue
        return count


class EmotionIsolationLayer:
    """情绪隔离层

    确保智能体分析不受市场情绪过度影响：
    1. 市场狂热时自动降低买入信号强度
    2. 市场恐慌时防止过度悲观
    3. 对情绪驱动的信号进行校准
    """

    GREED_CALIBRATION: Dict[str, float] = {
        "强烈买入": 0.7,
        "买入": 0.85,
        "持有": 1.0,
        "卖出": 1.1,
        "强烈卖出": 1.2,
    }

    FEAR_CALIBRATION: Dict[str, float] = {
        "强烈买入": 1.2,
        "买入": 1.1,
        "持有": 1.0,
        "卖出": 0.85,
        "强烈卖出": 0.7,
    }

    SIGNAL_DOWNGRADE_MAP: Dict[str, str] = {
        "强烈买入": "买入",
        "买入": "持有",
        "强烈卖出": "卖出",
        "卖出": "持有",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        logger.info("[情绪隔离] 初始化完成")

    def calibrate_signal(
        self,
        signal: str,
        confidence: int,
        fear_greed_index: float,
    ) -> Dict[str, Any]:
        """根据市场情绪校准交易信号

        核心逻辑：恐惧时贪婪，贪婪时恐惧。
        - 市场极度贪婪时(>80)，降低买入信号强度
        - 市场极度恐惧时(<20)，降低卖出信号强度

        Args:
            signal: 原始交易信号
            confidence: 原始置信度
            fear_greed_index: 恐贪指数 0-100

        Returns:
            校准结果字典
        """
        calibrated_signal = signal
        calibrated_confidence = confidence
        calibration_reason = ""

        if fear_greed_index >= 80:
            calibration_factor = self.GREED_CALIBRATION.get(signal, 1.0)
            calibrated_confidence = int(confidence * calibration_factor)
            calibration_reason = (
                f"市场极度贪婪(恐贪指数={fear_greed_index:.0f})，"
                f"买入信号已校准（置信度{confidence}→{calibrated_confidence}）"
            )
            if fear_greed_index >= 90 and signal in ("强烈买入", "买入"):
                calibrated_signal = self.SIGNAL_DOWNGRADE_MAP.get(signal, signal)
                calibration_reason += f"，信号降级为{calibrated_signal}"

        elif fear_greed_index <= 20:
            calibration_factor = self.FEAR_CALIBRATION.get(signal, 1.0)
            calibrated_confidence = int(confidence * calibration_factor)
            calibration_reason = (
                f"市场极度恐惧(恐贪指数={fear_greed_index:.0f})，"
                f"卖出信号已校准（置信度{confidence}→{calibrated_confidence}）"
            )
            if fear_greed_index <= 10 and signal in ("强烈卖出", "卖出"):
                calibrated_signal = self.SIGNAL_DOWNGRADE_MAP.get(signal, signal)
                calibration_reason += f"，信号降级为{calibrated_signal}"

        calibrated_confidence = max(10, min(100, calibrated_confidence))

        was_calibrated = (
            calibrated_signal != signal or calibrated_confidence != confidence
        )

        if was_calibrated:
            logger.info(
                f"[情绪隔离] 信号校准: {signal}({confidence}) → "
                f"{calibrated_signal}({calibrated_confidence}), 原因: {calibration_reason}"
            )

        return {
            "original_signal": signal,
            "original_confidence": confidence,
            "calibrated_signal": calibrated_signal,
            "calibrated_confidence": calibrated_confidence,
            "was_calibrated": was_calibrated,
            "calibration_reason": calibration_reason,
            "fear_greed_index": fear_greed_index,
        }
