"""合规审查模块 - 金融智能体合规边界守护

核心能力：
1. 免责声明注入 - 所有API响应自动附加免责声明
2. 荐股风险标注 - 信号输出时附加风险提示
3. 合规内容审查 - 检查分析内容是否涉及法律风险
4. 投资建议分级 - 区分"信息展示"和"投资建议"
5. 用户风险告知 - 首次使用风险确认
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger


DISCLAIMER_TEXT = (
    "本系统提供的分析结果仅供参考，不构成任何投资建议。"
    "股市有风险，投资需谨慎。使用本系统进行投资决策造成的任何损失，开发者不承担任何责任。"
)

SIGNAL_RISK_NOTICES = {
    "强烈买入": (
        "⚠️ 风险提示：本信号为系统分析结果，不构成投资建议。"
        "强烈买入信号不代表一定上涨，请结合自身风险承受能力谨慎决策。"
    ),
    "买入": (
        "⚠️ 风险提示：本信号为系统分析结果，不构成投资建议。"
        "买入信号存在判断失误的可能，请做好风险管理。"
    ),
    "强烈卖出": (
        "⚠️ 风险提示：本信号为系统分析结果，不构成投资建议。"
        "强烈卖出信号不代表一定下跌，请理性评估持仓情况。"
    ),
    "卖出": (
        "⚠️ 风险提示：本信号为系统分析结果，不构成投资建议。"
        "卖出信号存在误判可能，请综合考虑各方面因素。"
    ),
    "持有": (
        "ℹ️ 提示：本信号为系统分析结果，不构成投资建议。"
    ),
}

FORBIDDEN_CONTENT_PATTERNS = [
    ("保证盈利", "禁止承诺保证盈利，违反《证券法》相关规定"),
    ("稳赚不赔", "禁止承诺稳赚不赔，违反《证券法》相关规定"),
    ("必涨", "禁止使用绝对性预测用语，违反合规要求"),
    ("必定", "禁止使用绝对性预测用语，违反合规要求"),
    ("零风险", "禁止承诺零风险，违反合规要求"),
    ("内部消息", "禁止引用内部消息，涉嫌内幕交易"),
    ("内幕信息", "禁止引用内幕信息，涉嫌内幕交易"),
    ("庄家", "禁止讨论庄家行为，涉及市场操纵相关敏感内容"),
    ("操纵", "禁止讨论市场操纵，涉及法律风险"),
    ("代客理财", "禁止提供代客理财建议，需持有相关牌照"),
    ("推荐买入", "应使用'系统信号'而非'推荐'，避免构成投资建议"),
]


class ComplianceGuard:
    """合规审查守护

    职责：
    1. 对所有对外输出进行合规审查
    2. 自动注入免责声明和风险提示
    3. 过滤违规内容
    4. 记录合规审查日志
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._compliance_log: List[Dict[str, Any]] = []
        logger.info("[合规审查] 初始化完成")

    def inject_disclaimer(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """为API响应注入免责声明

        Args:
            response_data: 原始API响应数据

        Returns:
            注入免责声明后的响应数据
        """
        response_data["disclaimer"] = DISCLAIMER_TEXT
        response_data["disclaimer_type"] = "general"
        return response_data

    def inject_signal_risk_notice(
        self,
        signal: str,
        response_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """为交易信号注入风险提示

        Args:
            signal: 交易信号文本
            response_data: 原始API响应数据

        Returns:
            注入风险提示后的响应数据
        """
        risk_notice = SIGNAL_RISK_NOTICES.get(signal, "ℹ️ 提示：本信号为系统分析结果，不构成投资建议。")
        response_data["risk_notice"] = risk_notice
        response_data["signal_type"] = "system_analysis"
        response_data["is_investment_advice"] = False
        return response_data

    def audit_content(self, content: str) -> Dict[str, Any]:
        """审查内容是否合规

        检查分析内容是否包含违规用语，如保证盈利、内幕信息等。

        Args:
            content: 待审查的文本内容

        Returns:
            审查结果字典：
            - compliant: bool - 是否合规
            - violations: List[str] - 违规项列表
            - sanitized_content: str - 清洗后的内容
        """
        violations = []
        sanitized = content

        for pattern, reason in FORBIDDEN_CONTENT_PATTERNS:
            if pattern in content:
                violations.append(f"[{pattern}] {reason}")
                sanitized = sanitized.replace(pattern, f"【已过滤：{pattern}】")

        compliant = len(violations) == 0

        if not compliant:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "violations": violations,
                "original_snippet": content[:200],
            }
            self._compliance_log.append(log_entry)
            logger.warning(f"[合规审查] 发现{len(violations)}项违规: {violations}")

        return {
            "compliant": compliant,
            "violations": violations,
            "sanitized_content": sanitized,
        }

    def classify_output_level(self, output_type: str) -> str:
        """对输出内容进行分级

        区分"信息展示"和"投资建议"的合规边界。

        Args:
            output_type: 输出类型

        Returns:
            分级结果："information" / "analysis" / "signal"
        """
        information_types = {
            "price", "financial_data", "news", "market_data",
            "kline", "volume", "fund_flow_data",
        }
        analysis_types = {
            "technical_analysis", "fundamental_analysis",
            "sentiment_analysis", "news_analysis",
        }
        signal_types = {
            "trade_signal", "buy_signal", "sell_signal",
            "position_suggestion", "stop_loss_suggestion",
        }

        if output_type in information_types:
            return "information"
        elif output_type in analysis_types:
            return "analysis"
        elif output_type in signal_types:
            return "signal"
        return "information"

    def get_compliance_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取合规审查日志

        Args:
            limit: 返回条数上限

        Returns:
            合规审查日志列表
        """
        return self._compliance_log[-limit:]


def create_compliance_response(
    response_data: Dict[str, Any],
    signal: Optional[str] = None,
) -> Dict[str, Any]:
    """便捷函数：为API响应添加合规信息

    Args:
        response_data: 原始响应数据
        signal: 交易信号（可选）

    Returns:
        添加合规信息后的响应数据
    """
    guard = ComplianceGuard()
    response_data = guard.inject_disclaimer(response_data)
    if signal:
        response_data = guard.inject_signal_risk_notice(signal, response_data)
    return response_data
