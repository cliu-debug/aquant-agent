"""
AQuant-Agent - A股量化智能体

A multi-agent LLM framework for A-share stock investment research.
"""

__version__ = "0.1.0"
__author__ = "AQuant-Agent"
__email__ = "aquant-agent@proton.me"

# 延迟导入，避免循环依赖
# from astock_agents.workflow import AnalysisWorkflow
from astock_agents.models import StockData, AnalysisReport

__all__ = [
    # "AnalysisWorkflow",  # 延迟导入
    "StockData",
    "AnalysisReport",
]
