"""股票数据模型"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class StockPrice(BaseModel):
    """股票价格数据"""
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: Optional[float] = None  # 成交额
    
    # 复权价格
    adj_close: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d")
        }


class FinancialReport(BaseModel):
    """财务报告数据"""
    report_date: datetime
    report_type: str  # 年报、季报等
    
    # 利润表关键指标
    revenue: Optional[float] = None  # 营业收入
    net_profit: Optional[float] = None  # 净利润
    gross_profit: Optional[float] = None  # 毛利润
    
    # 资产负债表关键指标
    total_assets: Optional[float] = None  # 总资产
    total_liabilities: Optional[float] = None  # 总负债
    shareholders_equity: Optional[float] = None  # 股东权益
    
    # 现金流量表
    operating_cash_flow: Optional[float] = None  # 经营现金流
    
    # 关键比率
    roe: Optional[float] = None  # 净资产收益率
    roa: Optional[float] = None  # 总资产收益率
    gross_margin: Optional[float] = None  # 毛利率
    net_margin: Optional[float] = None  # 净利率
    debt_ratio: Optional[float] = None  # 资产负债率


class StockData(BaseModel):
    """股票完整数据"""
    # 基础信息
    stock_code: str = Field(..., description="股票代码，如 000001.SZ")
    stock_name: str = Field(..., description="股票名称")
    industry: Optional[str] = None  # 所属行业
    list_date: Optional[datetime] = None  # 上市日期
    
    # 价格数据
    prices: List[StockPrice] = Field(default_factory=list)
    
    # 财务数据
    financial_reports: List[FinancialReport] = Field(default_factory=list)
    
    # 估值指标
    pe_ttm: Optional[float] = None  # 市盈率TTM
    pb: Optional[float] = None  # 市净率
    ps_ttm: Optional[float] = None  # 市销率
    dividend_yield: Optional[float] = None  # 股息率
    market_cap: Optional[float] = None  # 总市值
    
    # 技术指标 (由TechnicalAnalyst计算)
    technical_indicators: Dict[str, Any] = Field(default_factory=dict)
    
    # 情绪数据
    sentiment_score: Optional[float] = None  # 情绪评分 0-100
    hot_topics: List[str] = Field(default_factory=list)  # 相关热点题材
    
    # 新闻/公告
    recent_news: List[Dict[str, Any]] = Field(default_factory=list)
    recent_announcements: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 数据更新时间
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def get_latest_price(self) -> Optional[StockPrice]:
        """获取最新价格"""
        if not self.prices:
            return None
        return max(self.prices, key=lambda x: x.date)
    
    def get_latest_financial_report(self) -> Optional[FinancialReport]:
        """获取最新财务报告"""
        if not self.financial_reports:
            return None
        return max(self.financial_reports, key=lambda x: x.report_date)
    
    @property
    def current_price(self) -> Optional[float]:
        """当前价格"""
        latest = self.get_latest_price()
        return latest.close if latest else None