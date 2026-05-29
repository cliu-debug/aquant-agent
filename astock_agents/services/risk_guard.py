"""独立风控执行层 (RiskGuard)

独立于决策引擎和LLM，强制执行风控规则。
无论规则引擎或LLM输出什么信号，风控层都有权否决。

三层架构中的第三层：
  Layer 1: 规则引擎 (主决策, 90%场景)
  Layer 2: 自主规划 (LLM补充, 10%边缘场景)
  Layer 3: 风控强制层 (独立执行, 100%场景)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from astock_agents.models import Signal, RiskLevel, TradeProposal, RiskAssessment


class RiskGuardRule:
    """风控规则基类"""

    def __init__(self, name: str, description: str, severity: str = "block"):
        self.name = name
        self.description = description
        self.severity = severity

    def check(
        self,
        trade_proposal: TradeProposal,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """检查风控规则，返回None表示通过，返回字符串表示拒绝原因"""
        raise NotImplementedError


class MaxPositionRule(RiskGuardRule):
    """最大仓位规则 - 单只股票仓位不超过总资金的比例"""

    def __init__(self, max_position_pct: float = 30.0):
        super().__init__(
            name="max_position",
            description=f"单只股票仓位不超过{max_position_pct}%",
            severity="block",
        )
        self.max_position_pct = max_position_pct

    def check(self, trade_proposal: TradeProposal, context: Dict[str, Any]) -> Optional[str]:
        if trade_proposal.position_size_pct > self.max_position_pct:
            return (
                f"仓位{trade_proposal.position_size_pct:.1f}%超过上限"
                f"{self.max_position_pct}%，已自动调整"
            )
        return None


class StopLossRule(RiskGuardRule):
    """止损规则 - 止损价格必须设置且在合理范围内"""

    def __init__(self, max_loss_pct: float = 15.0):
        super().__init__(
            name="stop_loss",
            description=f"最大亏损不超过{max_loss_pct}%",
            severity="adjust",
        )
        self.max_loss_pct = max_loss_pct

    def check(self, trade_proposal: TradeProposal, context: Dict[str, Any]) -> Optional[str]:
        if not trade_proposal.stop_loss_price or not trade_proposal.entry_price:
            return "未设置止损价格，建议设置止损"

        entry = trade_proposal.entry_price
        stop = trade_proposal.stop_loss_price

        if trade_proposal.direction in (Signal.BUY, Signal.STRONG_BUY):
            loss_pct = (entry - stop) / entry * 100
            if loss_pct > self.max_loss_pct:
                new_stop = entry * (1 - self.max_loss_pct / 100)
                return (
                    f"止损幅度{loss_pct:.1f}%超过上限{self.max_loss_pct}%，"
                    f"已调整止损价至{new_stop:.2f}"
                )
        elif trade_proposal.direction in (Signal.SELL, Signal.STRONG_SELL):
            loss_pct = (stop - entry) / entry * 100
            if loss_pct > self.max_loss_pct:
                new_stop = entry * (1 + self.max_loss_pct / 100)
                return (
                    f"止损幅度{loss_pct:.1f}%超过上限{self.max_loss_pct}%，"
                    f"已调整止损价至{new_stop:.2f}"
                )

        return None


class ForbiddenStockRule(RiskGuardRule):
    """禁买清单规则 - ST股、退市风险股、停牌股禁止交易"""

    FORBIDDEN_PATTERNS = ["ST", "*ST", "退", "停牌"]

    def __init__(self):
        super().__init__(
            name="forbidden_stock",
            description="ST/退市/停牌股票禁止交易",
            severity="block",
        )

    def check(self, trade_proposal: TradeProposal, context: Dict[str, Any]) -> Optional[str]:
        stock_name = context.get("stock_name", "")
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern in stock_name:
                return f"股票{stock_name}包含禁买标识'{pattern}'，交易被否决"
        return None


class ConfidenceThresholdRule(RiskGuardRule):
    """置信度阈值规则 - 低置信度信号降级处理"""

    def __init__(self, min_confidence: int = 30, warn_confidence: int = 50):
        super().__init__(
            name="confidence_threshold",
            description=f"置信度低于{min_confidence}%否决，低于{warn_confidence}%降级",
            severity="adjust",
        )
        self.min_confidence = min_confidence
        self.warn_confidence = warn_confidence

    def check(self, trade_proposal: TradeProposal, context: Dict[str, Any]) -> Optional[str]:
        confidence = context.get("final_confidence", 50)

        if confidence < self.min_confidence:
            return (
                f"置信度{confidence}%低于最低阈值{self.min_confidence}%，"
                f"交易被否决"
            )

        if confidence < self.warn_confidence:
            return (
                f"置信度{confidence}%较低，信号已降级为持有"
            )

        return None


class VolatilityRule(RiskGuardRule):
    """波动率规则 - 高波动时降低仓位"""

    def __init__(self, high_volatility_threshold: float = 5.0):
        super().__init__(
            name="volatility_control",
            description=f"ATR>{high_volatility_threshold}%时仓位减半",
            severity="adjust",
        )
        self.high_volatility_threshold = high_volatility_threshold

    def check(self, trade_proposal: TradeProposal, context: Dict[str, Any]) -> Optional[str]:
        atr_pct = context.get("atr_pct", 0)
        if atr_pct > self.high_volatility_threshold:
            return (
                f"ATR波动率{atr_pct:.1f}%超过阈值{self.high_volatility_threshold}%，"
                f"建议仓位减半"
            )
        return None


class RiskGuard:
    """独立风控执行层

    核心原则：
    1. 独立于决策引擎和LLM运行
    2. 所有交易提案必须经过风控检查
    3. severity="block"的规则可以否决交易
    4. severity="adjust"的规则可以调整交易参数
    5. 风控决策全链路记录，满足合规审计要求
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.rules: List[RiskGuardRule] = []
        self._audit_log: List[Dict[str, Any]] = []
        self._db = None

        # 注册默认风控规则
        self._register_default_rules()

        logger.info(f"[风控层] 初始化完成，注册{len(self.rules)}条规则")

    def _get_db(self):
        """懒加载数据库实例"""
        if self._db is None:
            try:
                from astock_agents.db.database import Database
                self._db = Database()
            except Exception as e:
                logger.warning(f"[风控层] 数据库初始化失败，审计日志仅存内存: {e}")
        return self._db

    def _register_default_rules(self) -> None:
        """注册默认风控规则"""
        max_pos = self.config.get("max_position_pct", 30.0)
        max_loss = self.config.get("max_loss_pct", 15.0)
        min_conf = self.config.get("min_confidence", 30)
        warn_conf = self.config.get("warn_confidence", 50)
        high_vol = self.config.get("high_volatility_threshold", 5.0)

        self.rules = [
            ForbiddenStockRule(),
            MaxPositionRule(max_pos),
            StopLossRule(max_loss),
            ConfidenceThresholdRule(min_conf, warn_conf),
            VolatilityRule(high_vol),
        ]

    def enforce(
        self,
        trade_proposal: TradeProposal,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行风控检查

        Args:
            trade_proposal: 交易提案
            context: 上下文信息（stock_name, final_confidence, atr_pct等）

        Returns:
            风控结果字典：
            - approved: bool - 是否批准
            - adjusted_proposal: TradeProposal - 调整后的交易提案
            - block_reasons: List[str] - 否决原因
            - adjustments: List[str] - 调整记录
            - audit_log: Dict - 审计日志
        """
        logger.info("[风控层] 开始执行风控检查")

        block_reasons: List[str] = []
        adjustments: List[str] = []
        adjusted = False

        # 复制交易提案用于调整
        proposal_dict = trade_proposal.model_dump()

        for rule in self.rules:
            reason = rule.check(trade_proposal, context)

            if reason is None:
                continue

            if rule.severity == "block":
                block_reasons.append(f"[{rule.name}] {reason}")
                logger.warning(f"[风控层] 规则{rule.name}否决交易: {reason}")
            elif rule.severity == "adjust":
                adjustments.append(f"[{rule.name}] {reason}")
                logger.info(f"[风控层] 规则{rule.name}调整交易: {reason}")
                adjusted = True

                # 执行自动调整
                if rule.name == "max_position":
                    max_pct = self.config.get("max_position_pct", 30.0)
                    proposal_dict["position_size_pct"] = min(
                        proposal_dict["position_size_pct"], max_pct
                    )

                if rule.name == "confidence_threshold":
                    confidence = context.get("final_confidence", 50)
                    min_conf = self.config.get("min_confidence", 30)
                    if confidence < min_conf:
                        proposal_dict["direction"] = Signal.HOLD.value
                    elif confidence < self.config.get("warn_confidence", 50):
                        proposal_dict["direction"] = Signal.HOLD.value

                if rule.name == "volatility_control":
                    proposal_dict["position_size_pct"] = (
                        proposal_dict["position_size_pct"] / 2
                    )

        # 构建调整后的交易提案
        try:
            if "direction" in proposal_dict and isinstance(proposal_dict["direction"], str):
                proposal_dict["direction"] = Signal(proposal_dict["direction"])
            adjusted_proposal = TradeProposal(**proposal_dict)
        except Exception:
            adjusted_proposal = trade_proposal

        # 判断是否批准
        approved = len(block_reasons) == 0

        # 记录审计日志
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "stock_code": context.get("stock_code", ""),
            "original_direction": trade_proposal.direction.value if hasattr(trade_proposal.direction, "value") else str(trade_proposal.direction),
            "original_position": trade_proposal.position_size_pct,
            "adjusted_direction": adjusted_proposal.direction.value if hasattr(adjusted_proposal.direction, "value") else str(adjusted_proposal.direction),
            "adjusted_position": adjusted_proposal.position_size_pct,
            "approved": approved,
            "block_reasons": block_reasons,
            "adjustments": adjustments,
        }
        self._audit_log.append(audit_entry)

        # 持久化审计日志到数据库
        try:
            db = self._get_db()
            if db:
                db.save_audit_log(
                    log_type="risk_guard",
                    action="enforce",
                    stock_code=context.get("stock_code", ""),
                    details=audit_entry,
                )
        except Exception as e:
            logger.warning(f"[风控层] 审计日志持久化失败: {e}")

        result = {
            "approved": approved,
            "adjusted_proposal": adjusted_proposal,
            "block_reasons": block_reasons,
            "adjustments": adjustments,
            "audit_entry": audit_entry,
        }

        if approved:
            if adjustments:
                logger.info(f"[风控层] 交易批准（有调整）: {len(adjustments)}项调整")
            else:
                logger.info("[风控层] 交易批准（无调整）")
        else:
            logger.warning(f"[风控层] 交易被否决: {block_reasons}")

        return result

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取审计日志

        优先从数据库读取（持久化），数据库不可用时降级到内存。

        Args:
            limit: 返回条数上限

        Returns:
            审计日志列表
        """
        try:
            db = self._get_db()
            if db:
                db_logs = db.get_audit_logs(log_type="risk_guard", limit=limit)
                if db_logs:
                    return db_logs
        except Exception:
            pass
        return self._audit_log[-limit:]
