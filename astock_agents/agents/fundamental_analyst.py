"""基本面分析师智能体"""

from typing import Dict, Any, Optional
from loguru import logger

from astock_agents.agents.base_agent import BaseAgent
from astock_agents.models import StockData, FundamentalAnalysis, Signal


class FundamentalAnalyst(BaseAgent):
    """基本面分析师 - 负责财务数据分析"""
    
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
        
        # 成长性分析
        growth_score, growth_analysis = self._analyze_growth(metrics)
        
        # 估值分析
        valuation_score, valuation_analysis = self._analyze_valuation(stock_data, metrics)
        
        # 财务健康分析
        financial_health_score, financial_health_analysis = self._analyze_financial_health(metrics)
        
        # 行业地位
        industry_position = self._assess_industry_position(stock_data, metrics)
        
        # 生成信号
        signal, confidence = self._generate_signal(
            profitability_score, growth_score, valuation_score, financial_health_score
        )
        
        # 生成摘要
        summary = self._generate_summary(
            stock_data, metrics, profitability_analysis, valuation_analysis, signal
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
        
        self.log_analysis(analysis.dict())
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
        
        return metrics
    
    def _analyze_profitability(self, metrics: Dict) -> tuple:
        """分析盈利能力"""
        score = 50
        analysis_points = []
        
        roe = metrics.get('roe')
        if roe is not None:
            if roe > 15:
                score += 20
                analysis_points.append(f"ROE优秀({roe:.1f}%)，盈利能力强")
            elif roe > 10:
                score += 10
                analysis_points.append(f"ROE良好({roe:.1f}%)")
            elif roe < 5:
                score -= 15
                analysis_points.append(f"ROE较低({roe:.1f}%)，盈利能力弱")
        
        gross_margin = metrics.get('gross_margin')
        if gross_margin is not None:
            if gross_margin > 30:
                score += 10
                analysis_points.append(f"毛利率高({gross_margin:.1f}%)，议价能力强")
            elif gross_margin < 10:
                score -= 10
                analysis_points.append(f"毛利率低({gross_margin:.1f}%)，行业竞争激烈")
        
        net_margin = metrics.get('net_margin')
        if net_margin is not None:
            if net_margin > 15:
                score += 10
                analysis_points.append(f"净利率优秀({net_margin:.1f}%)")
            elif net_margin < 5:
                score -= 10
                analysis_points.append(f"净利率偏低({net_margin:.1f}%)")
        
        analysis = "；".join(analysis_points) if analysis_points else "盈利能力数据不足"
        return min(100, max(0, score)), analysis
    
    def _analyze_growth(self, metrics: Dict) -> tuple:
        """分析成长性"""
        score = 50
        analysis_points = []
        
        # 简化处理，实际应该对比多期数据
        revenue = metrics.get('revenue')
        if revenue:
            if revenue > 10e8:  # 100亿
                analysis_points.append(f"营收规模较大({revenue/1e8:.1f}亿)")
            elif revenue > 1e8:  # 10亿
                analysis_points.append(f"营收规模中等({revenue/1e8:.1f}亿)")
            else:
                analysis_points.append(f"营收规模较小({revenue/1e8:.1f}亿)")
        
        # 默认中等成长
        analysis = "；".join(analysis_points) if analysis_points else "成长性数据待完善"
        return min(100, max(0, score)), analysis
    
    def _analyze_valuation(self, stock_data: StockData, metrics: Dict) -> tuple:
        """分析估值水平"""
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
            elif pe > 50:
                score -= 20
                analysis_points.append(f"PE偏高({pe:.1f})，估值偏贵")
            else:
                analysis_points.append(f"PE适中({pe:.1f})")
        
        pb = metrics.get('pb')
        if pb is not None and pb > 0:
            if pb < 1:
                score += 15
                analysis_points.append(f"PB破净({pb:.2f})，安全边际高")
            elif pb < 2:
                score += 5
                analysis_points.append(f"PB较低({pb:.2f})")
            elif pb > 5:
                score -= 15
                analysis_points.append(f"PB较高({pb:.2f})")
        
        dividend_yield = metrics.get('dividend_yield')
        if dividend_yield is not None and dividend_yield > 0:
            if dividend_yield > 0.03:  # 3%
                score += 10
                analysis_points.append(f"股息率较高({dividend_yield*100:.1f}%)")
        
        analysis = "；".join(analysis_points) if analysis_points else "估值数据不足"
        return min(100, max(0, score)), analysis
    
    def _analyze_financial_health(self, metrics: Dict) -> tuple:
        """分析财务健康度"""
        score = 70  # 默认良好
        analysis_points = []
        
        debt_ratio = metrics.get('debt_ratio')
        if debt_ratio is not None:
            if debt_ratio < 40:
                analysis_points.append(f"负债率低({debt_ratio:.1f}%)，财务稳健")
            elif debt_ratio > 70:
                score -= 20
                analysis_points.append(f"负债率高({debt_ratio:.1f}%)，财务风险较大")
            else:
                analysis_points.append(f"负债率适中({debt_ratio:.1f}%)")
        
        roa = metrics.get('roa')
        if roa is not None:
            if roa > 8:
                score += 10
                analysis_points.append(f"ROA优秀({roa:.1f}%)，资产利用效率高")
            elif roa < 3:
                score -= 10
                analysis_points.append(f"ROA偏低({roa:.1f}%)")
        
        analysis = "；".join(analysis_points) if analysis_points else "财务健康度数据待完善"
        return min(100, max(0, score)), analysis
    
    def _assess_industry_position(self, stock_data: StockData, metrics: Dict) -> str:
        """评估行业地位"""
        market_cap = metrics.get('market_cap')
        
        if market_cap:
            if market_cap > 1000e8:  # 1000亿
                return "行业龙头"
            elif market_cap > 100e8:  # 100亿
                return "行业重要参与者"
            else:
                return "中小型企业"
        
        return "行业地位待评估"
    
    def _generate_signal(
        self,
        profitability: int,
        growth: int,
        valuation: int,
        financial_health: int
    ) -> tuple:
        """生成交易信号"""
        # 加权计算总分
        total_score = (
            profitability * 0.3 +
            growth * 0.2 +
            valuation * 0.3 +
            financial_health * 0.2
        )
        
        if total_score >= 75:
            signal = Signal.STRONG_BUY
        elif total_score >= 60:
            signal = Signal.BUY
        elif total_score >= 45:
            signal = Signal.HOLD
        elif total_score >= 30:
            signal = Signal.SELL
        else:
            signal = Signal.STRONG_SELL
        
        confidence = min(100, max(0, int(abs(total_score - 50) * 2)))
        
        return signal, confidence
    
    def _generate_summary(
        self,
        stock_data: StockData,
        metrics: Dict,
        profitability_analysis: str,
        valuation_analysis: str,
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
            f"【估值分析】{valuation_analysis}",
            f"",
            f"【基本面信号】{signal.value}",
        ]
        
        return "\n".join(lines)