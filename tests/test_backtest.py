"""回测引擎单元测试"""

import sys
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from astock_agents.models.stock_data import StockData, StockPrice
from astock_agents.services.backtest import BacktestEngine, BacktestResult, BacktestTrade


def _make_stock_data(code: str = "600519.SH", name: str = "贵州茅台", days: int = 60) -> StockData:
    """构造测试用股票数据，模拟一个先涨后跌的走势"""
    prices = []
    base_price = 100.0
    for i in range(days):
        # 前30天上涨，后30天下跌
        if i < 30:
            close = base_price + i * 1.0
        else:
            close = base_price + 29.0 - (i - 30) * 1.0
        prices.append(StockPrice(
            date=datetime(2024, 1, 1 + i) if i < 31 else datetime(2024, 2, i - 30),
            open=close - 0.5,
            high=close + 1.0,
            low=close - 1.0,
            close=close,
            volume=1000000,
        ))
    return StockData(
        stock_code=code,
        stock_name=name,
        prices=prices,
    )


def _make_signals() -> list:
    """构造测试用交易信号：在低点买入，高点卖出"""
    return [
        {"date": "2024-01-05", "action": "buy"},
        {"date": "2024-02-02", "action": "sell"},
    ]


# ==================== 正常路径测试 ====================

def test_backtest_basic_run():
    """正常路径：基本回测执行"""
    engine = BacktestEngine(initial_capital=1000000.0)
    stock_data = _make_stock_data()
    signals = _make_signals()

    result = engine.run(
        stock_data=stock_data,
        signals=signals,
        strategy_name="测试策略",
    )

    assert isinstance(result, BacktestResult)
    assert result.strategy_name == "测试策略"
    assert result.stock_code == "600519.SH"
    assert result.stock_name == "贵州茅台"
    assert result.start_date != ""
    assert result.end_date != ""
    assert result.initial_capital == 1000000.0
    assert result.total_trades > 0
    assert len(result.trades) > 0
    assert len(result.equity_curve) == 60  # 60天数据


def test_backtest_profitable_strategy():
    """正常路径：盈利策略 - 低价买入高价卖出"""
    engine = BacktestEngine(initial_capital=1000000.0)
    stock_data = _make_stock_data()
    signals = _make_signals()

    result = engine.run(stock_data=stock_data, signals=signals)

    # 在上涨阶段买入，下跌前卖出，应该盈利
    assert result.final_capital > result.initial_capital
    assert result.total_return_pct > 0
    assert result.benchmark_return_pct is not None


def test_backtest_benchmark_return():
    """正常路径：基准收益率计算（买入持有）"""
    engine = BacktestEngine(initial_capital=1000000.0)
    stock_data = _make_stock_data()
    signals = _make_signals()

    result = engine.run(stock_data=stock_data, signals=signals)

    # 基准收益 = (末价 - 首价) / 首价 * 100
    first_price = stock_data.prices[0].close
    last_price = stock_data.prices[-1].close
    expected_benchmark = (last_price - first_price) / first_price * 100
    assert abs(result.benchmark_return_pct - round(expected_benchmark, 2)) < 0.1


def test_backtest_equity_curve_length():
    """正常路径：权益曲线长度等于交易日数"""
    engine = BacktestEngine(initial_capital=1000000.0)
    stock_data = _make_stock_data(days=30)
    signals = [{"date": "2024-01-05", "action": "buy"}]

    result = engine.run(stock_data=stock_data, signals=signals)

    assert len(result.equity_curve) == 30
    # 每个权益点包含必要字段
    for point in result.equity_curve:
        assert "date" in point
        assert "equity" in point
        assert "cash" in point
        assert "position_value" in point
        assert "price" in point


def test_backtest_commission_deduction():
    """正常路径：交易佣金扣除"""
    engine = BacktestEngine(initial_capital=1000000.0)
    stock_data = _make_stock_data()
    signals = _make_signals()

    result = engine.run(stock_data=stock_data, signals=signals)

    # 每笔交易都有佣金
    for trade in result.trades:
        assert trade.commission >= 5.0  # 最低佣金5元


# ==================== 边界条件测试 ====================

def test_backtest_empty_prices():
    """边界条件：无价格数据"""
    engine = BacktestEngine(initial_capital=1000000.0)
    stock_data = StockData(stock_code="000001.SZ", stock_name="平安银行", prices=[])
    signals = _make_signals()

    result = engine.run(stock_data=stock_data, signals=signals)

    assert result.total_return_pct == 0
    assert result.final_capital == result.initial_capital
    assert result.total_trades == 0


def test_backtest_no_signals():
    """边界条件：无交易信号 - 期末无持仓"""
    engine = BacktestEngine(initial_capital=1000000.0)
    stock_data = _make_stock_data()
    signals = []

    result = engine.run(stock_data=stock_data, signals=signals)

    # 无信号，不交易，资金不变
    assert result.total_trades == 0
    assert result.final_capital == result.initial_capital
    assert result.total_return_pct == 0


def test_backtest_buy_only_signal():
    """边界条件：只有买入信号，未触发止损止盈时期末自动清仓"""
    # 构造一个波动较小的股票，避免触发止损止盈
    prices = []
    for i in range(20):
        close = 100.0 + (i % 3) * 0.5  # 小幅波动
        prices.append(StockPrice(
            date=datetime(2024, 1, 1 + i),
            open=close - 0.1,
            high=close + 0.2,
            low=close - 0.2,
            close=close,
            volume=1000000,
        ))
    stock_data = StockData(stock_code="000001.SZ", stock_name="测试股票", prices=prices)
    signals = [{"date": "2024-01-02", "action": "buy"}]

    engine = BacktestEngine(initial_capital=1000000.0)
    result = engine.run(
        stock_data=stock_data,
        signals=signals,
        stop_loss_pct=0.5,  # 止损设大，不触发
        take_profit_pct=0.5,  # 止盈设大，不触发
    )

    # 应有买入和期末清仓两笔交易
    assert len(result.trades) >= 2
    actions = [t.action for t in result.trades]
    assert "buy" in actions
    assert "sell_close" in actions


def test_backtest_sell_without_position():
    """边界条件：无持仓时卖出信号被忽略"""
    engine = BacktestEngine(initial_capital=1000000.0)
    stock_data = _make_stock_data()
    signals = [{"date": "2024-01-05", "action": "sell"}]

    result = engine.run(stock_data=stock_data, signals=signals)

    # 无持仓卖出无效
    assert result.total_trades == 0


def test_backtest_stop_loss():
    """边界条件：止损触发"""
    # 构造一个持续下跌的股票
    prices = []
    for i in range(20):
        close = 100.0 - i * 3  # 每天跌3元
        prices.append(StockPrice(
            date=datetime(2024, 1, 1 + i),
            open=close + 0.5,
            high=close + 1.0,
            low=close - 1.0,
            close=close,
            volume=1000000,
        ))
    stock_data = StockData(stock_code="000001.SZ", stock_name="测试股票", prices=prices)
    signals = [{"date": "2024-01-02", "action": "buy"}]

    engine = BacktestEngine(initial_capital=1000000.0)
    result = engine.run(
        stock_data=stock_data,
        signals=signals,
        stop_loss_pct=0.07,  # 7%止损
        take_profit_pct=0.5,  # 止盈设高，不会触发
    )

    # 应触发止损
    actions = [t.action for t in result.trades]
    assert "sell_stop_loss" in actions


def test_backtest_take_profit():
    """边界条件：止盈触发"""
    # 构造一个持续上涨的股票
    prices = []
    for i in range(20):
        close = 100.0 + i * 2  # 每天涨2元
        prices.append(StockPrice(
            date=datetime(2024, 1, 1 + i),
            open=close - 0.5,
            high=close + 1.0,
            low=close - 1.0,
            close=close,
            volume=1000000,
        ))
    stock_data = StockData(stock_code="000001.SZ", stock_name="测试股票", prices=prices)
    signals = [{"date": "2024-01-02", "action": "buy"}]

    engine = BacktestEngine(initial_capital=1000000.0)
    result = engine.run(
        stock_data=stock_data,
        signals=signals,
        stop_loss_pct=0.5,  # 止损设大，不会触发
        take_profit_pct=0.15,  # 15%止盈
    )

    # 应触发止盈
    actions = [t.action for t in result.trades]
    assert "sell_take_profit" in actions


def test_backtest_max_drawdown():
    """边界条件：最大回撤计算"""
    engine = BacktestEngine(initial_capital=1000000.0)
    stock_data = _make_stock_data()
    signals = _make_signals()

    result = engine.run(stock_data=stock_data, signals=signals)

    # 最大回撤应为非负数
    assert result.max_drawdown_pct >= 0


def test_backtest_position_size():
    """边界条件：不同仓位比例"""
    engine = BacktestEngine(initial_capital=1000000.0)
    stock_data = _make_stock_data()
    signals = _make_signals()

    result_small = engine.run(stock_data=stock_data, signals=signals, position_size_pct=0.1)
    result_large = engine.run(stock_data=stock_data, signals=signals, position_size_pct=0.5)

    # 仓位比例不同，买入数量不同
    buy_small = [t for t in result_small.trades if t.action == "buy"]
    buy_large = [t for t in result_large.trades if t.action == "buy"]
    if buy_small and buy_large:
        assert buy_large[0].quantity >= buy_small[0].quantity


# ==================== 异常路径测试 ====================

def test_backtest_insufficient_funds():
    """异常路径：资金不足无法买入"""
    engine = BacktestEngine(initial_capital=100.0)  # 只有100元
    stock_data = _make_stock_data()  # 股价约100元
    signals = [{"date": "2024-01-05", "action": "buy"}]

    result = engine.run(stock_data=stock_data, signals=signals)

    # 资金不足，买不了一手（100股）
    assert result.total_trades == 0


def test_backtest_invalid_signal_action_ignored():
    """异常路径：无效信号动作被忽略（不产生交易）"""
    engine = BacktestEngine(initial_capital=1000000.0)
    stock_data = _make_stock_data()
    signals = [
        {"date": "2024-01-05", "action": "buy"},
        {"date": "2024-01-10", "action": "hold"},  # 无效动作
    ]

    result = engine.run(stock_data=stock_data, signals=signals)

    # 只有买入信号生效，hold被忽略
    buy_trades = [t for t in result.trades if t.action == "buy"]
    assert len(buy_trades) == 1


def test_backtest_result_serializable():
    """异常路径：回测结果可序列化为字典"""
    engine = BacktestEngine(initial_capital=1000000.0)
    stock_data = _make_stock_data()
    signals = _make_signals()

    result = engine.run(stock_data=stock_data, signals=signals)

    # 转为字典不应抛出异常
    result_dict = asdict(result)
    assert isinstance(result_dict, dict)
    assert "strategy_name" in result_dict
    assert "trades" in result_dict
    assert "equity_curve" in result_dict


# ==================== 辅助方法测试 ====================

def test_calc_max_drawdown_static():
    """测试最大回撤计算"""
    equity_curve = [
        {"equity": 100},
        {"equity": 110},
        {"equity": 105},
        {"equity": 95},
        {"equity": 100},
    ]
    dd = BacktestEngine._calc_max_drawdown(equity_curve)
    # 峰值110，最低95，回撤(110-95)/110 = 13.6%
    assert abs(dd - 13.64) < 0.1


def test_calc_max_drawdown_empty():
    """测试空权益曲线的最大回撤"""
    assert BacktestEngine._calc_max_drawdown([]) == 0.0


def test_calc_avg_holding_days():
    """测试平均持仓天数计算"""
    trades = [
        BacktestTrade(date=datetime(2024, 1, 1), action="buy", price=100, quantity=100),
        BacktestTrade(date=datetime(2024, 1, 10), action="sell", price=110, quantity=100),
        BacktestTrade(date=datetime(2024, 2, 1), action="buy", price=105, quantity=100),
        BacktestTrade(date=datetime(2024, 2, 20), action="sell", price=115, quantity=100),
    ]
    avg_days = BacktestEngine._calc_avg_holding_days(trades)
    # (9 + 19) / 2 = 14.0
    assert avg_days == 14.0


def test_calc_avg_holding_days_no_trades():
    """测试无交易时的平均持仓天数"""
    assert BacktestEngine._calc_avg_holding_days([]) == 0.0


if __name__ == "__main__":
    # 运行所有测试
    import traceback
    test_funcs = [
        test_backtest_basic_run,
        test_backtest_profitable_strategy,
        test_backtest_benchmark_return,
        test_backtest_equity_curve_length,
        test_backtest_commission_deduction,
        test_backtest_empty_prices,
        test_backtest_no_signals,
        test_backtest_buy_only_signal,
        test_backtest_sell_without_position,
        test_backtest_stop_loss,
        test_backtest_take_profit,
        test_backtest_max_drawdown,
        test_backtest_position_size,
        test_backtest_insufficient_funds,
        test_backtest_invalid_signal_action_ignored,
        test_backtest_result_serializable,
        test_calc_max_drawdown_static,
        test_calc_max_drawdown_empty,
        test_calc_avg_holding_days,
        test_calc_avg_holding_days_no_trades,
    ]

    passed = 0
    failed = 0
    for func in test_funcs:
        try:
            func()
            print(f"  PASS: {func.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {func.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n结果: {passed} 通过, {failed} 失败, 共 {len(test_funcs)} 个测试")
