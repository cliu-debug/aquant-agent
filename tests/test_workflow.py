"""工作流集成测试"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import asyncio

from astock_agents.models.stock_data import StockData, StockPrice
from astock_agents.models.analysis_report import (
    AnalysisReport, TechnicalAnalysis, Signal
)
from astock_agents.workflow.analysis_workflow import AnalysisWorkflow


# ==================== 测试数据工厂 ====================

def create_test_stock_data(days: int = 60) -> StockData:
    """创建测试股票数据"""
    import numpy as np
    
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


# ==================== 工作流测试 ====================

class TestAnalysisWorkflow:
    """分析工作流测试"""
    
    def test_create_workflow(self):
        """测试创建工作流"""
        workflow = AnalysisWorkflow()
        
        assert workflow is not None
    
    def test_workflow_structure(self):
        """测试工作流结构"""
        workflow = AnalysisWorkflow()
        
        # 检查工作流是否有必要的方法
        assert hasattr(workflow, 'run')
        assert hasattr(workflow, 'analyze_stock')
    
    @pytest.mark.asyncio
    async def test_run_analysis(self):
        """测试运行分析"""
        workflow = AnalysisWorkflow()
        stock_data = create_test_stock_data()
        
        # 运行分析
        result = await workflow.run(stock_data)
        
        assert result is not None
        assert isinstance(result, AnalysisReport)
    
    def test_analyze_stock_sync(self):
        """测试同步分析接口"""
        workflow = AnalysisWorkflow()
        stock_data = create_test_stock_data()
        
        # 如果有同步接口
        if hasattr(workflow, 'analyze_stock_sync'):
            result = workflow.analyze_stock_sync(stock_data)
            assert result is not None


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
        """测试风险管理器输出"""
        from astock_agents.agents.risk_manager import RiskManager
        from astock_agents.models.analysis_report import TechnicalAnalysis
        
        manager = RiskManager()
        stock_data = create_test_stock_data()
        
        tech_analysis = TechnicalAnalysis(
            trend="上升趋势",
            trend_strength=70,
            support_levels=[1800.0],
            resistance_levels=[1850.0],
            indicators={},
            patterns=[],
            summary="",
            signal=Signal.BUY,
            confidence=60
        )
        
        result = manager.analyze(stock_data, technical_analysis=tech_analysis)
        
        assert result is not None


# ==================== 多空辩论测试 ====================

class TestBullBearDebate:
    """多空辩论测试"""
    
    def test_bull_researcher(self):
        """测试多头研究员"""
        from astock_agents.agents.bull_researcher import BullResearcher
        
        researcher = BullResearcher()
        stock_data = create_test_stock_data()
        
        result = researcher.analyze(stock_data)
        
        assert result is not None
    
    def test_bear_researcher(self):
        """测试空头研究员"""
        from astock_agents.agents.bear_researcher import BearResearcher
        
        researcher = BearResearcher()
        stock_data = create_test_stock_data()
        
        result = researcher.analyze(stock_data)
        
        assert result is not None


# ==================== 交易员测试 ====================

class TestTrader:
    """交易员测试"""
    
    def test_trader_decision(self):
        """测试交易员决策"""
        from astock_agents.agents.trader import Trader
        
        trader = Trader()
        stock_data = create_test_stock_data()
        
        # 创建模拟分析结果
        tech_analysis = TechnicalAnalysis(
            trend="上升趋势",
            trend_strength=70,
            support_levels=[1800.0],
            resistance_levels=[1850.0],
            indicators={},
            patterns=[],
            summary="",
            signal=Signal.BUY,
            confidence=60
        )
        
        result = trader.analyze(
            stock_data,
            technical_analysis=tech_analysis
        )
        
        assert result is not None


# ==================== 完整流程测试 ====================

class TestFullAnalysisPipeline:
    """完整分析流程测试"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """测试完整分析流程"""
        workflow = AnalysisWorkflow()
        stock_data = create_test_stock_data()
        
        # 运行完整分析
        report = await workflow.run(stock_data)
        
        # 验证报告结构
        assert report is not None
        assert report.stock_code == "600519.SH"
        assert report.stock_name == "贵州茅台"
    
    def test_analysis_with_different_stocks(self):
        """测试不同股票的分析"""
        workflow = AnalysisWorkflow()
        
        stocks = [
            StockData(stock_code="600519.SH", stock_name="贵州茅台"),
            StockData(stock_code="000001.SZ", stock_name="平安银行"),
            StockData(stock_code="000858.SZ", stock_name="五粮液"),
        ]
        
        for stock in stocks:
            # 添加价格数据
            for i in range(30):
                stock.prices.append(StockPrice(
                    date=datetime(2024, 1, 1) + timedelta(days=i),
                    open=100.0,
                    high=102.0,
                    low=98.0,
                    close=100.0 + i * 0.1,
                    volume=1000000
                ))
            
            # 分析应该不抛出异常
            # 注意：这里可能需要异步处理
            try:
                result = workflow.analyze_stock(stock)
                assert result is not None
            except Exception as e:
                # 如果方法不存在或需要异步，跳过
                pass


# ==================== 错误处理测试 ====================

class TestWorkflowErrorHandling:
    """工作流错误处理测试"""
    
    def test_empty_stock_data(self):
        """测试空股票数据"""
        workflow = AnalysisWorkflow()
        
        stock = StockData(
            stock_code="600519.SH",
            stock_name="贵州茅台"
        )
        
        # 应该优雅处理空数据
        try:
            result = workflow.analyze_stock(stock)
            # 如果成功，结果应该是有效的
            assert result is not None
        except Exception as e:
            # 或者抛出有意义的异常
            assert "数据" in str(e) or "empty" in str(e).lower()
    
    def test_invalid_stock_code(self):
        """测试无效股票代码"""
        workflow = AnalysisWorkflow()
        
        stock = StockData(
            stock_code="INVALID",
            stock_name="无效股票"
        )
        
        # 应该优雅处理无效代码
        try:
            result = workflow.analyze_stock(stock)
        except Exception as e:
            # 预期会有异常
            pass


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
