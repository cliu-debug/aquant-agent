"""智能体层单元测试"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

from astock_agents.models.stock_data import StockData, StockPrice, FinancialReport
from astock_agents.models.analysis_report import (
    TechnicalAnalysis, FundamentalAnalysis, SentimentAnalysis,
    RiskAssessment, AnalysisReport, Signal, RiskLevel
)
from astock_agents.agents.base_agent import BaseAgent
from astock_agents.agents.technical_analyst import TechnicalAnalyst
from astock_agents.agents.fundamental_analyst import FundamentalAnalyst
from astock_agents.agents.sentiment_analyst import SentimentAnalyst
from astock_agents.agents.risk_manager import RiskManager


# ==================== 测试数据工厂 ====================

def create_mock_stock_data(days: int = 60) -> StockData:
    """创建模拟股票数据"""
    stock = StockData(
        stock_code="600519.SH",
        stock_name="贵州茅台",
        industry="白酒",
        pe_ttm=35.0,
        pb=10.0,
        market_cap=2.2e12
    )
    
    # 生成价格数据 - 模拟上涨趋势
    base_price = 1800.0
    for i in range(days):
        # 添加一些波动
        trend = i * 0.5  # 上涨趋势
        noise = np.sin(i * 0.3) * 20  # 波动
        close = base_price + trend + noise
        
        price = StockPrice(
            date=datetime(2024, 1, 1) + timedelta(days=i),
            open=close - 5,
            high=close + 10,
            low=close - 10,
            close=close,
            volume=1000000 + int(np.random.random() * 500000)
        )
        stock.prices.append(price)
    
    # 添加财务数据
    stock.financial_reports.append(FinancialReport(
        report_date=datetime(2024, 3, 31),
        report_type="一季报",
        revenue=40e9,
        net_profit=24e9,
        roe=0.12,
        gross_margin=0.92
    ))
    
    return stock


def create_mock_llm():
    """创建模拟LLM"""
    mock_llm = Mock()
    mock_llm.invoke = Mock(return_value=Mock(content="模拟分析结果"))
    return mock_llm


# ==================== 技术分析师测试 ====================

class TestTechnicalAnalyst:
    """技术分析师测试"""
    
    def test_create_analyst(self):
        """测试创建分析师"""
        analyst = TechnicalAnalyst()
        
        assert analyst.name == "技术分析师"
        assert "技术分析" in analyst.role
    
    def test_analyze_with_mock_data(self):
        """测试分析模拟数据"""
        analyst = TechnicalAnalyst()
        stock_data = create_mock_stock_data(days=60)
        
        result = analyst.analyze(stock_data)
        
        assert result is not None
        assert isinstance(result, TechnicalAnalysis)
        assert result.trend in ["上升趋势", "下降趋势", "震荡整理", "未知"]
        assert 0 <= result.confidence <= 100
        assert isinstance(result.signal, Signal)
    
    def test_analyze_with_insufficient_data(self):
        """测试数据不足时的处理"""
        analyst = TechnicalAnalyst()
        stock_data = create_mock_stock_data(days=5)  # 只有5天数据
        
        result = analyst.analyze(stock_data)
        
        # 应该优雅处理，不抛出异常
        assert result is not None
    
    def test_analyze_empty_data(self):
        """测试空数据处理"""
        analyst = TechnicalAnalyst()
        stock_data = StockData(
            stock_code="600519.SH",
            stock_name="贵州茅台"
        )
        
        result = analyst.analyze(stock_data)
        
        assert result is not None
        assert result.trend == "数据不足"
        assert result.signal == Signal.HOLD
    
    def test_indicator_calculation(self):
        """测试技术指标计算"""
        analyst = TechnicalAnalyst()
        stock_data = create_mock_stock_data(days=100)
        
        result = analyst.analyze(stock_data)
        
        # 检查指标是否计算
        assert "rsi" in result.indicators
        assert "macd" in result.indicators
        assert "kdj" in result.indicators
        assert "bollinger" in result.indicators
        assert "atr" in result.indicators
        assert "adx" in result.indicators
    
    def test_pattern_detection(self):
        """测试形态识别"""
        analyst = TechnicalAnalyst()
        stock_data = create_mock_stock_data(days=60)
        
        result = analyst.analyze(stock_data)
        
        # patterns应该是列表
        assert isinstance(result.patterns, list)
    
    def test_support_resistance_levels(self):
        """测试支撑阻力位计算"""
        analyst = TechnicalAnalyst()
        stock_data = create_mock_stock_data(days=60)
        
        result = analyst.analyze(stock_data)
        
        # 应该计算支撑阻力位
        assert isinstance(result.support_levels, list)
        assert isinstance(result.resistance_levels, list)


# ==================== 基本面分析师测试 ====================

class TestFundamentalAnalyst:
    """基本面分析师测试"""
    
    def test_create_analyst(self):
        """测试创建分析师"""
        analyst = FundamentalAnalyst()
        
        assert analyst.name == "基本面分析师"
    
    def test_analyze_with_financial_data(self):
        """测试分析财务数据"""
        analyst = FundamentalAnalyst()
        stock_data = create_mock_stock_data()
        
        result = analyst.analyze(stock_data)
        
        assert result is not None
        assert isinstance(result, FundamentalAnalysis)
    
    def test_analyze_without_financial_data(self):
        """测试无财务数据时的处理"""
        analyst = FundamentalAnalyst()
        stock_data = StockData(
            stock_code="600519.SH",
            stock_name="贵州茅台"
        )
        
        result = analyst.analyze(stock_data)
        
        # 应该优雅处理
        assert result is not None


# ==================== 情绪分析师测试 ====================

class TestSentimentAnalyst:
    """情绪分析师测试"""
    
    def test_create_analyst(self):
        """测试创建分析师"""
        analyst = SentimentAnalyst()
        
        assert analyst.name == "情绪分析师"
    
    def test_analyze(self):
        """测试情绪分析"""
        analyst = SentimentAnalyst()
        stock_data = create_mock_stock_data()
        
        result = analyst.analyze(stock_data)
        
        assert result is not None
        assert isinstance(result, SentimentAnalysis)


# ==================== 风险管理器测试 ====================

class TestRiskManager:
    """风险管理器测试"""
    
    def test_create_manager(self):
        """测试创建风险管理器"""
        manager = RiskManager()
        
        assert manager.name == "风险管理器"
    
    def test_assess_risk(self):
        """测试风险评估"""
        manager = RiskManager()
        stock_data = create_mock_stock_data()
        
        # 创建模拟的技术分析结果
        tech_analysis = TechnicalAnalysis(
            trend="上升趋势",
            trend_strength=70,
            support_levels=[1800.0, 1780.0],
            resistance_levels=[1850.0, 1900.0],
            indicators={},
            patterns=[],
            summary="",
            signal=Signal.BUY,
            confidence=60
        )
        
        result = manager.analyze(stock_data, technical_analysis=tech_analysis)
        
        assert result is not None
        assert isinstance(result, RiskAssessment)


# ==================== 信号枚举测试 ====================

class TestSignalEnum:
    """信号枚举测试"""
    
    def test_signal_values(self):
        """测试信号值"""
        assert Signal.STRONG_BUY.value == "强烈买入"
        assert Signal.BUY.value == "买入"
        assert Signal.HOLD.value == "持有"
        assert Signal.SELL.value == "卖出"
        assert Signal.STRONG_SELL.value == "强烈卖出"
    
    def test_signal_comparison(self):
        """测试信号比较"""
        assert Signal.STRONG_BUY != Signal.BUY
        assert Signal.BUY != Signal.SELL


# ==================== 风险等级测试 ====================

class TestRiskLevelEnum:
    """风险等级枚举测试"""
    
    def test_risk_level_values(self):
        """测试风险等级值"""
        assert RiskLevel.LOW.value == "低风险"
        assert RiskLevel.MEDIUM.value == "中等风险"
        assert RiskLevel.HIGH.value == "高风险"
        assert RiskLevel.EXTREME.value == "极高风险"


# ==================== 分析报告测试 ====================

class TestAnalysisReport:
    """分析报告测试"""
    
    def test_create_report(self):
        """测试创建分析报告"""
        report = AnalysisReport(
            stock_code="600519.SH",
            stock_name="贵州茅台"
        )
        
        assert report.stock_code == "600519.SH"
        assert report.stock_name == "贵州茅台"
        assert report.technical_analysis is None
        assert report.fundamental_analysis is None
    
    def test_report_with_analyses(self):
        """测试带分析结果的报告"""
        report = AnalysisReport(
            stock_code="600519.SH",
            stock_name="贵州茅台",
            technical_analysis=TechnicalAnalysis(
                trend="上升趋势",
                trend_strength=70,
                support_levels=[],
                resistance_levels=[],
                indicators={},
                patterns=[],
                summary="测试摘要",
                signal=Signal.BUY,
                confidence=60
            )
        )
        
        assert report.technical_analysis is not None
        assert report.technical_analysis.trend == "上升趋势"


# ==================== 技术指标计算单独测试 ====================

class TestIndicatorCalculations:
    """技术指标计算单独测试"""
    
    def test_ma_calculation(self):
        """测试移动平均线计算"""
        analyst = TechnicalAnalyst()
        
        # 创建测试数据
        df = pd.DataFrame({
            'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        })
        
        result = analyst._calc_ma(df)
        
        # MA5应该是最后5个收盘价的平均
        expected_ma5 = (105 + 106 + 107 + 108 + 109) / 5
        assert 'MA5' in result
        assert abs(result['MA5'] - expected_ma5) < 0.01
    
    def test_rsi_calculation(self):
        """测试RSI计算"""
        analyst = TechnicalAnalyst()
        stock_data = create_mock_stock_data(days=30)
        
        df = analyst._prepare_data(stock_data)
        result = analyst._calc_rsi(df)
        
        assert 'value' in result
        assert 0 <= result['value'] <= 100
        assert 'zone' in result
    
    def test_macd_calculation(self):
        """测试MACD计算"""
        analyst = TechnicalAnalyst()
        stock_data = create_mock_stock_data(days=50)
        
        df = analyst._prepare_data(stock_data)
        result = analyst._calc_macd(df)
        
        assert 'dif' in result
        assert 'dea' in result
        assert 'histogram' in result
        assert 'trend' in result
    
    def test_kdj_calculation(self):
        """测试KDJ计算"""
        analyst = TechnicalAnalyst()
        stock_data = create_mock_stock_data(days=30)
        
        df = analyst._prepare_data(stock_data)
        result = analyst._calc_kdj(df)
        
        assert 'k' in result
        assert 'd' in result
        assert 'j' in result
    
    def test_bollinger_calculation(self):
        """测试布林带计算"""
        analyst = TechnicalAnalyst()
        stock_data = create_mock_stock_data(days=30)
        
        df = analyst._prepare_data(stock_data)
        result = analyst._calc_bollinger(df)
        
        assert 'upper' in result
        assert 'middle' in result
        assert 'lower' in result
        assert result['upper'] > result['middle'] > result['lower']
    
    def test_atr_calculation(self):
        """测试ATR计算"""
        analyst = TechnicalAnalyst()
        stock_data = create_mock_stock_data(days=30)
        
        df = analyst._prepare_data(stock_data)
        result = analyst._calc_atr(df)
        
        assert 'value' in result
        assert 'pct' in result
        assert 'volatility' in result
        assert result['value'] > 0


# ==================== K线形态识别测试 ====================

class TestPatternRecognition:
    """K线形态识别测试"""
    
    def test_bullish_engulfing(self):
        """测试看涨吞没形态"""
        analyst = TechnicalAnalyst()
        
        # 创建看涨吞没形态数据
        df = pd.DataFrame({
            'open': [100, 95],   # 第二根开盘更低
            'high': [102, 105],
            'low': [98, 94],
            'close': [99, 104],   # 第二根收盘更高，吞没前一根
            'volume': [1000000, 1500000]
        })
        
        patterns = analyst._identify_double_candle_patterns(df)
        
        # 应该识别出看涨吞没
        assert "看涨吞没" in patterns
    
    def test_bearish_engulfing(self):
        """测试看跌吞没形态"""
        analyst = TechnicalAnalyst()
        
        # 创建看跌吞没形态数据
        df = pd.DataFrame({
            'open': [100, 105],   # 第二根开盘更高
            'high': [102, 106],
            'low': [98, 99],
            'close': [101, 98],   # 第二根收盘更低，吞没前一根
            'volume': [1000000, 1500000]
        })
        
        patterns = analyst._identify_double_candle_patterns(df)
        
        # 应该识别出看跌吞没
        assert "看跌吞没" in patterns
    
    def test_hammer_pattern(self):
        """测试锤子线形态"""
        analyst = TechnicalAnalyst()
        
        # 创建锤子线形态
        df = pd.DataFrame({
            'open': [100],
            'high': [101],
            'low': [90],   # 长下影线
            'close': [100.5],
            'volume': [1000000]
        })
        
        patterns = analyst._identify_single_candle_patterns(df)
        
        # 应该识别出锤子线
        assert any("锤子线" in p for p in patterns)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
