"""工作流集成测试"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, PropertyMock
import numpy as np

from astock_agents.models.stock_data import StockData, StockPrice
from astock_agents.models.analysis_report import (
    AnalysisReport, TechnicalAnalysis, FundamentalAnalysis,
    SentimentAnalysis, NewsAnalysis, DebateResult, TradeProposal,
    RiskAssessment, Signal, RiskLevel
)
from astock_agents.workflow.analysis_workflow import AnalysisWorkflow


# ==================== 测试数据工厂 ====================

def create_test_stock_data(days: int = 60) -> StockData:
    """创建测试股票数据"""
    stock = StockData(
        stock_code="600519.SH",
        stock_name="贵州茅台",
        industry="白酒",
        pe_ttm=35.0,
        pb=10.0
    )

    base_price = 1800.0
    for i in range(days):
        close = base_price + i * 0.5 + np.sin(i * 0.3) * 20
        price = StockPrice(
            date=datetime(2024, 1, 1) + timedelta(days=i),
            open=close - 5,
            high=close + 10,
            low=close - 10,
            close=close,
            volume=1000000
        )
        stock.prices.append(price)

    return stock


def create_test_technical_analysis() -> TechnicalAnalysis:
    """创建测试技术分析结果"""
    return TechnicalAnalysis(
        trend="上升趋势",
        trend_strength=70,
        support_levels=[1800.0],
        resistance_levels=[1850.0],
        indicators={
            "rsi": {"value": 55, "zone": "中性"},
            "macd": {"dif": 1.2, "dea": 0.8, "histogram": 0.4, "trend": "多头"},
            "kdj": {"k": 60, "d": 55, "j": 70},
            "bollinger": {"upper": 1900, "middle": 1820, "lower": 1740},
            "atr": {"value": 25.0, "pct": 1.4, "volatility": "中等"},
            "adx": {"value": 28, "trend_strength": "偏强"},
        },
        patterns=["金叉突破"],
        summary="技术面偏多",
        signal=Signal.BUY,
        confidence=60
    )


def create_test_fundamental_analysis() -> FundamentalAnalysis:
    """创建测试基本面分析结果"""
    return FundamentalAnalysis(
        profitability_score=75,
        profitability_analysis="盈利能力优秀",
        growth_score=65,
        growth_analysis="成长性良好",
        valuation_score=55,
        valuation_analysis="估值合理",
        financial_health_score=80,
        financial_health_analysis="财务状况稳健",
        industry_position="行业龙头",
        key_metrics={"pe_ttm": 35.0, "pb": 10.0, "roe": 12.0},
        summary="基本面良好",
        signal=Signal.BUY,
        confidence=65
    )


def create_test_sentiment_analysis() -> SentimentAnalysis:
    """创建测试情绪分析结果"""
    return SentimentAnalysis(
        overall_score=70,
        market_sentiment="市场情绪偏多",
        related_hot_topics=["白酒板块"],
        topic_momentum={"白酒板块": 0.8},
        fund_flow="主力资金小幅流入",
        news_sentiment="新闻面偏正面",
        summary="市场情绪偏多",
        signal=Signal.BUY,
        confidence=55
    )


def create_test_news_analysis() -> NewsAnalysis:
    """创建测试新闻分析结果"""
    return NewsAnalysis(
        key_news=[{"title": "业绩超预期", "date": "2024-03-31"}],
        key_announcements=[{"title": "分红方案", "date": "2024-03-31"}],
        macro_impact="宏观环境稳定",
        industry_updates="白酒行业景气度回升",
        risk_events=[],
        summary="新闻面偏正面",
        signal=Signal.HOLD,
        confidence=50
    )


def create_test_debate_result() -> DebateResult:
    """创建测试辩论结果"""
    return DebateResult(
        bull_arguments=["技术面偏多", "基本面良好"],
        bull_confidence=65,
        bear_arguments=["估值偏高"],
        bear_confidence=40,
        debate_summary="多头占优",
        winning_side="bull",
        key_disagreements=["估值是否合理"]
    )


def create_test_trade_proposal() -> TradeProposal:
    """创建测试交易提案"""
    return TradeProposal(
        direction=Signal.BUY,
        position_size_pct=10.0,
        entry_price=1830.0,
        target_price=1900.0,
        stop_loss_price=1790.0,
        expected_return_pct=3.8,
        risk_reward_ratio=1.75,
        time_horizon="中期",
        key_reasons=["技术面偏多", "基本面良好"],
        risk_factors=["估值偏高"],
        proposal_text="建议买入，仓位10%"
    )


# ==================== 工作流测试 ====================

class TestAnalysisWorkflow:
    """分析工作流测试"""

    def test_create_workflow(self):
        """测试创建工作流"""
        workflow = AnalysisWorkflow()

        assert workflow is not None

    def test_workflow_has_analyze_method(self):
        """测试工作流是否有analyze方法"""
        workflow = AnalysisWorkflow()

        # 检查工作流是否有必要的analyze方法
        assert hasattr(workflow, 'analyze')
        assert callable(workflow.analyze)

    @patch('astock_agents.workflow.analysis_workflow.DataManager')
    def test_analyze_method_signature(self, mock_dm_class):
        """测试analyze方法签名"""
        workflow = AnalysisWorkflow()

        # analyze方法接受stock_code和stock_name参数
        import inspect
        sig = inspect.signature(workflow.analyze)
        params = list(sig.parameters.keys())

        assert "stock_code" in params
        assert "stock_name" in params


# ==================== 智能体协作测试 ====================

class TestAgentCollaboration:
    """智能体协作测试"""

    def test_technical_analyst_output(self):
        """测试技术分析师输出"""
        from astock_agents.agents.technical_analyst import TechnicalAnalyst

        analyst = TechnicalAnalyst()
        stock_data = create_test_stock_data()

        result = analyst.analyze(stock_data)

        assert result is not None
        assert hasattr(result, 'signal')
        assert hasattr(result, 'confidence')

    def test_fundamental_analyst_output(self):
        """测试基本面分析师输出"""
        from astock_agents.agents.fundamental_analyst import FundamentalAnalyst

        analyst = FundamentalAnalyst()
        stock_data = create_test_stock_data()

        result = analyst.analyze(stock_data)

        assert result is not None

    def test_sentiment_analyst_output(self):
        """测试情绪分析师输出"""
        from astock_agents.agents.sentiment_analyst import SentimentAnalyst

        analyst = SentimentAnalyst()
        stock_data = create_test_stock_data()

        result = analyst.analyze(stock_data)

        assert result is not None

    def test_risk_manager_output(self):
        """测试风险管理经理输出"""
        from astock_agents.agents.risk_manager import RiskManager

        manager = RiskManager()
        stock_data = create_test_stock_data()
        trade_proposal = create_test_trade_proposal()

        result = manager.analyze(
            stock_data=stock_data,
            trade_proposal=trade_proposal
        )

        assert result is not None
        assert isinstance(result, RiskAssessment)


# ==================== 多空辩论测试 ====================

class TestBullBearDebate:
    """多空辩论测试"""

    def test_bull_researcher(self):
        """测试多头研究员"""
        from astock_agents.agents.bull_researcher import BullResearcher

        researcher = BullResearcher()
        stock_data = create_test_stock_data()
        technical = create_test_technical_analysis()
        fundamental = create_test_fundamental_analysis()
        sentiment = create_test_sentiment_analysis()
        news = create_test_news_analysis()

        result = researcher.analyze(
            stock_data=stock_data,
            technical=technical,
            fundamental=fundamental,
            sentiment=sentiment,
            news=news
        )

        assert result is not None
        assert "arguments" in result
        assert "confidence" in result

    def test_bear_researcher(self):
        """测试空头研究员"""
        from astock_agents.agents.bear_researcher import BearResearcher

        researcher = BearResearcher()
        stock_data = create_test_stock_data()
        technical = create_test_technical_analysis()
        fundamental = create_test_fundamental_analysis()
        sentiment = create_test_sentiment_analysis()
        news = create_test_news_analysis()

        result = researcher.analyze(
            stock_data=stock_data,
            technical=technical,
            fundamental=fundamental,
            sentiment=sentiment,
            news=news
        )

        assert result is not None
        assert "arguments" in result
        assert "confidence" in result

    def test_debate_result_construction(self):
        """测试辩论结果构建"""
        bull_result = {
            "arguments": ["技术面偏多", "基本面良好"],
            "confidence": 65,
            "argument_count": 2
        }
        bear_result = {
            "arguments": ["估值偏高"],
            "confidence": 40,
            "argument_count": 1
        }

        debate = DebateResult(
            bull_arguments=bull_result["arguments"],
            bull_confidence=bull_result["confidence"],
            bear_arguments=bear_result["arguments"],
            bear_confidence=bear_result["confidence"],
            debate_summary="多头占优",
            winning_side="bull",
            key_disagreements=["估值是否合理"]
        )

        assert debate.winning_side == "bull"
        assert len(debate.bull_arguments) == 2
        assert len(debate.bear_arguments) == 1


# ==================== 交易员测试 ====================

class TestTrader:
    """交易员测试"""

    def test_trader_decision(self):
        """测试交易员决策"""
        from astock_agents.agents.trader import Trader

        trader = Trader()
        stock_data = create_test_stock_data()
        technical = create_test_technical_analysis()
        fundamental = create_test_fundamental_analysis()
        sentiment = create_test_sentiment_analysis()
        news = create_test_news_analysis()
        debate = create_test_debate_result()

        result = trader.analyze(
            stock_data=stock_data,
            technical=technical,
            fundamental=fundamental,
            sentiment=sentiment,
            news=news,
            debate=debate
        )

        assert result is not None
        assert isinstance(result, TradeProposal)
        assert isinstance(result.direction, Signal)
        assert result.position_size_pct > 0


# ==================== 完整流程测试（Mock方式） ====================

class TestFullAnalysisPipeline:
    """完整分析流程测试 - 使用Mock避免真实数据连接"""

    @patch('astock_agents.workflow.analysis_workflow.DataManager')
    def test_analyze_returns_report(self, mock_dm_class):
        """测试analyze方法返回分析报告"""
        # Mock DataManager 返回测试数据
        mock_dm_instance = MagicMock()
        mock_dm_class.return_value = mock_dm_instance
        mock_dm_instance.get_stock_data.return_value = create_test_stock_data()

        workflow = AnalysisWorkflow()
        report = workflow.analyze(stock_code="600519.SH", stock_name="贵州茅台")

        assert report is not None
        assert isinstance(report, AnalysisReport)
        assert report.stock_code == "600519.SH"
        assert report.stock_name == "贵州茅台"

    @patch('astock_agents.workflow.analysis_workflow.DataManager')
    def test_analyze_with_data_fetch_failure(self, mock_dm_class):
        """测试数据获取失败时的处理"""
        # Mock DataManager 抛出异常
        mock_dm_instance = MagicMock()
        mock_dm_class.return_value = mock_dm_instance
        mock_dm_instance.get_stock_data.side_effect = Exception("数据获取失败")

        workflow = AnalysisWorkflow()
        report = workflow.analyze(stock_code="600519.SH", stock_name="贵州茅台")

        # 应该返回包含错误的报告
        assert report is not None
        assert isinstance(report, AnalysisReport)
        assert len(report.errors) > 0

    @patch('astock_agents.workflow.analysis_workflow.DataManager')
    def test_analyze_different_stocks(self, mock_dm_class):
        """测试不同股票的分析"""
        mock_dm_instance = MagicMock()
        mock_dm_class.return_value = mock_dm_instance

        # 创建不同股票的测试数据
        stock1 = create_test_stock_data()
        stock1.stock_code = "000001.SZ"
        stock1.stock_name = "平安银行"

        mock_dm_instance.get_stock_data.return_value = stock1

        workflow = AnalysisWorkflow()
        report = workflow.analyze(stock_code="000001.SZ", stock_name="平安银行")

        assert report is not None
        assert report.stock_code == "000001.SZ"


# ==================== 错误处理测试 ====================

class TestWorkflowErrorHandling:
    """工作流错误处理测试"""

    @patch('astock_agents.workflow.analysis_workflow.DataManager')
    def test_empty_stock_data(self, mock_dm_class):
        """测试空股票数据"""
        mock_dm_instance = MagicMock()
        mock_dm_class.return_value = mock_dm_instance

        # 返回空数据的StockData
        empty_stock = StockData(
            stock_code="600519.SH",
            stock_name="贵州茅台"
        )
        mock_dm_instance.get_stock_data.return_value = empty_stock

        workflow = AnalysisWorkflow()
        report = workflow.analyze(stock_code="600519.SH", stock_name="贵州茅台")

        # 应该优雅处理空数据，返回包含错误的报告
        assert report is not None
        assert isinstance(report, AnalysisReport)

    @patch('astock_agents.workflow.analysis_workflow.DataManager')
    def test_data_fetch_exception(self, mock_dm_class):
        """测试数据获取异常"""
        mock_dm_instance = MagicMock()
        mock_dm_class.return_value = mock_dm_instance
        mock_dm_instance.get_stock_data.side_effect = ConnectionError("网络连接失败")

        workflow = AnalysisWorkflow()
        report = workflow.analyze(stock_code="600519.SH", stock_name="贵州茅台")

        # 应该优雅处理异常
        assert report is not None
        assert isinstance(report, AnalysisReport)
        assert len(report.errors) > 0


# ==================== 性能测试 ====================

class TestPerformance:
    """性能测试"""

    @pytest.mark.slow
    def test_analysis_performance(self):
        """测试分析性能"""
        import time
        from astock_agents.agents.technical_analyst import TechnicalAnalyst

        analyst = TechnicalAnalyst()

        # 创建大量数据
        stock_data = create_test_stock_data(days=250)

        start_time = time.time()
        result = analyst.analyze(stock_data)
        elapsed_time = time.time() - start_time

        # 分析应该在合理时间内完成（例如5秒）
        assert elapsed_time < 5.0
        assert result is not None

    @pytest.mark.slow
    def test_multiple_stocks_performance(self):
        """测试多股票分析性能"""
        import time
        from astock_agents.agents.technical_analyst import TechnicalAnalyst

        analyst = TechnicalAnalyst()

        stocks = []
        for i in range(10):
            stock = create_test_stock_data(days=60)
            stock.stock_code = f"test{i:04d}"
            stocks.append(stock)

        start_time = time.time()

        for stock in stocks:
            result = analyst.analyze(stock)
            assert result is not None

        elapsed_time = time.time() - start_time

        # 10只股票分析应该在30秒内完成
        assert elapsed_time < 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
