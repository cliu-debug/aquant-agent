# AStockAgents 使用指南

## 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/astock-agents.git
cd astock-agents

# 安装依赖
pip install -r requirements.txt

# 安装项目
pip install -e .
```

### 基本使用

#### 1. 命令行Demo

```bash
# 分析单只股票
python examples/demo.py --code 600519.SH --name 贵州茅台

# 批量分析
python examples/demo.py --batch
```

#### 2. Web界面

```bash
# 启动Web服务
python -m astock_agents.web.app

# 访问 http://localhost:8000
```

#### 3. API调用

```bash
# GET请求
curl "http://localhost:8000/api/analyze?stock_code=600519.SH&stock_name=贵州茅台"

# POST请求
curl -X POST "http://localhost:8000/api/analyze" \
     -H "Content-Type: application/json" \
     -d '{"stock_code": "600519.SH", "stock_name": "贵州茅台"}'
```

#### 4. Python代码

```python
from astock_agents.agents.technical_analyst import TechnicalAnalyst
from astock_agents.models.stock_data import StockData, StockPrice

# 创建股票数据
stock = StockData(
    stock_code="600519.SH",
    stock_name="贵州茅台"
)

# 添加价格数据
for i in range(60):
    stock.prices.append(StockPrice(
        date=datetime(2024, 1, 1) + timedelta(days=i),
        open=1800.0, high=1820.0, low=1780.0, close=1810.0,
        volume=1000000
    ))

# 执行技术分析
analyst = TechnicalAnalyst()
result = analyst.analyze(stock)

print(f"趋势: {result.trend}")
print(f"信号: {result.signal.value}")
print(f"置信度: {result.confidence}%")
```

## 配置说明

### 配置文件

创建 `config.yaml`:

```yaml
# LLM配置
llm:
  default_provider: openai
  openai:
    model: gpt-4
    api_key: ${OPENAI_API_KEY}
    temperature: 0.3
  anthropic:
    model: claude-3-sonnet-20240229
    api_key: ${ANTHROPIC_API_KEY}

# 数据源配置
data_sources:
  mootdx:
    enabled: true
    timeout: 10
  tencent:
    enabled: true
    timeout: 10
  akshare:
    enabled: true

# 缓存配置
cache:
  ttl: 300  # 秒
  max_size: 1000

# 分析配置
analysis:
  default_days: 120
  confidence_threshold: 60
```

### 环境变量

```bash
# .env文件
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-xxx
LOG_LEVEL=INFO
```

## 功能详解

### 技术分析

技术分析师提供全面的技术指标计算和形态识别：

```python
from astock_agents.agents.technical_analyst import TechnicalAnalyst

analyst = TechnicalAnalyst()
result = analyst.analyze(stock_data)

# 获取技术指标
indicators = result.indicators
print(f"RSI: {indicators['rsi']['value']}")
print(f"MACD: {indicators['macd']['dif']}")
print(f"KDJ: {indicators['kdj']}")

# 获取形态识别
patterns = result.patterns
print(f"识别形态: {patterns}")

# 获取支撑阻力位
print(f"支撑位: {result.support_levels}")
print(f"阻力位: {result.resistance_levels}")
```

### 基本面分析

```python
from astock_agents.agents.fundamental_analyst import FundamentalAnalyst

analyst = FundamentalAnalyst()
result = analyst.analyze(stock_data)

print(f"估值水平: {result.valuation_level}")
print(f"盈利能力: {result.profitability}")
print(f"成长性: {result.growth}")
```

### 情绪分析

```python
from astock_agents.agents.sentiment_analyst import SentimentAnalyst

analyst = SentimentAnalyst()
result = analyst.analyze(stock_data)

print(f"情绪评分: {result.score}")
print(f"情绪状态: {result.state}")
```

### 多空辩论

```python
from astock_agents.agents.bull_researcher import BullResearcher
from astock_agents.agents.bear_researcher import BearResearcher

bull = BullResearcher()
bear = BearResearcher()

bull_args = bull.analyze(stock_data, technical_analysis=tech_result)
bear_args = bear.analyze(stock_data, technical_analysis=tech_result)

print(f"多头观点: {bull_args.arguments}")
print(f"空头观点: {bear_args.arguments}")
```

### 风险评估

```python
from astock_agents.agents.risk_manager import RiskManager

manager = RiskManager()
result = manager.analyze(stock_data, technical_analysis=tech_result)

print(f"整体风险: {result.overall_risk}")
print(f"市场风险: {result.market_risk}")
print(f"建议: {result.suggestions}")
```

## 完整工作流

```python
from astock_agents.workflow.analysis_workflow import AnalysisWorkflow
from astock_agents.data.data_manager import DataManager

# 初始化
workflow = AnalysisWorkflow()
data_manager = DataManager()

# 获取数据
stock_data = data_manager.get_stock_data("600519.SH")

# 运行完整分析
report = await workflow.run(stock_data)

# 查看结果
print(f"股票: {report.stock_name}")
print(f"技术信号: {report.technical_analysis.signal.value}")
print(f"综合评分: {report.final_decision.score}")
print(f"投资建议: {report.final_decision.recommendation}")
```

## Docker部署

### 构建镜像

```bash
docker build -t astock-agents .
```

### 运行容器

```bash
docker run -d -p 8000:8000 astock-agents
```

### Docker Compose

```bash
docker-compose up -d
```

## 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_data_layer.py -v

# 带覆盖率
pytest --cov=astock_agents
```

### 测试特定功能

```python
# 测试技术指标计算
pytest tests/test_agents_layer.py::TestIndicatorCalculations -v

# 测试形态识别
pytest tests/test_agents_layer.py::TestPatternRecognition -v
```

## API文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### API端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/analyze` | GET/POST | 股票分析 |
| `/api/stocks/popular` | GET | 热门股票列表 |
| `/api/compare` | GET | 多股对比 |

## 常见问题

### Q: 数据获取失败？

A: 检查网络连接，确保数据源可用。系统会自动降级到备用数据源。

### Q: 分析结果不准确？

A: 
1. 确保数据量足够（建议至少60天）
2. 调整置信度阈值
3. 结合多个分析结果综合判断

### Q: 如何添加自定义指标？

A: 继承 `TechnicalAnalyst` 并添加新方法：

```python
class CustomAnalyst(TechnicalAnalyst):
    def _calc_custom_indicator(self, df):
        # 自定义指标计算
        pass
```

## 最佳实践

1. **数据质量**: 使用多个数据源交叉验证
2. **风险控制**: 结合风险评估结果调整仓位
3. **综合判断**: 不要依赖单一指标或信号
4. **定期更新**: 定期更新数据和模型
5. **回测验证**: 策略上线前进行充分回测

## 免责声明

⚠️ **重要提示**

本系统提供的分析结果仅供参考，不构成任何投资建议。股市有风险，投资需谨慎。使用本系统进行投资决策造成的任何损失，开发者不承担任何责任。
