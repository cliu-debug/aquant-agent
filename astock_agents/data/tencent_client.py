"""腾讯财经数据源客户端 - 提供实时行情和估值数据"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger

from astock_agents.data.base_client import BaseDataClient
from astock_agents.data.circuit_breaker import get_circuit_breaker, with_retry
from astock_agents.models.stock_data import StockPrice, FinancialReport


class TencentClient(BaseDataClient):
    """腾讯财经数据源客户端 - 提供实时行情和估值数据"""

    # 腾讯财经行情接口
    QUOTE_URL = "https://qt.gtimg.cn/q={market}{code}"

    # 市场前缀映射
    MARKET_PREFIX = {"SH": "sh", "SZ": "sz", "BJ": "bj"}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(name="tencent", config=config)
        self._circuit_breaker = get_circuit_breaker("tencent")

    def _build_symbol(self, stock_code: str) -> str:
        """
        构建腾讯财经代码格式

        Args:
            stock_code: 标准股票代码

        Returns:
            腾讯格式代码（如 sh600519）
        """
        code = self._normalize_stock_code(stock_code)
        market = self._determine_market(stock_code)
        prefix = self.MARKET_PREFIX.get(market, "sz")
        return f"{prefix}{code}"

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
            logger.warning("[tencent] 断路器已断开，跳过K线请求")
            return None
        try:
            result = self._fetch_kline_impl(stock_code, days, freq)
            self._circuit_breaker.record_success()
            return result
        except Exception as e:
            self._circuit_breaker.record_failure()
            logger.error(f"[tencent] 获取K线失败: {stock_code}, {e}")
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
        import requests

        symbol = self._build_symbol(stock_code)

        # 腾讯日K线接口
        url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},{freq},,{days},,qfq"
        resp = requests.get(url, timeout=10)

        if resp.status_code != 200:
            return None

        data = resp.json()
        stock_data = data.get("data", {}).get(symbol, {})
        kline_data = stock_data.get("qfq" + freq, stock_data.get(freq, []))

        if not kline_data:
            logger.warning(f"[tencent] 无K线数据: {stock_code}")
            return None

        prices = []
        for item in kline_data[-days:]:
            price = StockPrice(
                date=datetime.strptime(item[0], "%Y-%m-%d"),
                open=float(item[1]),
                close=float(item[2]),
                high=float(item[3]),
                low=float(item[4]),
                volume=int(item[5]),
            )
            prices.append(price)

        logger.info(f"[tencent] 获取K线成功: {stock_code}, {len(prices)}条")
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
            logger.warning("[tencent] 断路器已断开，跳过实时行情请求")
            return None
        try:
            result = self._fetch_realtime_quote_impl(stock_code)
            self._circuit_breaker.record_success()
            return result
        except Exception as e:
            self._circuit_breaker.record_failure()
            logger.error(f"[tencent] 获取实时行情失败: {stock_code}, {e}")
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
        import requests

        symbol = self._build_symbol(stock_code)
        url = self.QUOTE_URL.format(market=symbol[:2], code=symbol[2:])
        resp = requests.get(url, timeout=10)

        if resp.status_code != 200:
            return None

        # 解析腾讯行情数据（格式为 v_字段名="值1~值2~..."）
        text = resp.text
        parts = text.split('~')

        if len(parts) < 50:
            return None

        return {
            "stock_code": stock_code,
            "stock_name": parts[1] if len(parts) > 1 else "",
            "price": float(parts[3]) if len(parts) > 3 and parts[3] else 0,
            "close": float(parts[3]) if len(parts) > 3 and parts[3] else 0,
            "open": float(parts[5]) if len(parts) > 5 and parts[5] else 0,
            "volume": int(float(parts[6])) if len(parts) > 6 and parts[6] else 0,
            "high": float(parts[33]) if len(parts) > 33 and parts[33] else 0,
            "low": float(parts[34]) if len(parts) > 34 and parts[34] else 0,
            "pe_ttm": float(parts[39]) if len(parts) > 39 and parts[39] else None,
            "market_cap": float(parts[45]) if len(parts) > 45 and parts[45] else None,
        }

    def fetch_financial_reports(self, stock_code: str) -> Optional[List[FinancialReport]]:
        """获取财务报告（腾讯接口不提供，返回 None）"""
        logger.debug(f"[tencent] 不支持财务数据获取: {stock_code}")
        return None
