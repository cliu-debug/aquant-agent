"""数据源客户端基类"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger

from astock_agents.models.stock_data import StockData, StockPrice, FinancialReport


class BaseDataClient(ABC):
    """数据源客户端基类，定义统一数据获取接口"""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据源客户端

        Args:
            name: 数据源名称
            config: 数据源配置
        """
        self.name = name
        self.config = config or {}
        self._enabled = self.config.get("enabled", True)
        logger.info(f"数据源客户端初始化: {name} (enabled={self._enabled})")

    @property
    def enabled(self) -> bool:
        """是否启用"""
        return self._enabled

    @abstractmethod
    def fetch_kline(
        self,
        stock_code: str,
        days: int = 250,
        freq: str = "daily"
    ) -> Optional[List[StockPrice]]:
        """
        获取K线数据

        Args:
            stock_code: 股票代码（如 600519.SH）
            days: 获取天数
            freq: 频率 daily/weekly

        Returns:
            价格列表，失败返回 None
        """
        pass

    @abstractmethod
    def fetch_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取实时行情

        Args:
            stock_code: 股票代码

        Returns:
            行情字典，失败返回 None
        """
        pass

    @abstractmethod
    def fetch_financial_reports(self, stock_code: str) -> Optional[List[FinancialReport]]:
        """
        获取财务报告

        Args:
            stock_code: 股票代码

        Returns:
            财务报告列表，失败返回 None
        """
        pass

    def _normalize_stock_code(self, stock_code: str) -> str:
        """
        标准化股票代码

        统一转换为 6位数字 格式（如 600519）

        Args:
            stock_code: 原始股票代码

        Returns:
            标准化后的代码
        """
        # 去除后缀 .SH / .SZ
        code = stock_code.split(".")[0] if "." in stock_code else stock_code
        return code.strip()

    def _determine_market(self, stock_code: str) -> str:
        """
        判断市场类型

        Args:
            stock_code: 股票代码

        Returns:
            市场标识
        """
        code = self._normalize_stock_code(stock_code)
        if code.startswith(("6", "9")):
            return "SH"  # 上海
        elif code.startswith(("0", "3", "2")):
            return "SZ"  # 深圳
        elif code.startswith(("4", "8")):
            return "BJ"  # 北京
        return "SZ"
