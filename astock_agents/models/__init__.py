"""数据模型定义"""

from astock_agents.models.stock_data import StockData, StockPrice, FinancialReport
from astock_agents.models.analysis_report import (
    AnalysisReport,
    TechnicalAnalysis,
    FundamentalAnalysis,
    SentimentAnalysis,
    NewsAnalysis,
    DebateResult,
    TradeProposal,
    RiskAssessment,
    Signal,
    RiskLevel,
)

__all__ = [
    "StockData",
    "StockPrice",
    "FinancialReport",
    "AnalysisReport",
    "TechnicalAnalysis",
    "FundamentalAnalysis",
    "SentimentAnalysis",
    "NewsAnalysis",
    "DebateResult",
    "TradeProposal",
    "RiskAssessment",
    "Signal",
    "RiskLevel",
]
