"""Mootdx (通达信) 数据源客户端"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger

from astock_agents.data.base_client import BaseDataClient
from astock_agents.data.circuit_breaker import get_circuit_breaker, with_retry
from astock_agents.models.stock_data import StockPrice, FinancialReport


class MootdxClient(BaseDataClient):
    """通达信数据源客户端 - 提供K线数据和实时行情"""

    # 市场映射：0=深圳, 1=上海
    MARKET_MAP = {"SZ": 0, "SH": 1, "BJ": 0}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(name="mootdx", config=config)
        self._api = None
        self._circuit_breaker = get_circuit_breaker("mootdx")

    def _get_api(self):
        """懒加载 mootdx API 连接"""
        if self._api is not None:
            return self._api

        try:
            from mootdx.quotes import Quotes

            market = self.config.get("market", "std")  # std=标准, ext=扩展
            self._api = Quotes.factory(market=market)

            if self._api is None:
                logger.warning("[mootdx] 无法连接到通达信服务器")
            else:
                logger.info("[mootdx] 连接成功")

            return self._api
        except Exception as e:
            logger.error(f"[mootdx] 连接失败: {e}")
            return None

    def fetch_kline(
        self,
        stock_code: str,
        days: int = 250,
        freq: str = "daily"
    ) -> Optional[List[StockPrice]]:
        """
        获取K线数据（带断路器保护）

        Args:
            stock_code: 股票代码（如 600519.SH）
            days: 获取天数
            freq: 频率 daily/weekly/monthly

        Returns:
            价格列表，失败返回 None
        """
        if not self._enabled:
            return None
        if self._circuit_breaker.is_open:
            logger.warning("[mootdx] 断路器已断开，跳过K线请求")
            return None
        try:
            result = self._fetch_kline_impl(stock_code, days, freq)
            self._circuit_breaker.record_success()
            return result
        except Exception as e:
            self._circuit_breaker.record_failure()
            logger.error(f"[mootdx] 获取K线失败: {stock_code}, {e}")
            return None

    @with_retry(max_attempts=2, wait_min=1.0, wait_max=5.0)
    def _fetch_kline_impl(
        self,
        stock_code: str,
        days: int,
        freq: str
    ) -> Optional[List[StockPrice]]:
        """
        K线数据获取实现（带重试）

        Args:
            stock_code: 股票代码
            days: 获取天数
            freq: 频率

        Returns:
            价格列表，失败抛出异常

        Raises:
            Exception: API调用失败时抛出
        """
        api = self._get_api()
        if api is None:
            return None

        code = self._normalize_stock_code(stock_code)
        market = self.MARKET_MAP.get(self._determine_market(stock_code), 1)

        # 频率映射
        category_map = {
            "daily": 9,    # 日线
            "weekly": 5,   # 周线
            "monthly": 6,  # 月线
        }
        category = category_map.get(freq, 9)

        df = api.bars(
            symbol=code,
            category=category,
            market=market,
            offset=days
        )

        if df is None or df.empty:
            logger.warning(f"[mootdx] 无K线数据: {stock_code}")
            return None

        prices = []
        for _, row in df.iterrows():
            price = StockPrice(
                date=row.get("datetime", row.name) if isinstance(row.get("datetime", row.name), datetime) else datetime.now(),
                open=float(row.get("open", 0)),
                high=float(row.get("high", 0)),
                low=float(row.get("low", 0)),
                close=float(row.get("close", 0)),
                volume=int(row.get("vol", 0)),
                amount=float(row.get("amount", 0)),
            )
            prices.append(price)

        logger.info(f"[mootdx] 获取K线成功: {stock_code}, {len(prices)}条")
        return prices

    def fetch_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取实时行情（带断路器保护）

        Args:
            stock_code: 股票代码

        Returns:
            行情字典，失败返回 None
        """
        if not self._enabled:
            return None
        if self._circuit_breaker.is_open:
            logger.warning("[mootdx] 断路器已断开，跳过实时行情请求")
            return None
        try:
            result = self._fetch_realtime_quote_impl(stock_code)
            self._circuit_breaker.record_success()
            return result
        except Exception as e:
            self._circuit_breaker.record_failure()
            logger.error(f"[mootdx] 获取实时行情失败: {stock_code}, {e}")
            return None

    @with_retry(max_attempts=2, wait_min=1.0, wait_max=5.0)
    def _fetch_realtime_quote_impl(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        实时行情获取实现（带重试）

        Args:
            stock_code: 股票代码

        Returns:
            行情字典，失败抛出异常

        Raises:
            Exception: API调用失败时抛出
        """
        api = self._get_api()
        if api is None:
            return None

        code = self._normalize_stock_code(stock_code)
        market = self.MARKET_MAP.get(self._determine_market(stock_code), 1)

        df = api.quotes(symbol=code, market=market)

        if df is None or df.empty:
            return None

        row = df.iloc[0]
        return {
            "stock_code": stock_code,
            "stock_name": str(row.get("name", "")),
            "price": float(row.get("price", 0)),
            "open": float(row.get("open", 0)),
            "high": float(row.get("high", 0)),
            "low": float(row.get("low", 0)),
            "close": float(row.get("close", 0)),
            "volume": int(row.get("vol", 0)),
            "amount": float(row.get("amount", 0)),
            "bid1": float(row.get("bid1", 0)),
            "ask1": float(row.get("ask1", 0)),
        }

    def fetch_financial_reports(self, stock_code: str) -> Optional[List[FinancialReport]]:
        """获取财务报告（mootdx 不提供财务数据，返回 None）"""
        logger.debug(f"[mootdx] 不支持财务数据获取: {stock_code}")
        return None
