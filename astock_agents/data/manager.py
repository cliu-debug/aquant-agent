"""数据管理器 - 统一多数据源管理、优先级降级和缓存"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger
from cachetools import TTLCache

from astock_agents.data.base_client import BaseDataClient
from astock_agents.data.mootdx_client import MootdxClient
from astock_agents.data.akshare_client import AkshareClient
from astock_agents.data.tencent_client import TencentClient
from astock_agents.data.circuit_breaker import get_all_circuit_breaker_stats
from astock_agents.models.stock_data import StockData, StockPrice, FinancialReport


class DataManager:
    """
    统一数据管理器

    职责：
    1. 管理多个数据源客户端
    2. 按优先级尝试各数据源，失败时自动降级
    3. 提供数据缓存，减少重复请求
    """

    # 默认数据源优先级：K线数据
    KLINE_PRIORITY = ["mootdx", "akshare", "tencent"]
    # 默认数据源优先级：实时行情
    QUOTE_PRIORITY = ["tencent", "mootdx", "akshare"]
    # 默认数据源优先级：财务数据
    FINANCIAL_PRIORITY = ["akshare"]

    # 缓存配置
    CACHE_TTL = 300  # 5分钟缓存
    CACHE_MAX_SIZE = 100

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据管理器

        Args:
            config: 配置字典，包含各数据源的配置
        """
        self.config = config or {}
        data_source_config = self.config.get("data_sources", {})

        # 初始化各数据源客户端
        self._clients: Dict[str, BaseDataClient] = {}

        # 按配置初始化数据源
        client_classes = {
            "mootdx": MootdxClient,
            "akshare": AkshareClient,
            "tencent": TencentClient,
        }

        for name, cls in client_classes.items():
            source_config = data_source_config.get(name, {"enabled": True})
            if source_config.get("enabled", True):
                try:
                    self._clients[name] = cls(config=source_config)
                    logger.info(f"[DataManager] 数据源已注册: {name}")
                except Exception as e:
                    logger.warning(f"[DataManager] 数据源初始化失败: {name}, {e}")

        # 初始化缓存
        self._kline_cache = TTLCache(maxsize=self.CACHE_MAX_SIZE, ttl=self.CACHE_TTL)
        self._quote_cache = TTLCache(maxsize=self.CACHE_MAX_SIZE, ttl=60)  # 行情缓存1分钟
        self._financial_cache = TTLCache(maxsize=self.CACHE_MAX_SIZE, ttl=self.CACHE_TTL * 4)  # 财务缓存20分钟

        logger.info(f"[DataManager] 初始化完成，已注册 {len(self._clients)} 个数据源")

    def get_stock_data(
        self,
        stock_code: str,
        stock_name: Optional[str] = None,
        days: int = 120,
    ) -> tuple:
        """获取股票完整数据

        按优先级从多个数据源获取数据，自动降级和合并

        Args:
            stock_code: 股票代码（如 600519.SH）
            stock_name: 股票名称（可选，自动获取）
            days: K线天数

        Returns:
            (StockData, data_source_info) 元组
            - StockData: 完整股票数据
            - data_source_info: 数据源标注信息字典
        """
        logger.info(f"[DataManager] 获取股票数据: {stock_code}")

        data_source_info = {
            "sources_used": {},
            "sources_unavailable": [],
            "quality_warnings": [],
        }

        # 1. 获取K线数据
        prices, kline_source = self._fetch_with_fallback_tracked(
            "kline", stock_code, days=days
        )
        if kline_source:
            data_source_info["sources_used"]["kline"] = kline_source
        else:
            data_source_info["sources_unavailable"].append("kline")
            data_source_info["quality_warnings"].append("K线数据不可用，技术分析可能受限")

        # 2. 获取实时行情（补充估值数据）
        quote, quote_source = self._fetch_with_fallback_tracked(
            "quote", stock_code
        )
        if quote_source:
            data_source_info["sources_used"]["quote"] = quote_source
        else:
            data_source_info["sources_unavailable"].append("quote")
            data_source_info["quality_warnings"].append("实时行情数据不可用，估值分析可能受限")

        # 3. 获取财务数据
        financial_reports, financial_source = self._fetch_with_fallback_tracked(
            "financial", stock_code
        )
        if financial_source:
            data_source_info["sources_used"]["financial"] = financial_source
        else:
            data_source_info["sources_unavailable"].append("financial")
            data_source_info["quality_warnings"].append("财务数据不可用，基本面分析可能受限")

        # 4. 获取股票基本信息
        stock_info = self._fetch_stock_info(stock_code)

        # 5. 数据质量检查
        if prices and len(prices) < 60:
            data_source_info["quality_warnings"].append(
                f"K线数据仅{len(prices)}天（建议120天以上），技术指标可靠性降低"
            )

        # 6. 组装 StockData
        stock_data = StockData(
            stock_code=stock_code,
            stock_name=stock_name or self._extract_stock_name(quote, stock_info, stock_code),
            industry=self._extract_industry(stock_info),
            prices=prices or [],
            financial_reports=financial_reports or [],
            pe_ttm=self._extract_valuation(quote, "pe_ttm"),
            pb=self._extract_valuation(quote, "pb"),
            market_cap=self._extract_valuation(quote, "market_cap"),
            updated_at=datetime.now(),
        )

        logger.info(
            f"[DataManager] 数据获取完成: {stock_data.stock_name} "
            f"(K线{len(stock_data.prices)}条, 财报{len(stock_data.financial_reports)}条, "
            f"数据源={data_source_info['sources_used']})"
        )

        # 持久化数据源状态到数据库
        self._persist_data_source_status(data_source_info)

        return stock_data, data_source_info

    def _fetch_with_fallback_tracked(
        self,
        data_type: str,
        stock_code: str,
        **kwargs,
    ) -> tuple:
        """按优先级尝试各数据源，返回数据和实际使用的数据源名称

        Args:
            data_type: 数据类型 kline/quote/financial
            stock_code: 股票代码
            **kwargs: 额外参数

        Returns:
            (data, source_name) 元组，data为获取到的数据，source_name为数据源名称
        """
        priority_map = {
            "kline": self.KLINE_PRIORITY,
            "quote": self.QUOTE_PRIORITY,
            "financial": self.FINANCIAL_PRIORITY,
        }
        priority = priority_map.get(data_type, list(self._clients.keys()))

        cache_map = {
            "kline": self._kline_cache,
            "quote": self._quote_cache,
            "financial": self._financial_cache,
        }
        cache = cache_map.get(data_type)
        cache_key = f"{data_type}:{stock_code}"

        if cache is not None and cache_key in cache:
            logger.debug(f"[DataManager] 缓存命中: {cache_key}")
            cached_source = getattr(self, '_cache_source_map', {}).get(cache_key, "cache")
            return cache[cache_key], cached_source

        for source_name in priority:
            client = self._clients.get(source_name)
            if client is None or not client.enabled:
                continue

            try:
                if data_type == "kline":
                    result = client.fetch_kline(stock_code, **kwargs)
                elif data_type == "quote":
                    result = client.fetch_realtime_quote(stock_code)
                elif data_type == "financial":
                    result = client.fetch_financial_reports(stock_code)
                else:
                    continue

                if result is not None:
                    if cache is not None:
                        cache[cache_key] = result
                    if not hasattr(self, '_cache_source_map'):
                        self._cache_source_map: Dict[str, str] = {}
                    self._cache_source_map[cache_key] = source_name
                    logger.debug(f"[DataManager] 数据源 {source_name} 获取 {data_type} 成功")
                    return result, source_name

            except Exception as e:
                logger.warning(f"[DataManager] 数据源 {source_name} 获取 {data_type} 失败: {e}")
                continue

        logger.warning(f"[DataManager] 所有数据源均无法获取 {data_type}: {stock_code}")
        return None, None

    def _persist_data_source_status(self, data_source_info: Dict[str, Any]) -> None:
        """将数据源状态持久化到数据库

        Args:
            data_source_info: 数据源标注信息
        """
        try:
            from astock_agents.db.database import Database
            db = Database()
            for data_type, source_name in data_source_info.get("sources_used", {}).items():
                db.save_data_source_status(
                    source_name=source_name,
                    data_type=data_type,
                    status="available",
                    message="数据获取成功",
                )
            for data_type in data_source_info.get("sources_unavailable", []):
                db.save_data_source_status(
                    source_name="all",
                    data_type=data_type,
                    status="unavailable",
                    message="所有数据源均不可用",
                )
        except Exception as e:
            logger.debug(f"[DataManager] 数据源状态持久化失败（非致命）: {e}")

    def _fetch_with_fallback(
        self,
        data_type: str,
        stock_code: str,
        **kwargs
    ):
        """
        按优先级尝试各数据源，失败时自动降级

        Args:
            data_type: 数据类型 kline/quote/financial
            stock_code: 股票代码
            **kwargs: 额外参数

        Returns:
            获取到的数据，所有数据源失败返回 None
        """
        # 确定优先级
        priority_map = {
            "kline": self.KLINE_PRIORITY,
            "quote": self.QUOTE_PRIORITY,
            "financial": self.FINANCIAL_PRIORITY,
        }
        priority = priority_map.get(data_type, list(self._clients.keys()))

        # 检查缓存
        cache_map = {
            "kline": self._kline_cache,
            "quote": self._quote_cache,
            "financial": self._financial_cache,
        }
        cache = cache_map.get(data_type)
        cache_key = f"{data_type}:{stock_code}"

        if cache is not None and cache_key in cache:
            logger.debug(f"[DataManager] 缓存命中: {cache_key}")
            return cache[cache_key]

        # 按优先级尝试各数据源
        for source_name in priority:
            client = self._clients.get(source_name)
            if client is None or not client.enabled:
                continue

            try:
                if data_type == "kline":
                    result = client.fetch_kline(stock_code, **kwargs)
                elif data_type == "quote":
                    result = client.fetch_realtime_quote(stock_code)
                elif data_type == "financial":
                    result = client.fetch_financial_reports(stock_code)
                else:
                    continue

                if result is not None:
                    # 写入缓存
                    if cache is not None:
                        cache[cache_key] = result
                    logger.debug(f"[DataManager] 数据源 {source_name} 获取 {data_type} 成功")
                    return result

            except Exception as e:
                logger.warning(f"[DataManager] 数据源 {source_name} 获取 {data_type} 失败: {e}")
                continue

        logger.warning(f"[DataManager] 所有数据源均无法获取 {data_type}: {stock_code}")
        return None

    def _fetch_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取股票基本信息"""
        akshare_client = self._clients.get("akshare")
        if akshare_client and hasattr(akshare_client, "fetch_stock_info"):
            try:
                return akshare_client.fetch_stock_info(stock_code)
            except Exception as e:
                logger.debug(f"[DataManager] 获取股票信息失败: {e}")
        return None

    @staticmethod
    def _extract_stock_name(
        quote: Optional[Dict],
        stock_info: Optional[Dict],
        stock_code: str
    ) -> str:
        """从行情或信息中提取股票名称"""
        if quote and quote.get("stock_name"):
            return quote["stock_name"]
        if stock_info and stock_info.get("stock_name"):
            return stock_info["stock_name"]
        return stock_code

    @staticmethod
    def _extract_industry(stock_info: Optional[Dict]) -> Optional[str]:
        """从股票信息中提取行业"""
        if stock_info:
            return stock_info.get("industry")
        return None

    @staticmethod
    def _extract_valuation(quote: Optional[Dict], key: str) -> Optional[float]:
        """从行情数据中提取估值指标"""
        if quote:
            value = quote.get(key)
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    pass
        return None

    def clear_cache(self):
        """清空所有缓存"""
        self._kline_cache.clear()
        self._quote_cache.clear()
        self._financial_cache.clear()
        logger.info("[DataManager] 缓存已清空")

    def get_circuit_breaker_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有断路器状态

        Returns:
            以断路器名称为键、统计信息为值的字典
        """
        return get_all_circuit_breaker_stats()

    def health_check(self) -> Dict[str, Any]:
        """
        健康检查，包含数据源和断路器状态

        Returns:
            健康状态字典
        """
        cb_stats = self.get_circuit_breaker_stats()
        # 检查是否有断路器处于OPEN状态
        open_breakers = [name for name, stats in cb_stats.items() if stats["state"] == "OPEN"]
        healthy = len(open_breakers) == 0

        return {
            "status": "healthy" if healthy else "degraded",
            "data_sources": list(self._clients.keys()),
            "circuit_breakers": cb_stats,
            "open_breakers": open_breakers,
        }
