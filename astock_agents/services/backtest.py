"""回测系统引擎 - 用历史数据验证交易策略"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
from loguru import logger

from astock_agents.models.stock_data import StockData, StockPrice


@dataclass
class BacktestTrade:
    """回测交易记录"""
    date: datetime
    action: str  # buy / sell / sell_stop_loss / sell_take_profit / sell_close
    price: float
    quantity: int
    commission: float = 0.0
    reason: str = ""


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    stock_code: str
    stock_name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return_pct: float  # 总收益率%
    annual_return_pct: float  # 年化收益率%
    max_drawdown_pct: float  # 最大回撤%
    sharpe_ratio: Optional[float]  # 夏普比率
    win_rate: float  # 胜率%
    profit_factor: Optional[float]  # 盈亏比
    total_trades: int
    win_trades: int
    loss_trades: int
    avg_holding_days: float
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)  # 权益曲线
    benchmark_return_pct: Optional[float] = None  # 基准收益率（如沪深300）


class BacktestEngine:
    """
    回测引擎

    功能：
    1. 基于信号策略的回测
    2. 计算关键风险收益指标
    3. 生成权益曲线
    4. 与基准对比
    """

    # 交易费率
    COMMISSION_RATE = 0.0003
    COMMISSION_MIN = 5.0
    STAMP_TAX_RATE = 0.001  # 仅卖出

    def __init__(self, initial_capital: float = 1000000.0):
        """初始化回测引擎

        Args:
            initial_capital: 初始资金，默认100万
        """
        self.initial_capital = initial_capital

    def run(
        self,
        stock_data: StockData,
        signals: List[Dict[str, Any]],
        strategy_name: str = "自定义策略",
        position_size_pct: float = 0.2,  # 每次开仓占总资金比例
        stop_loss_pct: float = 0.07,  # 止损比例
        take_profit_pct: float = 0.15,  # 止盈比例
    ) -> BacktestResult:
        """
        执行回测

        Args:
            stock_data: 股票历史数据
            signals: 交易信号列表，格式 [{"date": "2024-01-15", "action": "buy"}, ...]
            strategy_name: 策略名称
            position_size_pct: 每次开仓占总资金比例
            stop_loss_pct: 止损比例
            take_profit_pct: 止盈比例

        Returns:
            BacktestResult: 回测结果
        """
        if not stock_data.prices:
            return self._empty_result(strategy_name, stock_data)

        prices = sorted(stock_data.prices, key=lambda p: p.date)
        price_map = {p.date.strftime("%Y-%m-%d"): p for p in prices}

        # 初始化
        cash = self.initial_capital
        position = 0  # 持仓数量
        entry_price = 0.0  # 入场价
        trades: List[BacktestTrade] = []
        equity_curve: List[Dict[str, Any]] = []

        # 信号按日期索引
        signal_map = {s["date"]: s["action"] for s in signals}

        # 逐日模拟
        for price in prices:
            date_str = price.date.strftime("%Y-%m-%d")
            action = signal_map.get(date_str)

            # 止损止盈检查
            if position > 0 and entry_price > 0:
                pnl_pct = (price.close - entry_price) / entry_price
                if pnl_pct <= -stop_loss_pct:
                    # 止损卖出
                    commission = self._calc_sell_commission(price.close, position)
                    cash = self._sell(price.close, position, cash)
                    trades.append(BacktestTrade(
                        date=price.date, action="sell_stop_loss",
                        price=price.close, quantity=position,
                        commission=commission,
                        reason=f"止损({pnl_pct*100:.1f}%)"
                    ))
                    position = 0
                    entry_price = 0.0
                elif pnl_pct >= take_profit_pct:
                    # 止盈卖出
                    commission = self._calc_sell_commission(price.close, position)
                    cash = self._sell(price.close, position, cash)
                    trades.append(BacktestTrade(
                        date=price.date, action="sell_take_profit",
                        price=price.close, quantity=position,
                        commission=commission,
                        reason=f"止盈({pnl_pct*100:.1f}%)"
                    ))
                    position = 0
                    entry_price = 0.0

            # 信号执行
            if action == "buy" and position == 0:
                buy_amount = cash * position_size_pct
                qty = int(buy_amount / price.close / 100) * 100  # 整手
                if qty >= 100:
                    cost = self._buy(price.close, qty, cash)
                    if cost > 0:
                        cash -= cost
                        position = qty
                        entry_price = price.close
                        trades.append(BacktestTrade(
                            date=price.date, action="buy",
                            price=price.close, quantity=qty,
                            commission=self._calc_buy_commission(price.close, qty),
                            reason="信号买入"
                        ))

            elif action == "sell" and position > 0:
                commission = self._calc_sell_commission(price.close, position)
                cash = self._sell(price.close, position, cash)
                trades.append(BacktestTrade(
                    date=price.date, action="sell",
                    price=price.close, quantity=position,
                    commission=commission,
                    reason="信号卖出"
                ))
                position = 0
                entry_price = 0.0

            # 记录权益
            equity = cash + position * price.close
            equity_curve.append({
                "date": date_str,
                "equity": round(equity, 2),
                "cash": round(cash, 2),
                "position_value": round(position * price.close, 2),
                "price": price.close,
            })

        # 期末清仓
        if position > 0 and prices:
            last_price = prices[-1].close
            commission = self._calc_sell_commission(last_price, position)
            cash = self._sell(last_price, position, cash)
            trades.append(BacktestTrade(
                date=prices[-1].date, action="sell_close",
                price=last_price, quantity=position,
                commission=commission,
                reason="期末清仓"
            ))

        # 计算指标
        final_capital = cash
        total_return = (final_capital - self.initial_capital) / self.initial_capital * 100

        # 年化收益
        days = len(prices)
        years = days / 252 if days > 0 else 1
        annual_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0

        # 最大回撤
        max_drawdown = self._calc_max_drawdown(equity_curve)

        # 夏普比率
        sharpe = self._calc_sharpe_ratio(equity_curve)

        # 胜率
        win_trades, loss_trades, profit_factor = self._calc_trade_stats(trades)
        total_trades_count = len([t for t in trades if t.action.startswith("sell")])
        win_rate = win_trades / total_trades_count * 100 if total_trades_count > 0 else 0

        # 基准收益（买入持有）
        benchmark_return = None
        if len(prices) >= 2:
            benchmark_return = (prices[-1].close - prices[0].close) / prices[0].close * 100

        result = BacktestResult(
            strategy_name=strategy_name,
            stock_code=stock_data.stock_code,
            stock_name=stock_data.stock_name,
            start_date=prices[0].date.strftime("%Y-%m-%d") if prices else "",
            end_date=prices[-1].date.strftime("%Y-%m-%d") if prices else "",
            initial_capital=self.initial_capital,
            final_capital=round(final_capital, 2),
            total_return_pct=round(total_return, 2),
            annual_return_pct=round(annual_return, 2),
            max_drawdown_pct=round(max_drawdown, 2),
            sharpe_ratio=round(sharpe, 2) if sharpe else None,
            win_rate=round(win_rate, 1),
            profit_factor=round(profit_factor, 2) if profit_factor else None,
            total_trades=total_trades_count,
            win_trades=win_trades,
            loss_trades=loss_trades,
            avg_holding_days=self._calc_avg_holding_days(trades),
            trades=trades,
            equity_curve=equity_curve,
            benchmark_return_pct=round(benchmark_return, 2) if benchmark_return is not None else None,
        )

        logger.info(
            f"[回测] 完成: {strategy_name}, "
            f"收益{total_return:.1f}%, 回撤{max_drawdown:.1f}%, "
            f"夏普{sharpe:.2f}" if sharpe else f"[回测] 完成: {strategy_name}, 收益{total_return:.1f}%, 回撤{max_drawdown:.1f}%"
        )
        return result

    def _buy(self, price: float, quantity: int, cash: float) -> float:
        """计算买入成本（含佣金）

        Args:
            price: 买入价格
            quantity: 买入数量
            cash: 可用现金

        Returns:
            总成本（含佣金），资金不足返回0
        """
        amount = price * quantity
        commission = max(amount * self.COMMISSION_RATE, self.COMMISSION_MIN)
        total_cost = amount + commission
        return total_cost if total_cost <= cash else 0

    def _sell(self, price: float, quantity: int, cash: float) -> float:
        """计算卖出收入（扣佣金和印花税）

        Args:
            price: 卖出价格
            quantity: 卖出数量
            cash: 当前现金

        Returns:
            卖出后现金余额
        """
        amount = price * quantity
        commission = max(amount * self.COMMISSION_RATE, self.COMMISSION_MIN)
        stamp_tax = amount * self.STAMP_TAX_RATE
        return cash + amount - commission - stamp_tax

    def _calc_buy_commission(self, price: float, quantity: int) -> float:
        """计算买入佣金

        Args:
            price: 买入价格
            quantity: 买入数量

        Returns:
            买入佣金
        """
        return max(price * quantity * self.COMMISSION_RATE, self.COMMISSION_MIN)

    def _calc_sell_commission(self, price: float, quantity: int) -> float:
        """计算卖出佣金（含印花税）

        Args:
            price: 卖出价格
            quantity: 卖出数量

        Returns:
            卖出佣金+印花税
        """
        amount = price * quantity
        return max(amount * self.COMMISSION_RATE, self.COMMISSION_MIN) + amount * self.STAMP_TAX_RATE

    @staticmethod
    def _calc_max_drawdown(equity_curve: List[Dict]) -> float:
        """计算最大回撤

        Args:
            equity_curve: 权益曲线数据

        Returns:
            最大回撤百分比
        """
        if not equity_curve:
            return 0.0
        peak = equity_curve[0]["equity"]
        max_dd = 0.0
        for point in equity_curve:
            if point["equity"] > peak:
                peak = point["equity"]
            dd = (peak - point["equity"]) / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return max_dd

    @staticmethod
    def _calc_sharpe_ratio(equity_curve: List[Dict], risk_free_rate: float = 0.03) -> Optional[float]:
        """计算夏普比率

        Args:
            equity_curve: 权益曲线数据
            risk_free_rate: 无风险利率，默认3%

        Returns:
            夏普比率，数据不足返回None
        """
        if len(equity_curve) < 2:
            return None
        import numpy as np
        returns: List[float] = []
        for i in range(1, len(equity_curve)):
            prev = equity_curve[i - 1]["equity"]
            curr = equity_curve[i]["equity"]
            if prev > 0:
                returns.append(curr / prev - 1)

        if not returns:
            return None

        daily_rf = risk_free_rate / 252
        excess_returns = [r - daily_rf for r in returns]
        mean_excess = float(np.mean(excess_returns))
        std_returns = float(np.std(returns))

        if std_returns == 0:
            return None

        return mean_excess / std_returns * (252 ** 0.5)

    @staticmethod
    def _calc_trade_stats(trades: List[BacktestTrade]) -> tuple:
        """计算交易统计（胜率、盈亏比）

        Args:
            trades: 交易记录列表

        Returns:
            (盈利次数, 亏损次数, 盈亏比)
        """
        sell_trades = [t for t in trades if t.action.startswith("sell")]
        if not sell_trades:
            return 0, 0, None

        # 配对买卖计算盈亏
        total_profit = 0.0
        total_loss = 0.0
        wins = 0
        losses = 0
        buy_trades = [t for t in trades if t.action == "buy"]

        for i, sell in enumerate(sell_trades):
            if i < len(buy_trades):
                pnl = (sell.price - buy_trades[i].price) * sell.quantity
                if pnl > 0:
                    total_profit += pnl
                    wins += 1
                else:
                    total_loss += abs(pnl)
                    losses += 1

        profit_factor = total_profit / total_loss if total_loss > 0 else None
        return wins, losses, profit_factor

    @staticmethod
    def _calc_avg_holding_days(trades: List[BacktestTrade]) -> float:
        """计算平均持仓天数

        Args:
            trades: 交易记录列表

        Returns:
            平均持仓天数
        """
        buy_dates = [t.date for t in trades if t.action == "buy"]
        sell_dates = [t.date for t in trades if t.action.startswith("sell")]

        if not buy_dates or not sell_dates:
            return 0.0

        holding_days: List[int] = []
        for i in range(min(len(buy_dates), len(sell_dates))):
            delta = (sell_dates[i] - buy_dates[i]).days
            holding_days.append(max(0, delta))

        return round(sum(holding_days) / len(holding_days), 1) if holding_days else 0.0

    def _empty_result(self, strategy_name: str, stock_data: StockData) -> BacktestResult:
        """生成空回测结果（无价格数据时使用）

        Args:
            strategy_name: 策略名称
            stock_data: 股票数据

        Returns:
            空的BacktestResult
        """
        return BacktestResult(
            strategy_name=strategy_name,
            stock_code=stock_data.stock_code,
            stock_name=stock_data.stock_name,
            start_date="", end_date="",
            initial_capital=self.initial_capital,
            final_capital=self.initial_capital,
            total_return_pct=0, annual_return_pct=0,
            max_drawdown_pct=0, sharpe_ratio=None,
            win_rate=0, profit_factor=None,
            total_trades=0, win_trades=0, loss_trades=0,
            avg_holding_days=0,
        )
