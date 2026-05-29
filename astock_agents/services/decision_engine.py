"""混合决策引擎 (DecisionEngine)

三层决策架构的核心调度器：
  Layer 1: 规则引擎 (主决策, 90%场景) - 快速、确定、可审计
  Layer 2: 自主规划 (LLM补充, 10%边缘场景) - 灵活、深度、有条件触发
  Layer 3: 风控强制层 (独立执行, 100%场景) - 安全底线、不可绕过

决策流程：
  1. 规则引擎先执行，生成初始信号和置信度
  2. 判断是否需要LLM介入（不确定检测）
  3. LLM仅在规则不确定时补充分析
  4. 风控层独立检查，有权否决任何交易
  5. 全链路记录决策日志
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from astock_agents.models import Signal, TradeProposal, RiskAssessment, RiskLevel
from astock_agents.services.risk_guard import RiskGuard


class UncertaintyDetector:
    """不确定性检测器 - 判断规则引擎输出是否需要LLM补充"""

    @staticmethod
    def detect(
        signal: Signal,
        confidence: int,
        debate_winning_side: str,
        debate_cooperation: float,
        dimension_signals: Dict[str, Signal],
    ) -> Dict[str, Any]:
        """检测规则引擎输出的不确定性

        触发LLM补充的条件：
        1. 置信度在40-60%之间（模糊区间）
        2. 多空辩论平局
        3. 各维度信号严重分歧
        4. 合作度评分低于0.3

        Args:
            signal: 规则引擎生成的信号
            confidence: 置信度
            debate_winning_side: 辩论获胜方
            debate_cooperation: 合作度评分
            dimension_signals: 各维度信号

        Returns:
            不确定性检测结果
        """
        reasons: List[str] = []
        need_llm = False
        uncertainty_level = "low"

        # 检查1：置信度模糊区间
        if 40 <= confidence <= 60:
            reasons.append(f"置信度{confidence}%处于模糊区间(40-60%)")
            need_llm = True
            uncertainty_level = "medium"

        # 检查2：辩论平局
        if debate_winning_side == "neutral":
            reasons.append("多空辩论平局，无明确方向")
            need_llm = True
            uncertainty_level = "high"

        # 检查3：维度信号分歧
        signal_values = []
        for dim, sig in dimension_signals.items():
            sig_str = sig.value if hasattr(sig, "value") else str(sig)
            signal_values.append(sig_str)

        buy_count = sum(1 for s in signal_values if s in ("强烈买入", "买入"))
        sell_count = sum(1 for s in signal_values if s in ("强烈卖出", "卖出"))
        hold_count = sum(1 for s in signal_values if s == "持有")

        if buy_count > 0 and sell_count > 0 and abs(buy_count - sell_count) <= 1:
            reasons.append(
                f"维度信号分歧严重: 买入{buy_count}个, 卖出{sell_count}个, 持有{hold_count}个"
            )
            need_llm = True
            uncertainty_level = "high"

        # 检查4：合作度低
        if debate_cooperation < 0.3:
            reasons.append(f"合作度评分{debate_cooperation:.2f}过低，辩论质量存疑")
            need_llm = True
            if uncertainty_level != "high":
                uncertainty_level = "medium"

        return {
            "need_llm": need_llm,
            "uncertainty_level": uncertainty_level,
            "reasons": reasons,
        }


class DecisionEngine:
    """混合决策引擎

    规则为主(70%) + 自主规划补充(30%) + 风控强制层

    使用方式：
      engine = DecisionEngine(config)
      result = engine.decide(
          rule_signal=Signal.BUY,
          rule_confidence=65,
          debate_winning_side="bull",
          debate_cooperation=0.8,
          dimension_signals={...},
          trade_proposal=...,
          llm_available=True,
          context={...},
      )
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.risk_guard = RiskGuard(config=self.config.get("risk_guard", {}))
        self.uncertainty_detector = UncertaintyDetector()
        self._decision_log: List[Dict[str, Any]] = []
        self._db = None

        logger.info("[决策引擎] 混合架构初始化完成 (规则为主 + LLM补充 + 风控强制)")

    def _get_db(self):
        """懒加载数据库实例"""
        if self._db is None:
            try:
                from astock_agents.db.database import Database
                self._db = Database()
            except Exception as e:
                logger.warning(f"[决策引擎] 数据库初始化失败，决策日志仅存内存: {e}")
        return self._db

    def decide(
        self,
        rule_signal: Signal,
        rule_confidence: int,
        debate_winning_side: str,
        debate_cooperation: float,
        dimension_signals: Dict[str, Signal],
        trade_proposal: TradeProposal,
        llm_available: bool = False,
        llm_rationale: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行混合决策

        Args:
            rule_signal: 规则引擎生成的信号
            rule_confidence: 规则引擎置信度
            debate_winning_side: 辩论获胜方(bull/bear/neutral)
            debate_cooperation: 合作度评分(0-1)
            dimension_signals: 各维度信号字典
            trade_proposal: 交易提案
            llm_available: LLM是否可用
            llm_rationale: LLM生成的决策逻辑(如果有)
            context: 上下文信息

        Returns:
            决策结果字典
        """
        context = context or {}
        decision_start = datetime.now()

        logger.info(
            f"[决策引擎] 开始决策: 规则信号={rule_signal.value}, "
            f"置信度={rule_confidence}%, 辩论方={debate_winning_side}"
        )

        # ========== Layer 1: 规则引擎决策 (主决策) ==========
        final_signal = rule_signal
        final_confidence = rule_confidence
        decision_source = "rule_engine"
        llm_triggered = False

        # ========== Layer 2: 不确定性检测 + LLM补充 ==========
        uncertainty = self.uncertainty_detector.detect(
            signal=rule_signal,
            confidence=rule_confidence,
            debate_winning_side=debate_winning_side,
            debate_cooperation=debate_cooperation,
            dimension_signals=dimension_signals,
        )

        if uncertainty["need_llm"] and llm_available and llm_rationale:
            llm_triggered = True
            decision_source = "hybrid_rule_llm"

            logger.info(
                f"[决策引擎] LLM补充触发: {uncertainty['reasons']}"
            )

            # LLM补充逻辑：LLM可以调整信号，但不能完全推翻规则引擎
            if uncertainty["uncertainty_level"] == "high":
                # 高不确定性：LLM有较大调整权
                final_confidence = max(20, rule_confidence - 10)
                if llm_rationale and "谨慎" in llm_rationale:
                    final_signal = Signal.HOLD
                    logger.info("[决策引擎] LLM建议谨慎，信号降级为持有")
            else:
                # 中等不确定性：LLM仅微调置信度
                final_confidence = max(30, rule_confidence - 5)
        elif uncertainty["need_llm"] and not llm_available:
            # 需要LLM但不可用：降低置信度，信号降级
            if rule_confidence < 50:
                final_signal = Signal.HOLD
                final_confidence = max(20, rule_confidence - 15)
                decision_source = "rule_engine_downgraded"
                logger.info(
                    "[决策引擎] 需要LLM补充但不可用，信号降级为持有"
                )

        # ========== Layer 3: 风控强制层 ==========
        risk_context = {
            "stock_code": context.get("stock_code", ""),
            "stock_name": context.get("stock_name", ""),
            "final_confidence": final_confidence,
            "atr_pct": context.get("atr_pct", 0),
        }

        risk_result = self.risk_guard.enforce(trade_proposal, risk_context)

        if not risk_result["approved"]:
            final_signal = Signal.HOLD
            final_confidence = 0
            decision_source = "risk_guard_blocked"
            logger.warning(
                f"[决策引擎] 交易被风控层否决: {risk_result['block_reasons']}"
            )

        adjusted_proposal = risk_result["adjusted_proposal"]

        # 如果风控层调整了方向，更新最终信号
        if hasattr(adjusted_proposal, "direction"):
            adjusted_dir = adjusted_proposal.direction
            adjusted_dir_str = adjusted_dir.value if hasattr(adjusted_dir, "value") else str(adjusted_dir)
            if adjusted_dir_str == "持有" and final_signal != Signal.HOLD:
                final_signal = Signal.HOLD
                decision_source = "risk_guard_adjusted"

        # ========== 记录决策日志 ==========
        decision_log = {
            "timestamp": decision_start.isoformat(),
            "stock_code": context.get("stock_code", ""),
            "layer1_rule_signal": rule_signal.value,
            "layer1_rule_confidence": rule_confidence,
            "layer2_uncertainty": uncertainty,
            "layer2_llm_triggered": llm_triggered,
            "layer3_risk_approved": risk_result["approved"],
            "layer3_risk_adjustments": risk_result["adjustments"],
            "layer3_risk_blocks": risk_result["block_reasons"],
            "final_signal": final_signal.value,
            "final_confidence": final_confidence,
            "decision_source": decision_source,
        }
        self._decision_log.append(decision_log)

        # 持久化决策日志到数据库
        try:
            db = self._get_db()
            if db:
                db.save_audit_log(
                    log_type="decision_engine",
                    action="decide",
                    stock_code=context.get("stock_code", ""),
                    details=decision_log,
                )
        except Exception as e:
            logger.warning(f"[决策引擎] 决策日志持久化失败: {e}")

        logger.info(
            f"[决策引擎] 决策完成: 最终信号={final_signal.value}, "
            f"置信度={final_confidence}%, 来源={decision_source}"
        )

        return {
            "final_signal": final_signal,
            "final_confidence": final_confidence,
            "decision_source": decision_source,
            "uncertainty": uncertainty,
            "llm_triggered": llm_triggered,
            "risk_result": risk_result,
            "adjusted_proposal": adjusted_proposal,
            "decision_log": decision_log,
        }

    def get_decision_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取决策日志

        优先从数据库读取（持久化），数据库不可用时降级到内存。

        Args:
            limit: 返回条数上限

        Returns:
            决策日志列表
        """
        try:
            db = self._get_db()
            if db:
                db_logs = db.get_audit_logs(log_type="decision_engine", limit=limit)
                if db_logs:
                    return db_logs
        except Exception:
            pass
        return self._decision_log[-limit:]
