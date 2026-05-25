"""数据层单元测试"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

from astock_agents.models.stock_data import StockData, StockPrice, FinancialReport
from astock_agents.data.base_client import BaseDataClient
from astock_agents.data.tencent_client import TencentClient
from astock_agents.data.akshare_client import AkshareClient
from astock_agents.data.mootdx_client import MootdxClient
from astock_agents.data.data_manager import DataManager


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
        assert price.high == 10.5
        assert price.low == 9.8
        assert price.close == 10.2
        assert price.volume == 1000000
        assert price.amount is None
        assert price.adj_close is None
    
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
        assert report.net_profit == 100000000.0
        assert report.roe == 0.15


class TestStockData:
    """StockData模型测试"""
    
    def test_create_stock_data(self):
        """测试创建股票数据"""
        stock = StockData(
            stock_code="600519.SH",
            stock_name="贵州茅台"
        )
        
        assert stock.stock_code == "600519.SH"
        assert stock.stock_name == "贵州茅台"
        assert stock.prices == []
        assert stock.financial_reports == []
    
    def test_add_prices(self):
        """测试添加价格数据"""
        stock = StockData(
            stock_code="600519.SH",
            stock_name="贵州茅台"
        )
        
        # 添加多日价格
        for i in range(5):
            price = StockPrice(
                date=datetime(2024, 1, 1) + timedelta(days=i),
                open=100.0 + i,
                high=101.0 + i,
                low=99.0 + i,
                close=100.5 + i,
                volume=1000000
            )
            stock.prices.append(price)
        
        assert len(stock.prices) == 5
        assert stock.prices[0].date == datetime(2024, 1, 1)
    
    def test_get_latest_price(self):
        """测试获取最新价格"""
        stock = StockData(
            stock_code="600519.SH",
            stock_name="贵州茅台"
        )
        
        # 无价格数据
        assert stock.get_latest_price() is None
        
        # 添加价格
        for i in range(3):
            price = StockPrice(
                date=datetime(2024, 1, 1) + timedelta(days=i),
                open=100.0,
                high=101.0,
                low=99.0,
                close=100.0 + i,
                volume=1000000
            )
            stock.prices.append(price)
        
        latest = stock.get_latest_price()
        assert latest is not None
        assert latest.date == datetime(2024, 1, 3)
        assert latest.close == 102.0
    
    def test_current_price_property(self):
        """测试当前价格属性"""
        stock = StockData(
            stock_code="600519.SH",
            stock_name="贵州茅台"
        )
        
        # 无价格
        assert stock.current_price is None
        
        # 有价格
        stock.prices.append(StockPrice(
            date=datetime(2024, 1, 1),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000000
        ))
        
        assert stock.current_price == 100.5


# ==================== 数据客户端测试 ====================

class TestTencentClient:
    """腾讯财经客户端测试"""
    
    def test_normalize_code_sh(self):
        """测试上海股票代码转换"""
        client = TencentClient(enabled=False)
        
        assert client._normalize_code("600519.SH") == "sh600519"
        assert client._normalize_code("600519.SS") == "sh600519"
    
    def test_normalize_code_sz(self):
        """测试深圳股票代码转换"""
        client = TencentClient(enabled=False)
        
        assert client._normalize_code("000001.SZ") == "sz000001"
    
    def test_disabled_client(self):
        """测试禁用的客户端"""
        client = TencentClient(enabled=False)
        
        # 禁用的客户端应返回空数据
        assert client.get_kline("600519.SH") == []
        assert client.get_realtime_quote("600519.SH") is None
        assert client.get_financial_data("600519.SH") is None
    
    def test_parse_tencent_data(self):
        """测试解析腾讯数据"""
        client = TencentClient(enabled=False)
        
        # 模拟腾讯返回的数据格式
        mock_data = 'v_sh600519="1~贵州茅台~600519~1800.00~1780.00~1790.00~1810.00~1785.00~10000000~18000000000~~~~~~~0.56~20.5~~35.2~~~~~"'
        
        result = client._parse_tencent_data(mock_data, "sh600519")
        
        assert result is not None
        assert result["code"] == "600519"
        assert result["name"] == "贵州茅台"
        assert result["price"] == 1800.00
    
    @patch('requests.Session.get')
    def test_get_realtime_quote(self, mock_get):
        """测试获取实时行情"""
        client = TencentClient(enabled=True)
        
        # 模拟响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'v_sh600519="1~贵州茅台~600519~1800.00~1780.00~1790.00~1810.00~1785.00~10000000~18000000000~~~~~~~0.56~20.5~~35.2~~~~~"'
        mock_response.encoding = 'gbk'
        mock_get.return_value = mock_response
        
        result = client.get_realtime_quote("600519.SH")
        
        assert result is not None
        assert result["name"] == "贵州茅台"


class TestAkshareClient:
    """Akshare客户端测试"""
    
    def test_disabled_client(self):
        """测试禁用的客户端"""
        client = AkshareClient(enabled=False)
        
        assert client.get_kline("600519.SH") == []
        assert client.get_realtime_quote("600519.SH") is None
    
    def test_is_available(self):
        """测试可用性检查"""
        client = AkshareClient(enabled=True)
        # akshare应该可用
        assert client.is_available() is True


class TestMootdxClient:
    """Mootdx客户端测试"""
    
    def test_disabled_client(self):
        """测试禁用的客户端"""
        client = MootdxClient(enabled=False)
        
        assert client.get_kline("600519.SH") == []
        assert client.get_realtime_quote("600519.SH") is None


# ==================== 数据管理器测试 ====================

class TestDataManager:
    """数据管理器测试"""
    
    def test_create_data_manager(self):
        """测试创建数据管理器"""
        manager = DataManager()
        
        assert manager is not None
        assert hasattr(manager, 'get_stock_data')
    
    def test_data_manager_with_disabled_clients(self):
        """测试所有客户端禁用时的行为"""
        manager = DataManager(
            use_tencent=False,
            use_akshare=False,
            use_mootdx=False
        )
        
        # 应该优雅处理无可用数据源的情况
        # 这里不抛出异常，而是返回空数据或None
        result = manager.get_stock_data("600519.SH")
        # 结果可能是None或空的StockData
        assert result is None or (isinstance(result, StockData) and len(result.prices) == 0)


# ==================== 缓存测试 ====================

class TestCaching:
    """缓存功能测试"""
    
    def test_cache_ttl(self):
        """测试缓存过期"""
        client = TencentClient(enabled=False)
        
        # 默认缓存5分钟
        assert client._cache_ttl == 300
    
    def test_cache_key_generation(self):
        """测试缓存key生成"""
        client = TencentClient(enabled=False)
        
        key1 = client._get_cache_key("kline", code="600519", period="daily")
        key2 = client._get_cache_key("kline", code="600519", period="daily")
        key3 = client._get_cache_key("kline", code="000001", period="daily")
        
        assert key1 == key2  # 相同参数生成相同key
        assert key1 != key3  # 不同参数生成不同key
    
    def test_cache_set_and_get(self):
        """测试缓存存取"""
        client = TencentClient(enabled=False)
        
        key = "test_key"
        data = {"price": 100.0}
        
        # 设置缓存
        client._set_cache(key, data)
        
        # 获取缓存
        result = client._get_from_cache(key)
        assert result == data
        
        # 不存在的key
        assert client._get_from_cache("non_existent") is None


# ==================== 异常处理测试 ====================

class TestErrorHandling:
    """异常处理测试"""
    
    def test_invalid_stock_code(self):
        """测试无效股票代码"""
        client = TencentClient(enabled=False)
        
        # 应该优雅处理无效代码
        result = client._normalize_code("")
        assert result == ""
    
    def test_empty_data_handling(self):
        """测试空数据处理"""
        stock = StockData(
            stock_code="600519.SH",
            stock_name="贵州茅台"
        )
        
        # 空数据应该返回None或空列表
        assert stock.get_latest_price() is None
        assert stock.get_latest_financial_report() is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
