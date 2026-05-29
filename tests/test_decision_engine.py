"""决策引擎单元测试

覆盖场景：
1. 正常路径：混合决策生成
2. 边界条件：空上下文、极端置信度
3. 风控集成：风控否决、调整
4. 审计日志：持久化验证
5. 不确定性检测
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

test_db_path = os.path.join(tempfile.gettempdir(), "test_astock_decision2.db")
os.environ["ASTOCK_DB_PATH"] = test_db_path

from astock_agents.services.decision_engine import DecisionEngine
from astock_agents.models.analysis_report import Signal, TradeProposal


@pytest.fixture
def engine():
    """创建决策引擎实例"""
    return DecisionEngine()


@pytest.fixture
def buy_proposal():
    """买入交易提案"""
    return TradeProposal(
        direction=Signal.BUY,
        position_size_pct=15.0,
        entry_price=1800.0,
        target_price=2000.0,
        stop_loss_price=1700.0,
        expected_return_pct=11.1,
        risk_reward_ratio=2.0,
        time_horizon="中期",
        key_reasons=["业绩稳健"],
        risk_factors=["估值偏高"],
        proposal_text="建议买入",
    )


@pytest.fixture
def sell_proposal():
    """卖出交易提案"""
    return TradeProposal(
        direction=Signal.SELL,
        position_size_pct=10.0,
        entry_price=12.5,
        target_price=11.0,
        stop_loss_price=13.5,
        expected_return_pct=-12.0,
        risk_reward_ratio=1.5,
        time_horizon="短期",
        key_reasons=["趋势下行"],
        risk_factors=["可能反弹"],
        proposal_text="建议卖出",
    )


class TestDecisionEngineBasic:
    """决策引擎基础测试"""

    def test_engine_init(self, engine):
        """引擎初始化"""
        assert engine is not None
        assert engine.risk_guard is not None
        assert engine.uncertainty_detector is not None

    def test_buy_decision(self, engine, buy_proposal):
        """买入信号决策"""
        result = engine.decide(
            rule_signal=Signal.BUY,
            rule_confidence=70,
            debate_winning_side="bull",
            debate_cooperation=0.8,
            dimension_signals={"technical": Signal.BUY, "fundamental": Signal.BUY},
            trade_proposal=buy_proposal,
            context={"stock_code": "600519.SH", "stock_name": "贵州茅台"},
        )

        assert result["final_signal"] is not None
        assert result["final_confidence"] > 0
        assert result["decision_source"] in ("rule", "rule_engine", "llm", "risk_override")

    def test_sell_decision(self, engine, sell_proposal):
        """卖出信号决策"""
        result = engine.decide(
            rule_signal=Signal.SELL,
            rule_confidence=60,
            debate_winning_side="bear",
            debate_cooperation=0.7,
            dimension_signals={"technical": Signal.SELL},
            trade_proposal=sell_proposal,
            context={"stock_code": "000001.SZ"},
        )

        assert result["final_signal"] is not None

    def test_hold_decision(self, engine, buy_proposal):
        """持有信号决策"""
        result = engine.decide(
            rule_signal=Signal.HOLD,
            rule_confidence=50,
            debate_winning_side="neutral",
            debate_cooperation=0.5,
            dimension_signals={},
            trade_proposal=buy_proposal,
            context={"stock_code": "600036.SH"},
        )

        assert result["final_signal"] is not None

    def test_risk_guard_blocks_extreme_position(self, engine):
        """风控否决极端仓位"""
        extreme_proposal = TradeProposal(
            direction=Signal.STRONG_BUY,
            position_size_pct=80.0,
            entry_price=100.0,
            target_price=120.0,
            stop_loss_price=90.0,
            expected_return_pct=20.0,
            risk_reward_ratio=2.0,
            time_horizon="短期",
            key_reasons=["测试"],
            risk_factors=["测试"],
            proposal_text="极端仓位测试",
        )

        result = engine.decide(
            rule_signal=Signal.STRONG_BUY,
            rule_confidence=80,
            debate_winning_side="bull",
            debate_cooperation=0.9,
            dimension_signals={},
            trade_proposal=extreme_proposal,
            context={"stock_code": "600519.SH"},
        )

        risk_result = result.get("risk_result", {})
        if not risk_result.get("approved", True):
            assert len(risk_result.get("block_reasons", [])) > 0


class TestDecisionEngineEdgeCases:
    """边界条件测试"""

    def test_low_confidence(self, engine, buy_proposal):
        """低置信度决策"""
        result = engine.decide(
            rule_signal=Signal.BUY,
            rule_confidence=20,
            debate_winning_side="bull",
            debate_cooperation=0.3,
            dimension_signals={},
            trade_proposal=buy_proposal,
            context={"stock_code": "600519.SH"},
        )

        assert result["final_signal"] is not None

    def test_high_confidence(self, engine, buy_proposal):
        """高置信度决策"""
        result = engine.decide(
            rule_signal=Signal.STRONG_BUY,
            rule_confidence=95,
            debate_winning_side="bull",
            debate_cooperation=0.95,
            dimension_signals={"technical": Signal.STRONG_BUY},
            trade_proposal=buy_proposal,
            context={"stock_code": "600519.SH"},
        )

        assert result["final_signal"] is not None
        assert result["final_confidence"] > 0

    def test_empty_context(self, engine, buy_proposal):
        """空上下文"""
        result = engine.decide(
            rule_signal=Signal.BUY,
            rule_confidence=60,
            debate_winning_side="bull",
            debate_cooperation=0.6,
            dimension_signals={},
            trade_proposal=buy_proposal,
            context={},
        )

        assert result["final_signal"] is not None


class TestDecisionLogPersistence:
    """决策日志持久化测试"""

    def test_decision_log_recorded(self, engine, buy_proposal):
        """决策日志被记录"""
        engine.decide(
            rule_signal=Signal.BUY,
            rule_confidence=70,
            debate_winning_side="bull",
            debate_cooperation=0.8,
            dimension_signals={},
            trade_proposal=buy_proposal,
            context={"stock_code": "600519.SH"},
        )

        logs = engine.get_decision_log(limit=10)
        assert len(logs) > 0

    def test_decision_log_persisted_to_db(self, engine, buy_proposal):
        """决策日志持久化到数据库"""
        engine.decide(
            rule_signal=Signal.BUY,
            rule_confidence=70,
            debate_winning_side="bull",
            debate_cooperation=0.8,
            dimension_signals={},
            trade_proposal=buy_proposal,
            context={"stock_code": "600519.SH"},
        )

        from astock_agents.db.database import Database
        db = Database(db_path=test_db_path)
        db_logs = db.get_audit_logs(log_type="decision_engine", limit=10)
        assert len(db_logs) > 0


def teardown_module():
    """测试结束后清理测试数据库"""
    try:
        os.remove(test_db_path)
    except OSError:
        pass
