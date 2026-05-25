"""基本面分析师智能体 - 增强版

优化内容：
- 补全成长性分析（营收增长率、利润增长率）
- 修复默认分数偏高问题（无数据时默认50而非70）
- 增加行业对比逻辑
- 增加多期财务数据对比
- 增加现金流分析
- 优化信号区分度
"""

from typing import Dict, Any, Optional, List
from loguru import logger

from astock_agents.agents.base_agent import BaseAgent
from astock_agents.models import StockData, FundamentalAnalysis, Signal


class FundamentalAnalyst(BaseAgent):
    """基本面分析师 - 负责财务数据分析"""

    # 行业PE参考区间（用于行业对比）
    INDUSTRY_PE_RANGE = {
        "银行": (5, 10),
        "房地产": (6, 12),
        "钢铁": (8, 15),
        "煤炭": (8, 15),
        "交通运输": (10, 18),
        "汽车": (12, 20),
        "家电": (12, 22),
        "食品饮料": (20, 35),
        "白酒": (25, 40),
        "医药": (25, 45),
        "新能源": (25, 50),
        "科技": (30, 60),
        "半导体": (35, 70),
    }

    def __init__(self, llm=None, config=None):
        super().__init__(
            name="基本面分析师",
            role="通过财务数据、估值指标、行业对比评估公司内在价值",
            llm=llm,
            config=config
        )

    def analyze(self, stock_data: StockData, **kwargs) -> FundamentalAnalysis:
        """执行基本面分析"""
        logger.info(f"[{self.name}] 开始基本面分析: {stock_data.stock_code}")

        # 获取关键财务指标
        metrics = self._extract_metrics(stock_data)

        # 盈利能力分析
        profitability_score, profitability_analysis = self._analyze_profitability(metrics)

        # 成长性分析（增强）
        growth_score, growth_analysis = self._analyze_growth(stock_data, metrics)

        # 估值分析（增加行业对比）
        valuation_score, valuation_analysis = self._analyze_valuation(stock_data, metrics)

        # 财务健康分析（修复默认分数）
        financial_health_score, financial_health_analysis = self._analyze_financial_health(metrics)

        # 行业地位
        industry_position = self._assess_industry_position(stock_data, metrics)

        # 生成信号
        signal, confidence = self._generate_signal(
            profitability_score, growth_score, valuation_score, financial_health_score
        )

        # 生成摘要
        summary = self._generate_summary(
            stock_data, metrics, profitability_analysis, growth_analysis,
            valuation_analysis, financial_health_analysis, signal
        )

        analysis = FundamentalAnalysis(
            profitability_score=profitability_score,
            profitability_analysis=profitability_analysis,
            growth_score=growth_score,
            growth_analysis=growth_analysis,
            valuation_score=valuation_score,
            valuation_analysis=valuation_analysis,
            financial_health_score=financial_health_score,
            financial_health_analysis=financial_health_analysis,
            industry_position=industry_position,
            key_metrics=metrics,
            summary=summary,
            signal=signal,
            confidence=confidence
        )

        self.log_analysis(analysis.model_dump())
        return analysis

    def _extract_metrics(self, stock_data: StockData) -> Dict[str, Any]:
        """提取关键财务指标"""
        metrics = {}

        # 从stock_data提取估值指标
        metrics['pe_ttm'] = stock_data.pe_ttm
        metrics['pb'] = stock_data.pb
        metrics['ps_ttm'] = stock_data.ps_ttm
        metrics['dividend_yield'] = stock_data.dividend_yield
        metrics['market_cap'] = stock_data.market_cap

        # 从财务报告提取指标
        if stock_data.financial_reports:
            latest = stock_data.financial_reports[0]
            metrics['roe'] = latest.roe
            metrics['roa'] = latest.roa
            metrics['gross_margin'] = latest.gross_margin
            metrics['net_margin'] = latest.net_margin
            metrics['debt_ratio'] = latest.debt_ratio
            metrics['revenue'] = latest.revenue
            metrics['net_profit'] = latest.net_profit

            # 多期数据对比（提取增长率）
            if len(stock_data.financial_reports) >= 2:
                prev = stock_data.financial_reports[1]
                metrics['revenue_growth'] = self._calc_growth_rate(
                    latest.revenue, prev.revenue
                )
                metrics['profit_growth'] = self._calc_growth_rate(
                    latest.net_profit, prev.net_profit
                )
                metrics['roe_change'] = self._calc_change(
                    latest.roe, prev.roe
                )

        return metrics

    @staticmethod
    def _calc_growth_rate(current: Optional[float], previous: Optional[float]) -> Optional[float]:
        """计算增长率"""
        if current is not None and previous is not None and previous != 0:
            return round((current - previous) / abs(previous) * 100, 1)
        return None

    @staticmethod
    def _calc_change(current: Optional[float], previous: Optional[float]) -> Optional[float]:
        """计算变化值"""
        if current is not None and previous is not None:
            return round(current - previous, 2)
        return None

    def _analyze_profitability(self, metrics: Dict) -> tuple:
        """分析盈利能力"""
        score = 50  # 中性基准
        analysis_points = []
        has_data = False

        roe = metrics.get('roe')
        if roe is not None:
            has_data = True
            if roe > 20:
                score += 20
                analysis_points.append(f"ROE优秀({roe:.1f}%)，盈利能力强")
            elif roe > 15:
                score += 15
                analysis_points.append(f"ROE良好({roe:.1f}%)，盈利能力较强")
            elif roe > 10:
                score += 8
                analysis_points.append(f"ROE一般({roe:.1f}%)")
            elif roe < 5:
                score -= 15
                analysis_points.append(f"ROE较低({roe:.1f}%)，盈利能力弱")

        gross_margin = metrics.get('gross_margin')
        if gross_margin is not None:
            has_data = True
            if gross_margin > 40:
                score += 12
                analysis_points.append(f"毛利率高({gross_margin:.1f}%)，议价能力强")
            elif gross_margin > 25:
                score += 5
                analysis_points.append(f"毛利率中等({gross_margin:.1f}%)")
            elif gross_margin < 10:
                score -= 10
                analysis_points.append(f"毛利率低({gross_margin:.1f}%)，行业竞争激烈")

        net_margin = metrics.get('net_margin')
        if net_margin is not None:
            has_data = True
            if net_margin > 20:
                score += 10
                analysis_points.append(f"净利率优秀({net_margin:.1f}%)")
            elif net_margin > 10:
                score += 5
                analysis_points.append(f"净利率良好({net_margin:.1f}%)")
            elif net_margin < 3:
                score -= 10
                analysis_points.append(f"净利率偏低({net_margin:.1f}%)")

        # ROE变化趋势
        roe_change = metrics.get('roe_change')
        if roe_change is not None:
            if roe_change > 2:
                score += 5
                analysis_points.append(f"ROE同比提升{roe_change:.1f}个百分点")
            elif roe_change < -2:
                score -= 5
                analysis_points.append(f"ROE同比下降{abs(roe_change):.1f}个百分点")

        if not has_data:
            return 50, "盈利能力数据不足"

        analysis = "；".join(analysis_points) if analysis_points else "盈利能力数据不足"
        return min(100, max(0, score)), analysis

    def _analyze_growth(self, stock_data: StockData, metrics: Dict) -> tuple:
        """
        分析成长性（增强版）

        基于营收增长率、利润增长率、ROE变化等指标综合评估
        """
        score = 50  # 中性基准
        analysis_points = []
        has_data = False

        # 营收增长率
        revenue_growth = metrics.get('revenue_growth')
        if revenue_growth is not None:
            has_data = True
            if revenue_growth > 30:
                score += 20
                analysis_points.append(f"营收高速增长({revenue_growth:.1f}%)")
            elif revenue_growth > 15:
                score += 12
                analysis_points.append(f"营收稳健增长({revenue_growth:.1f}%)")
            elif revenue_growth > 5:
                score += 5
                analysis_points.append(f"营收温和增长({revenue_growth:.1f}%)")
            elif revenue_growth > 0:
                score += 2
                analysis_points.append(f"营收微增({revenue_growth:.1f}%)")
            elif revenue_growth > -10:
                score -= 8
                analysis_points.append(f"营收小幅下滑({revenue_growth:.1f}%)")
            else:
                score -= 15
                analysis_points.append(f"营收大幅下滑({revenue_growth:.1f}%)")

        # 利润增长率
        profit_growth = metrics.get('profit_growth')
        if profit_growth is not None:
            has_data = True
            if profit_growth > 30:
                score += 18
                analysis_points.append(f"利润高速增长({profit_growth:.1f}%)")
            elif profit_growth > 15:
                score += 10
                analysis_points.append(f"利润稳健增长({profit_growth:.1f}%)")
            elif profit_growth > 0:
                score += 3
                analysis_points.append(f"利润小幅增长({profit_growth:.1f}%)")
            elif profit_growth > -15:
                score -= 8
                analysis_points.append(f"利润下滑({profit_growth:.1f}%)")
            else:
                score -= 15
                analysis_points.append(f"利润大幅下滑({profit_growth:.1f}%)")

        # 营收规模参考
        revenue = metrics.get('revenue')
        if revenue:
            if revenue > 100e8:
                analysis_points.append(f"营收规模大({revenue/1e8:.0f}亿)")
            elif revenue > 10e8:
                analysis_points.append(f"营收规模中等({revenue/1e8:.0f}亿)")

        if not has_data:
            return 50, "成长性数据待完善（需多期财务数据对比）"

        analysis = "；".join(analysis_points) if analysis_points else "成长性数据待完善"
        return min(100, max(0, score)), analysis

    def _analyze_valuation(self, stock_data: StockData, metrics: Dict) -> tuple:
        """分析估值水平（增加行业对比）"""
        score = 50
        analysis_points = []

        pe = metrics.get('pe_ttm')
        if pe is not None and pe > 0:
            if pe < 10:
                score += 25
                analysis_points.append(f"PE极低({pe:.1f})，估值优势明显")
            elif pe < 20:
                score += 15
                analysis_points.append(f"PE较低({pe:.1f})，估值合理偏低")
            elif pe < 35:
                score += 0
                analysis_points.append(f"PE适中({pe:.1f})")
            elif pe < 50:
                score -= 10
                analysis_points.append(f"PE偏高({pe:.1f})")
            else:
                score -= 20
                analysis_points.append(f"PE过高({pe:.1f})，估值偏贵")

            # 行业PE对比
            industry = stock_data.industry or ""
            for key, (low, high) in self.INDUSTRY_PE_RANGE.items():
                if key in industry or industry in key:
                    if pe < low:
                        score += 8
                        analysis_points.append(f"低于行业PE区间({low}-{high})，估值偏低")
                    elif pe > high:
                        score -= 8
                        analysis_points.append(f"高于行业PE区间({low}-{high})，估值偏高")
                    else:
                        analysis_points.append(f"处于行业PE区间内({low}-{high})")
                    break

        pb = metrics.get('pb')
        if pb is not None and pb > 0:
            if pb < 1:
                score += 15
                analysis_points.append(f"PB破净({pb:.2f})，安全边际高")
            elif pb < 2:
                score += 5
                analysis_points.append(f"PB较低({pb:.2f})")
            elif pb > 5:
                score -= 10
                analysis_points.append(f"PB较高({pb:.2f})")
            elif pb > 8:
                score -= 15
                analysis_points.append(f"PB过高({pb:.2f})，估值偏贵")

        dividend_yield = metrics.get('dividend_yield')
        if dividend_yield is not None and dividend_yield > 0:
            if dividend_yield > 0.04:
                score += 12
                analysis_points.append(f"股息率高({dividend_yield*100:.1f}%)，分红优厚")
            elif dividend_yield > 0.02:
                score += 5
                analysis_points.append(f"股息率尚可({dividend_yield*100:.1f}%)")

        analysis = "；".join(analysis_points) if analysis_points else "估值数据不足"
        return min(100, max(0, score)), analysis

    def _analyze_financial_health(self, metrics: Dict) -> tuple:
        """分析财务健康度（修复默认分数偏高问题）"""
        score = 50  # 修复：无数据时默认50（中性），而非70
        analysis_points = []
        has_data = False

        debt_ratio = metrics.get('debt_ratio')
        if debt_ratio is not None:
            has_data = True
            if debt_ratio < 30:
                score += 15
                analysis_points.append(f"负债率低({debt_ratio:.1f}%)，财务非常稳健")
            elif debt_ratio < 50:
                score += 8
                analysis_points.append(f"负债率适中({debt_ratio:.1f}%)，财务稳健")
            elif debt_ratio < 70:
                score -= 5
                analysis_points.append(f"负债率偏高({debt_ratio:.1f}%)，需关注")
            else:
                score -= 20
                analysis_points.append(f"负债率高({debt_ratio:.1f}%)，财务风险较大")

        roa = metrics.get('roa')
        if roa is not None:
            has_data = True
            if roa > 10:
                score += 10
                analysis_points.append(f"ROA优秀({roa:.1f}%)，资产利用效率高")
            elif roa > 5:
                score += 5
                analysis_points.append(f"ROA良好({roa:.1f}%)")
            elif roa < 2:
                score -= 8
                analysis_points.append(f"ROA偏低({roa:.1f}%)，资产效率不足")

        # 现金流参考（通过营收和利润关系间接判断）
        revenue = metrics.get('revenue')
        net_profit = metrics.get('net_profit')
        if revenue and net_profit and revenue > 0:
            profit_margin = net_profit / revenue * 100
            if profit_margin < 0:
                score -= 10
                analysis_points.append("净利润为负，需关注现金流状况")

        if not has_data:
            return 50, "财务健康度数据待完善"

        analysis = "；".join(analysis_points) if analysis_points else "财务健康度数据待完善"
        return min(100, max(0, score)), analysis

    def _assess_industry_position(self, stock_data: StockData, metrics: Dict) -> str:
        """评估行业地位"""
        market_cap = metrics.get('market_cap')

        if market_cap:
            if market_cap > 2000e8:
                return "行业绝对龙头，市场地位稳固"
            elif market_cap > 500e8:
                return "行业龙头，竞争力强"
            elif market_cap > 100e8:
                return "行业重要参与者"
            elif market_cap > 30e8:
                return "行业中游企业"
            else:
                return "中小型企业，行业影响力有限"

        return "行业地位待评估"

    def _generate_signal(
        self,
        profitability: int,
        growth: int,
        valuation: int,
        financial_health: int
    ) -> tuple:
        """生成交易信号（优化区分度）"""
        # 加权计算总分
        total_score = (
            profitability * 0.3 +
            growth * 0.25 +
            valuation * 0.25 +
            financial_health * 0.2
        )

        if total_score >= 75:
            signal = Signal.STRONG_BUY
        elif total_score >= 62:
            signal = Signal.BUY
        elif total_score >= 38:
            signal = Signal.HOLD
        elif total_score >= 25:
            signal = Signal.SELL
        else:
            signal = Signal.STRONG_SELL

        confidence = min(100, max(10, int(abs(total_score - 50) * 2)))

        return signal, confidence

    def _generate_summary(
        self,
        stock_data: StockData,
        metrics: Dict,
        profitability_analysis: str,
        growth_analysis: str,
        valuation_analysis: str,
        financial_health_analysis: str,
        signal: Signal
    ) -> str:
        """生成分析摘要"""
        lines = [
            f"{stock_data.stock_name}({stock_data.stock_code})基本面分析：",
            f"",
            f"【估值指标】",
            f"• PE(TTM): {metrics.get('pe_ttm', 'N/A')}",
            f"• PB: {metrics.get('pb', 'N/A')}",
            f"• 股息率: {metrics.get('dividend_yield', 'N/A')}",
            f"• 市值: {metrics.get('market_cap', 'N/A')}",
            f"",
            f"【盈利能力】{profitability_analysis}",
            f"",
            f"【成长性】{growth_analysis}",
            f"",
            f"【估值分析】{valuation_analysis}",
            f"",
            f"【财务健康】{financial_health_analysis}",
            f"",
            f"【基本面信号】{signal.value}",
        ]

        return "\n".join(lines)
