"""交易员智能体"""

from typing import Dict, Any, Optional
from loguru import logger

from astock_agents.agents.base_agent import BaseAgent
from astock_agents.models import (
    StockData, TechnicalAnalysis, FundamentalAnalysis,
    SentimentAnalysis, NewsAnalysis, DebateResult,
    TradeProposal, Signal
)


class Trader(BaseAgent):
    """交易员 - 负责生成交易提案"""
    
    def __init__(self, llm=None, config=None):
        super().__init__(
            name="交易员",
            role="整合分析师和研究员的观点，生成具体交易方案",
            llm=llm,
            config=config
        )
    
    def analyze(
        self,
        stock_data: StockData,
        technical: TechnicalAnalysis,
        fundamental: FundamentalAnalysis,
        sentiment: SentimentAnalysis,
        news: NewsAnalysis,
        debate: DebateResult,
        **kwargs
    ) -> TradeProposal:
        """
        生成交易提案
        
        整合所有分析结果，生成具体的交易建议
        """
        logger.info(f"[{self.name}] 开始生成交易提案: {stock_data.stock_code}")
        
        # 确定交易方向
        direction = self._determine_direction(debate, technical, fundamental)
        
        # 计算仓位建议
        position_size = self._calculate_position_size(
            direction, technical, fundamental, sentiment, debate
        )
        
        # 计算价格区间
        entry_price, target_price, stop_loss = self._calculate_price_levels(
            stock_data, technical, direction
        )
        
        # 计算预期收益和风险
        expected_return, risk_reward = self._calculate_risk_reward(
            entry_price, target_price, stop_loss, direction
        )
        
        # 确定时间框架
        time_horizon = self._determine_time_horizon(technical, fundamental)
        
        # 整理核心理由
        key_reasons = self._compile_reasons(
            debate, technical, fundamental, sentiment
        )
        
        # 整理风险因素
        risk_factors = self._compile_risk_factors(
            debate, technical, fundamental, news
        )
        
        # 生成完整提案文本
        proposal_text = self._generate_proposal_text(
            stock_data, direction, position_size, entry_price,
            target_price, stop_loss, key_reasons, risk_factors
        )

        # LLM增强分析：生成交易决策逻辑说明
        rationale = None
        if self.llm:
            try:
                llm_result = self._llm_generate_rationale(
                    stock_data, direction, debate, technical, fundamental, sentiment, news
                )
                if llm_result.get("rationale"):
                    rationale = llm_result["rationale"]
            except Exception as e:
                logger.warning(f"[{self.name}] LLM增强分析失败，使用规则引擎结果: {e}")

        proposal = TradeProposal(
            direction=direction,
            position_size_pct=position_size,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss_price=stop_loss,
            expected_return_pct=expected_return,
            risk_reward_ratio=risk_reward,
            time_horizon=time_horizon,
            key_reasons=key_reasons,
            risk_factors=risk_factors,
            proposal_text=proposal_text,
            rationale=rationale
        )
        
        logger.info(f"[{self.name}] 交易提案生成完成: {direction.value}")
        return proposal
    
    def _determine_direction(
        self,
        debate: DebateResult,
        technical: TechnicalAnalysis,
        fundamental: FundamentalAnalysis
    ) -> Signal:
        """确定交易方向"""
        # 基于辩论结果
        if debate.winning_side == "bull":
            if debate.bull_confidence >= 70:
                return Signal.STRONG_BUY
            return Signal.BUY
        elif debate.winning_side == "bear":
            if debate.bear_confidence >= 70:
                return Signal.STRONG_SELL
            return Signal.SELL
        
        # 平局时综合判断
        tech_score = 1 if technical.signal.value in ["买入", "强烈买入"] else -1 if technical.signal.value in ["卖出", "强烈卖出"] else 0
        fund_score = 1 if fundamental.signal.value in ["买入", "强烈买入"] else -1 if fundamental.signal.value in ["卖出", "强烈卖出"] else 0
        
        total = tech_score + fund_score
        
        if total >= 2:
            return Signal.BUY
        elif total <= -2:
            return Signal.SELL
        else:
            return Signal.HOLD
    
    def _calculate_position_size(
        self,
        direction: Signal,
        technical: TechnicalAnalysis,
        fundamental: FundamentalAnalysis,
        sentiment: SentimentAnalysis,
        debate: DebateResult
    ) -> float:
        """计算建议仓位 (%)"""
        base_size = 10  # 基础仓位10%
        
        # 根据置信度调整
        if direction in [Signal.STRONG_BUY, Signal.STRONG_SELL]:
            base_size = 20
        elif direction == Signal.HOLD:
            return 0
        
        # 根据多维度信号调整
        confidence_factors = [
            technical.confidence / 100,
            fundamental.confidence / 100,
            sentiment.confidence / 100,
        ]
        
        avg_confidence = sum(confidence_factors) / len(confidence_factors)
        
        # 辩论结果调整
        if debate.winning_side == "bull" and direction in [Signal.BUY, Signal.STRONG_BUY]:
            debate_factor = debate.bull_confidence / 100
        elif debate.winning_side == "bear" and direction in [Signal.SELL, Signal.STRONG_SELL]:
            debate_factor = debate.bear_confidence / 100
        else:
            debate_factor = 0.5
        
        # 综合计算
        position = base_size * (0.5 + avg_confidence * 0.3 + debate_factor * 0.2)
        
        return round(min(30, max(0, position)), 1)  # 限制在0-30%
    
    def _calculate_price_levels(
        self,
        stock_data: StockData,
        technical: TechnicalAnalysis,
        direction: Signal
    ) -> tuple:
        """
        计算价格区间

        买入方向：目标取最近阻力位（第一档），止损取最近支撑位（第一档）
        卖出方向：目标取最近支撑位（第一档），止损取最近阻力位（第一档）
        """
        current_price = stock_data.current_price

        if not current_price:
            return None, None, None

        entry = current_price

        if direction in [Signal.BUY, Signal.STRONG_BUY]:
            # 买入：目标为最近阻力位（最接近当前价且高于当前价的阻力位）
            if technical.resistance_levels:
                # 阻力位按降序排列，取最接近当前价的（即大于当前价的最小阻力位）
                nearby_resistance = [r for r in technical.resistance_levels if r > current_price]
                target = nearby_resistance[-1] if nearby_resistance else technical.resistance_levels[-1]
            else:
                target = current_price * 1.15  # 默认15%上涨空间

            # 止损为最近支撑位（最接近当前价且低于当前价的支撑位）
            if technical.support_levels:
                # 支撑位按升序排列，取最接近当前价的（即小于当前价的最大支撑位）
                nearby_support = [s for s in technical.support_levels if s < current_price]
                stop_loss = nearby_support[-1] if nearby_support else technical.support_levels[0]
            else:
                stop_loss = current_price * 0.93  # 默认7%止损

        elif direction in [Signal.SELL, Signal.STRONG_SELL]:
            # 卖出：目标为最近支撑位（最接近当前价且低于当前价的支撑位）
            if technical.support_levels:
                nearby_support = [s for s in technical.support_levels if s < current_price]
                target = nearby_support[-1] if nearby_support else technical.support_levels[0]
            else:
                target = current_price * 0.85  # 默认15%下跌空间

            # 止损为最近阻力位（最接近当前价且高于当前价的阻力位）
            if technical.resistance_levels:
                nearby_resistance = [r for r in technical.resistance_levels if r > current_price]
                stop_loss = nearby_resistance[-1] if nearby_resistance else technical.resistance_levels[-1]
            else:
                stop_loss = current_price * 1.07  # 默认7%止损
        else:
            target = None
            stop_loss = None

        return round(entry, 2), round(target, 2) if target else None, round(stop_loss, 2) if stop_loss else None
    
    def _calculate_risk_reward(
        self,
        entry: Optional[float],
        target: Optional[float],
        stop_loss: Optional[float],
        direction: Optional[Signal] = None
    ) -> tuple:
        """
        计算风险收益比

        Args:
            entry: 入场价
            target: 目标价
            stop_loss: 止损价
            direction: 交易方向（用于正确计算预期收益）

        Returns:
            (预期收益率%, 风险收益比)
        """
        if not all([entry, target, stop_loss]):
            return None, None

        potential_gain = abs(target - entry)
        potential_loss = abs(entry - stop_loss)

        # 预期收益：买入方向为正，卖出方向为负
        if direction in [Signal.SELL, Signal.STRONG_SELL]:
            expected_return = round(-1 * (potential_gain / entry) * 100, 1)
        else:
            expected_return = round((potential_gain / entry) * 100, 1)

        risk_reward = round(potential_gain / potential_loss, 2) if potential_loss > 0 else None

        return expected_return, risk_reward
    
    def _determine_time_horizon(
        self,
        technical: TechnicalAnalysis,
        fundamental: FundamentalAnalysis
    ) -> str:
        """确定时间框架"""
        # 基于趋势判断
        if technical.trend == "上升趋势":
            if technical.trend_strength > 70:
                return "中期(1-3个月)"
            else:
                return "短期(1-4周)"
        elif technical.trend == "下降趋势":
            return "短期(1-4周)"
        else:
            return "短期(1-4周)"
    
    def _compile_reasons(
        self,
        debate: DebateResult,
        technical: TechnicalAnalysis,
        fundamental: FundamentalAnalysis,
        sentiment: SentimentAnalysis
    ) -> list:
        """整理核心理由"""
        reasons = []
        
        # 辩论获胜方的主要论据
        if debate.winning_side == "bull":
            reasons.extend(debate.bull_arguments[:3])
        elif debate.winning_side == "bear":
            reasons.extend(debate.bear_arguments[:3])
        
        # 技术面关键信号
        if technical.patterns:
            reasons.append(f"技术形态: {technical.patterns[0]}")
        
        # 基本面关键指标
        if fundamental.valuation_score >= 70:
            reasons.append("估值具有吸引力")
        
        # 情绪面
        if sentiment.overall_score >= 70:
            reasons.append("市场情绪积极")
        
        return reasons[:5]  # 限制数量
    
    def _compile_risk_factors(
        self,
        debate: DebateResult,
        technical: TechnicalAnalysis,
        fundamental: FundamentalAnalysis,
        news: NewsAnalysis
    ) -> list:
        """整理风险因素"""
        risks = []
        
        # 辩论中失败方的主要论据（作为风险提示）
        if debate.winning_side == "bull":
            risks.extend(debate.bear_arguments[:2])
        elif debate.winning_side == "bear":
            risks.extend(debate.bull_arguments[:2])
        
        # 新闻风险
        if news.risk_events:
            risks.extend([f"风险事件[{e.get('level', '未知')}]: {e.get('title', '')[:30]}" for e in news.risk_events[:2]])
        
        # 技术面风险
        if technical.trend == "下降趋势":
            risks.append("处于下降趋势")
        
        # 基本面风险
        if fundamental.financial_health_score < 50:
            risks.append("财务状况欠佳")
        
        return risks[:5]
    
    def _generate_proposal_text(
        self,
        stock_data: StockData,
        direction: Signal,
        position_size: float,
        entry_price: Optional[float],
        target_price: Optional[float],
        stop_loss: Optional[float],
        key_reasons: list,
        risk_factors: list
    ) -> str:
        """生成完整提案文本"""
        lines = [
            f"【交易提案】{stock_data.stock_name} ({stock_data.stock_code})",
            f"",
            f"交易方向: {direction.value}",
            f"建议仓位: {position_size}%",
            f"",
        ]
        
        if entry_price:
            lines.append(f"入场价格: {entry_price}")
        if target_price:
            lines.append(f"目标价格: {target_price}")
        if stop_loss:
            lines.append(f"止损价格: {stop_loss}")
        
        lines.append("")
        
        if key_reasons:
            lines.append("【核心理由】")
            for reason in key_reasons:
                lines.append(f"• {reason}")
            lines.append("")
        
        if risk_factors:
            lines.append("【风险提示】")
            for risk in risk_factors:
                lines.append(f"• {risk}")
            lines.append("")
        
        return "\n".join(lines)

    def _llm_generate_rationale(
        self,
        stock_data: StockData,
        direction: Signal,
        debate: DebateResult,
        technical: TechnicalAnalysis,
        fundamental: FundamentalAnalysis,
        sentiment: SentimentAnalysis,
        news: NewsAnalysis
    ) -> Dict[str, str]:
        """
        使用LLM生成交易决策逻辑说明

        LLM必须基于多空辩论结果和风险评估

        Args:
            stock_data: 股票数据
            direction: 交易方向
            debate: 辩论结果
            technical: 技术分析结果
            fundamental: 基本面分析结果
            sentiment: 情绪分析结果
            news: 新闻分析结果

        Returns:
            LLM结构化输出字典
        """
        # 构建数据摘要（基于多空辩论结果和各维度信号）
        data_parts = [
            f"股票={stock_data.stock_name}({stock_data.stock_code})",
            f"当前价格={stock_data.current_price}",
            f"交易方向={direction.value}",
            f"辩论获胜方={debate.winning_side}",
            f"多头置信度={debate.bull_confidence}",
            f"空头置信度={debate.bear_confidence}",
            f"技术信号={technical.signal.value}",
            f"基本面信号={fundamental.signal.value}",
            f"情绪信号={sentiment.signal.value}",
            f"新闻信号={news.signal.value}",
        ]

        # 添加辩论论据
        if debate.bull_arguments:
            data_parts.append(f"多头论据={'；'.join(debate.bull_arguments[:3])}")
        if debate.bear_arguments:
            data_parts.append(f"空头论据={'；'.join(debate.bear_arguments[:3])}")

        data_summary = ", ".join(data_parts)

        instruction = (
            f"基于以上多空辩论结果和各维度分析数据，为{stock_data.stock_name}的"
            f"交易决策（{direction.value}）生成逻辑说明。"
            "请说明：1)为何做出此交易决策；2)决策的核心依据；3)需要关注的风险。"
            "所有论述必须基于提供的数据，不得编造。"
        )

        output_fields = ["rationale", "decision_logic", "risk_considerations"]

        return self._call_llm_with_data(data_summary, instruction, output_fields)