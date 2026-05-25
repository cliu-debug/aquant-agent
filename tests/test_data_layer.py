"""数据层单元测试"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from astock_agents.models.stock_data import StockData, StockPrice, FinancialReport
from astock_agents.data.base_client import BaseDataClient
from astock_agents.data.tencent_client import TencentClient
from astock_agents.data.akshare_client import AkshareClient
from astock_agents.data.mootdx_client import MootdxClient
from astock_agents.data.manager import DataManager


# ==================== 数据模型测试 ====================

class TestStockPrice:
    """StockPrice模型测试"""

    def test_create_stock_price(self):
        """测试创建股票价格数据"""
        price = StockPrice(
            date=datetime(2024, 1, 1),
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1000000
        )
        assert price.date == datetime(2024, 1, 1)
        assert price.open == 10.0
        assert price.close == 10.2
        assert price.amount is None

    def test_stock_price_with_optional_fields(self):
        """测试带可选字段的价格数据"""
        price = StockPrice(
            date=datetime(2024, 1, 1),
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            volume=1000000,
            amount=10200000.0,
            adj_close=10.15
        )
        assert price.amount == 10200000.0
        assert price.adj_close == 10.15


class TestFinancialReport:
    """FinancialReport模型测试"""

    def test_create_financial_report(self):
        """测试创建财务报告"""
        report = FinancialReport(
            report_date=datetime(2024, 3, 31),
            report_type="一季报",
            revenue=1000000000.0,
            net_profit=100000000.0,
            roe=0.15
        )
        assert report.report_date == datetime(2024, 3, 31)
        assert report.report_type == "一季报"
        assert report.revenue == 1000000000.0


class TestStockData:
    """StockData模型测试"""

    def test_create_stock_data(self):
        """测试创建股票数据"""
        stock = StockData(stock_code="600519.SH", stock_name="贵州茅台")
        assert stock.stock_code == "600519.SH"
        assert stock.prices == []

    def test_get_latest_price(self):
        """测试获取最新价格"""
        stock = StockData(stock_code="600519.SH", stock_name="贵州茅台")
        assert stock.get_latest_price() is None

        for i in range(3):
            stock.prices.append(StockPrice(
                date=datetime(2024, 1, 1) + timedelta(days=i),
                open=100.0, high=101.0, low=99.0,
                close=100.0 + i, volume=1000000
            ))

        latest = stock.get_latest_price()
        assert latest is not None
        assert latest.close == 102.0

    def test_current_price_property(self):
        """测试当前价格属性"""
        stock = StockData(stock_code="600519.SH", stock_name="贵州茅台")
        assert stock.current_price is None

        stock.prices.append(StockPrice(
            date=datetime(2024, 1, 1),
            open=100.0, high=101.0, low=99.0,
            close=100.5, volume=1000000
        ))
        assert stock.current_price == 100.5


# ==================== 基类客户端测试 ====================

class TestBaseDataClient:
    """BaseDataClient基类测试"""

    def test_normalize_stock_code(self):
        """测试股票代码标准化"""
        # 使用具体子类测试
        client = TencentClient(config={"enabled": False})

        assert client._normalize_stock_code("600519.SH") == "600519"
        assert client._normalize_stock_code("000001.SZ") == "000001"
        assert client._normalize_stock_code("600519") == "600519"

    def test_determine_market(self):
        """测试市场判断"""
        client = TencentClient(config={"enabled": False})

        assert client._determine_market("600519.SH") == "SH"
        assert client._determine_market("000001.SZ") == "SZ"
        assert client._determine_market("430047.BJ") == "BJ"

    def test_enabled_property(self):
        """测试enabled属性"""
        client_enabled = TencentClient(config={"enabled": True})
        client_disabled = TencentClient(config={"enabled": False})

        assert client_enabled.enabled is True
        assert client_disabled.enabled is False


# ==================== 腾讯客户端测试 ====================

class TestTencentClient:
    """腾讯财经客户端测试"""

    def test_build_symbol(self):
        """测试构建腾讯代码格式"""
        client = TencentClient(config={"enabled": False})

        assert client._build_symbol("600519.SH") == "sh600519"
        assert client._build_symbol("000001.SZ") == "sz000001"

    def test_fetch_kline_returns_none_when_no_data(self):
        """测试无数据时返回None"""
        client = TencentClient(config={"enabled": False})
        # 未连接时返回None
        result = client.fetch_kline("600519.SH")
        assert result is None

    def test_fetch_realtime_quote_returns_none_when_no_data(self):
        """测试实时行情无数据"""
        client = TencentClient(config={"enabled": False})
        result = client.fetch_realtime_quote("600519.SH")
        assert result is None

    def test_fetch_financial_reports_returns_none(self):
        """测试腾讯不支持财务数据"""
        client = TencentClient(config={"enabled": False})
        result = client.fetch_financial_reports("600519.SH")
        assert result is None


# ==================== Akshare客户端测试 ====================

class TestAkshareClient:
    """Akshare客户端测试"""

    def test_safe_float(self):
        """测试安全浮点转换"""
        assert AkshareClient._safe_float(10.5) == 10.5
        assert AkshareClient._safe_float("10.5") == 10.5
        assert AkshareClient._safe_float("10.5%") == 10.5
        assert AkshareClient._safe_float("100亿") == 100.0
        assert AkshareClient._safe_float(None) is None
        assert AkshareClient._safe_float("abc") is None

    def test_fetch_financial_reports_returns_none_when_no_data(self):
        """测试无数据时返回None"""
        client = AkshareClient(config={"enabled": False})
        result = client.fetch_financial_reports("600519.SH")
        assert result is None


# ==================== Mootdx客户端测试 ====================

class TestMootdxClient:
    """Mootdx客户端测试"""

    def test_market_map(self):
        """测试市场映射"""
        assert MootdxClient.MARKET_MAP["SZ"] == 0
        assert MootdxClient.MARKET_MAP["SH"] == 1

    def test_fetch_kline_returns_none_when_no_connection(self):
        """测试无连接时返回None"""
        client = MootdxClient(config={"enabled": False})
        result = client.fetch_kline("600519.SH")
        assert result is None

    def test_fetch_financial_reports_returns_none(self):
        """测试mootdx不支持财务数据"""
        client = MootdxClient(config={"enabled": False})
        result = client.fetch_financial_reports("600519.SH")
        assert result is None


# ==================== 数据管理器测试 ====================

class TestDataManager:
    """数据管理器测试"""

    def test_create_data_manager(self):
        """测试创建数据管理器"""
        manager = DataManager()
        assert manager is not None
        assert hasattr(manager, "get_stock_data")

    def test_create_with_all_disabled(self):
        """测试所有数据源禁用"""
        config = {
            "data_sources": {
                "mootdx": {"enabled": False},
                "akshare": {"enabled": False},
                "tencent": {"enabled": False},
            }
        }
        manager = DataManager(config=config)
        assert len(manager._clients) == 0

    def test_clear_cache(self):
        """测试清空缓存"""
        manager = DataManager()
        manager.clear_cache()
        # 不应抛出异常


# ==================== 异常处理测试 ====================

class TestErrorHandling:
    """异常处理测试"""

    def test_empty_stock_code(self):
        """测试空股票代码"""
        client = TencentClient(config={"enabled": False})
        result = client._normalize_stock_code("")
        assert result == ""

    def test_empty_data_handling(self):
        """测试空数据处理"""
        stock = StockData(stock_code="600519.SH", stock_name="贵州茅台")
        assert stock.get_latest_price() is None
        assert stock.get_latest_financial_report() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
