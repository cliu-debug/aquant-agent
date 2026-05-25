# AStockAgents 架构文档

## 系统概述

AStockAgents 是一个基于多智能体协同的A股分析系统，采用 LangGraph 构建工作流，实现多维度、多视角的股票投资分析。

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        AStockAgents                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   数据层     │    │   智能体层   │    │   应用层     │       │
│  │              │    │              │    │              │       │
│  │ ┌──────────┐ │    │ ┌──────────┐ │    │ ┌──────────┐ │       │
│  │ │ Mootdx   │ │    │ │ Technical│ │    │ │   CLI    │ │       │
│  │ │ Client   │ │    │ │ Analyst  │ │    │ │ Interface│ │       │
│  │ └──────────┘ │    │ └──────────┘ │    │ └──────────┘ │       │
│  │ ┌──────────┐ │    │ ┌──────────┐ │    │ ┌──────────┐ │       │
│  │ │ Tencent  │ │    │ │Fundamentl│ │    │ │   Web    │ │       │
│  │ │ Client   │ │    │ │ Analyst  │ │    │ │ Interface│ │       │
│  │ └──────────┘ │    │ └──────────┘ │    │ └──────────┘ │       │
│  │ ┌──────────┐ │    │ ┌──────────┐ │    │ ┌──────────┐ │       │
│  │ │ Akshare  │ │    │ │ Sentiment│ │    │ │   API    │ │       │
│  │ │ Client   │ │    │ │ Analyst  │ │    │ │ Server   │ │       │
│  │ └──────────┘ │    │ └──────────┘ │    │ └──────────┘ │       │
│  │              │    │ ┌──────────┐ │    │              │       │
│  │ ┌──────────┐ │    │ │   Bull   │ │    │              │       │
│  │ │  Data    │ │    │ │Researcher│ │    │              │       │
│  │ │ Manager  │ │    │ └──────────┘ │    │              │       │
│  │ └──────────┘ │    │ ┌──────────┐ │    │              │       │
│  │              │    │ │   Bear   │ │    │              │       │
│  │              │    │ │Researcher│ │    │              │       │
│  │              │    │ └──────────┘ │    │              │       │
│  │              │    │ ┌──────────┐ │    │              │       │
│  │              │    │ │  Trader  │ │    │              │       │
│  │              │    │ └──────────┘ │    │              │       │
│  │              │    │ ┌──────────┐ │    │              │       │
│  │              │    │ │   Risk   │ │    │              │       │
│  │              │    │ │ Manager  │ │    │              │       │
│  │              │    │ └──────────┘ │    │              │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    工作流编排 (LangGraph)                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 核心模块

### 1. 数据层 (Data Layer)

数据层负责从多个数据源获取股票数据，实现统一的数据接口和缓存机制。

#### 数据源

| 数据源 | 功能 | 特点 |
|--------|------|------|
| Mootdx | 通达信数据接口 | K线数据、实时行情 |
| Tencent | 腾讯财经 | 实时行情、估值数据 |
| Akshare | 开源数据接口 | 财务数据、历史数据 |

#### 数据管理器

```python
class DataManager:
    """统一数据管理，实现多源优先级和自动降级"""
    
    def get_stock_data(self, stock_code: str) -> StockData:
        # 按优先级尝试各数据源
        # 失败时自动降级到下一个数据源
        pass
```

### 2. 智能体层 (Agents Layer)

智能体层包含8个专业分析智能体，各司其职又相互协作。

#### 智能体列表

| 智能体 | 职责 | 输出 |
|--------|------|------|
| TechnicalAnalyst | 技术分析 | 趋势、指标、形态、信号 |
| FundamentalAnalyst | 基本面分析 | 估值、盈利、成长评估 |
| SentimentAnalyst | 情绪分析 | 市场情绪、热点题材 |
| NewsAnalyst | 新闻分析 | 新闻解读、事件影响 |
| BullResearcher | 多头研究员 | 看涨论据 |
| BearResearcher | 空头研究员 | 看跌论据 |
| Trader | 交易员 | 综合决策 |
| RiskManager | 风险管理 | 风险评估、仓位建议 |

#### 技术分析师增强功能

新增技术指标：
- **ATR** (Average True Range) - 真实波幅，衡量波动性
- **OBV** (On-Balance Volume) - 能量潮，追踪资金流向
- **Williams %R** - 威廉指标，判断超买超卖
- **CCI** (Commodity Channel Index) - 顺势指标
- **ADX** (Average Directional Index) - 趋势强度指标

新增K线形态：
- 吞没形态（看涨/看跌）
- 孕线形态
- 早晨之星/黄昏之星
- 双底/双顶
- 头肩顶/头肩底

### 3. 工作流层 (Workflow Layer)

使用 LangGraph 构建智能体协同工作流。

#### 工作流图

```
┌─────────────┐
│   开始      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 数据获取    │
└──────┬──────┘
       │
       ├──────────────────┬──────────────────┐
       ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 技术分析    │    │ 基本面分析  │    │ 情绪分析    │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       └──────────────────┴──────────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  多空辩论   │
                   └──────┬──────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  风险评估   │
                   └──────┬──────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  最终决策   │
                   └──────┬──────┘
                          │
                          ▼
                   ┌─────────────┐
                   │   结束      │
                   └─────────────┘
```

### 4. 应用层 (Application Layer)

提供多种使用方式：
- **CLI**: 命令行界面
- **Web**: 基于FastAPI的Web界面
- **API**: RESTful API服务

## 数据模型

### StockData

```python
class StockData(BaseModel):
    stock_code: str          # 股票代码
    stock_name: str          # 股票名称
    industry: Optional[str]  # 所属行业
    prices: List[StockPrice] # 价格数据
    financial_reports: List[FinancialReport]  # 财务数据
    pe_ttm: Optional[float]  # 市盈率TTM
    pb: Optional[float]      # 市净率
    market_cap: Optional[float]  # 总市值
    technical_indicators: Dict  # 技术指标
    sentiment_score: Optional[float]  # 情绪评分
```

### AnalysisReport

```python
class AnalysisReport(BaseModel):
    stock_code: str
    stock_name: str
    technical_analysis: TechnicalAnalysis
    fundamental_analysis: FundamentalAnalysis
    sentiment_analysis: SentimentAnalysis
    risk_assessment: RiskAssessment
    final_decision: Decision
    timestamp: datetime
```

## 技术栈

| 类别 | 技术 |
|------|------|
| 框架 | LangGraph, LangChain |
| 数据 | Pandas, NumPy |
| 接口 | FastAPI, Pydantic |
| 可视化 | Matplotlib, Plotly |
| 部署 | Docker, Docker Compose |
| 测试 | Pytest |

## 扩展性设计

### 添加新数据源

```python
from astock_agents.data.base_client import BaseDataClient

class NewDataSource(BaseDataClient):
    def _fetch_kline(self, stock_code, ...):
        # 实现K线数据获取
        pass
    
    def _fetch_realtime_quote(self, stock_code):
        # 实现实时行情获取
        pass
```

### 添加新智能体

```python
from astock_agents.agents.base_agent import BaseAgent

class NewAnalyst(BaseAgent):
    def analyze(self, stock_data, **kwargs):
        # 实现分析逻辑
        pass
```

### 添加新工作流节点

```python
workflow.add_node("new_analyst", new_analyst_func)
workflow.add_edge("previous_node", "new_analyst")
workflow.add_edge("new_analyst", "next_node")
```

## 性能优化

1. **数据缓存**: 5分钟TTL缓存，减少重复请求
2. **并行分析**: 多智能体并行执行
3. **懒加载**: 按需加载数据和模型
4. **异步IO**: 非阻塞数据获取

## 安全考虑

1. **输入验证**: Pydantic模型验证所有输入
2. **错误处理**: 优雅降级，不暴露内部错误
3. **日志脱敏**: 敏感信息不记录日志
4. **API限流**: 防止滥用

## 监控与运维

- **健康检查**: `/api/health`
- **日志**: 结构化日志，支持ELK
- **指标**: Prometheus兼容指标
- **告警**: 异常自动告警
