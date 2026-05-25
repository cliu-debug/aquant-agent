"""投资系统数据模型 - 自选股、模拟交易、交易记录、选股条件"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


# ==================== 枚举定义 ====================

class WatchlistGroup(str, Enum):
    """自选股分组"""
    DEFAULT = "默认"
    MOMENTUM = "动量策略"
    VALUE = "价值策略"
    GROWTH = "成长策略"
    DIVIDEND = "红利策略"
    CUSTOM = "自定义"


class TradeDirection(str, Enum):
    """交易方向"""
    BUY = "买入"
    SELL = "卖出"


class TradeStatus(str, Enum):
    """交易状态"""
    PENDING = "待成交"
    FILLED = "已成交"
    CANCELLED = "已取消"
    PARTIAL = "部分成交"


class OrderType(str, Enum):
    """订单类型"""
    MARKET = "市价单"
    LIMIT = "限价单"


class ScreenerConditionType(str, Enum):
    """选股条件类型"""
    PE = "PE"
    PB = "PB"
    ROE = "ROE"
    REVENUE_GROWTH = "营收增长率"
    PROFIT_GROWTH = "利润增长率"
    MARKET_CAP = "市值"
    TURNOVER_RATE = "换手率"
    RSI = "RSI"
    MA_TREND = "均线趋势"
    VOLUME_RATIO = "量比"
    DIVIDEND_YIELD = "股息率"


class ScreenerOperator(str, Enum):
    """选股条件运算符"""
    GT = "大于"
    GTE = "大于等于"
    LT = "小于"
    LTE = "小于等于"
    BETWEEN = "区间"
    EQ = "等于"


# ==================== 自选股模型 ====================

class WatchlistItem(BaseModel):
    """自选股条目"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")})

    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    group: WatchlistGroup = Field(WatchlistGroup.DEFAULT, description="分组")
    tags: List[str] = Field(default_factory=list, description="标签")
    reason: Optional[str] = Field(None, description="加入自选理由")
    target_price: Optional[float] = Field(None, description="目标价")
    stop_loss: Optional[float] = Field(None, description="止损价")
    added_at: datetime = Field(default_factory=datetime.now, description="加入时间")
    last_analyzed_at: Optional[datetime] = Field(None, description="最近分析时间")
    last_signal: Optional[str] = Field(None, description="最近信号")
    notes: Optional[str] = Field(None, description="备注")


class WatchlistGroupInfo(BaseModel):
    """自选股分组信息"""
    name: str = Field(..., description="分组名称")
    count: int = Field(0, description="股票数量")
    description: Optional[str] = Field(None, description="分组描述")


# ==================== 选股器模型 ====================

class ScreenerCondition(BaseModel):
    """选股条件"""
    field: ScreenerConditionType = Field(..., description="条件字段")
    operator: ScreenerOperator = Field(..., description="运算符")
    value: Any = Field(..., description="条件值（单值或区间[min,max]）")


class ScreenerPreset(BaseModel):
    """选股预设方案"""
    name: str = Field(..., description="方案名称")
    description: Optional[str] = Field(None, description="方案描述")
    conditions: List[ScreenerCondition] = Field(default_factory=list, description="条件列表")


class ScreenerResult(BaseModel):
    """选股结果"""
    stock_code: str
    stock_name: str
    industry: Optional[str] = None
    match_score: int = Field(0, description="匹配度评分0-100")
    matched_conditions: List[str] = Field(default_factory=list, description="匹配的条件")
    key_metrics: Dict[str, Any] = Field(default_factory=dict, description="关键指标快照")


class ScreenerResponse(BaseModel):
    """选股响应"""
    preset_name: str = Field(..., description="使用的方案名称")
    total_matched: int = Field(0, description="匹配总数")
    results: List[ScreenerResult] = Field(default_factory=list, description="选股结果")
    scanned_at: datetime = Field(default_factory=datetime.now)


# ==================== 模拟交易模型 ====================

class TradeOrder(BaseModel):
    """交易订单"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")})

    order_id: str = Field(..., description="订单ID")
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    direction: TradeDirection = Field(..., description="交易方向")
    order_type: OrderType = Field(OrderType.MARKET, description="订单类型")
    quantity: int = Field(..., description="数量（股）")
    price: Optional[float] = Field(None, description="委托价格（限价单必填）")
    filled_price: Optional[float] = Field(None, description="成交价格")
    filled_quantity: int = Field(0, description="成交数量")
    status: TradeStatus = Field(TradeStatus.PENDING, description="订单状态")
    commission: float = Field(0, description="佣金")
    stamp_tax: float = Field(0, description="印花税")
    reason: Optional[str] = Field(None, description="交易理由")
    signal_source: Optional[str] = Field(None, description="信号来源（如技术分析）")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    filled_at: Optional[datetime] = Field(None, description="成交时间")


class Position(BaseModel):
    """持仓"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")})

    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    quantity: int = Field(..., description="持仓数量")
    available_quantity: int = Field(..., description="可用数量")
    avg_cost: float = Field(..., description="持仓均价")
    current_price: Optional[float] = Field(None, description="当前价格")
    market_value: Optional[float] = Field(None, description="市值")
    unrealized_pnl: Optional[float] = Field(None, description="浮动盈亏")
    unrealized_pnl_pct: Optional[float] = Field(None, description="浮动盈亏比例%")
    realized_pnl: float = Field(0, description="已实现盈亏")
    first_buy_at: Optional[datetime] = Field(None, description="首次买入时间")
    last_trade_at: Optional[datetime] = Field(None, description="最近交易时间")


class Portfolio(BaseModel):
    """投资组合"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")})

    portfolio_id: str = Field("default", description="组合ID")
    name: str = Field("默认组合", description="组合名称")
    initial_capital: float = Field(1000000.0, description="初始资金")
    available_cash: float = Field(1000000.0, description="可用现金")
    positions: List[Position] = Field(default_factory=list, description="持仓列表")
    total_market_value: Optional[float] = Field(None, description="总市值")
    total_pnl: Optional[float] = Field(None, description="总盈亏")
    total_pnl_pct: Optional[float] = Field(None, description="总盈亏比例%")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ==================== 交易复盘模型 ====================

class TradeRecord(BaseModel):
    """完整交易记录（一笔买入到卖出的完整周期）"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")})

    record_id: str = Field(..., description="记录ID")
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    buy_price: float = Field(..., description="买入均价")
    buy_quantity: int = Field(..., description="买入数量")
    buy_time: datetime = Field(..., description="买入时间")
    buy_reason: Optional[str] = Field(None, description="买入理由")
    sell_price: Optional[float] = Field(None, description="卖出均价")
    sell_quantity: Optional[int] = Field(None, description="卖出数量")
    sell_time: Optional[datetime] = Field(None, description="卖出时间")
    sell_reason: Optional[str] = Field(None, description="卖出理由")
    holding_days: Optional[int] = Field(None, description="持仓天数")
    realized_pnl: Optional[float] = Field(None, description="已实现盈亏")
    realized_pnl_pct: Optional[float] = Field(None, description="盈亏比例%")
    max_drawdown_pct: Optional[float] = Field(None, description="持仓期间最大回撤%")
    status: str = Field("持有中", description="状态：持有中/已平仓")
    signal_at_buy: Optional[str] = Field(None, description="买入时信号")
    signal_at_sell: Optional[str] = Field(None, description="卖出时信号")


class ReviewReport(BaseModel):
    """复盘报告"""
    model_config = ConfigDict(json_encoders={datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")})

    period: str = Field(..., description="复盘周期（如2024-Q1）")
    total_trades: int = Field(0, description="总交易次数")
    win_trades: int = Field(0, description="盈利次数")
    loss_trades: int = Field(0, description="亏损次数")
    win_rate: float = Field(0, description="胜率%")
    total_pnl: float = Field(0, description="总盈亏")
    avg_pnl_per_trade: float = Field(0, description="平均每笔盈亏")
    avg_holding_days: float = Field(0, description="平均持仓天数")
    max_single_gain_pct: Optional[float] = Field(None, description="单笔最大盈利%")
    max_single_loss_pct: Optional[float] = Field(None, description="单笔最大亏损%")
    profit_factor: Optional[float] = Field(None, description="盈亏比（总盈利/总亏损）")
    best_stock: Optional[str] = Field(None, description="最佳标的")
    worst_stock: Optional[str] = Field(None, description="最差标的")
    common_mistakes: List[str] = Field(default_factory=list, description="常见错误")
    improvement_suggestions: List[str] = Field(default_factory=list, description="改进建议")
    records: List[TradeRecord] = Field(default_factory=list, description="交易记录明细")
    generated_at: datetime = Field(default_factory=datetime.now)
