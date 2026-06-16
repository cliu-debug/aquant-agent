<div align="center">

# 🧠 AQuant-Agent

**A股量化智能体 - 10个AI分析师协同决策**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-CC%20BY--NC%204.0-blue)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/cliu-debug/aquant-agent?style=social)](https://github.com/cliu-debug/aquant-agent)
[![GitHub Release](https://img.shields.io/github/v/release/cliu-debug/aquant-agent)](https://github.com/cliu-debug/aquant-agent/releases)

**一句话说清楚**：用 LangGraph 编排 10 个专业 AI 智能体，模拟顶级投研团队的分析流程，为 A 股投资者提供全方位、多维度的智能决策支持。

[🚀 5分钟快速体验](#-5分钟快速体验) · [✨ 核心亮点](#-核心亮点) · [📊 效果展示](#-效果展示) · [🏗️ 架构设计](#️-架构设计)

</div>

---

## 🎯 为什么选择 AQuant-Agent？

| 传统量化工具 | AQuant-Agent |
|-------------|--------------|
| 单一指标分析 | **10个智能体协同**：技术+基本面+情绪+新闻+资金流+多空辩论 |
| 静态规则 | **LLM增强决策**：本地模型/免费API，零成本运行 |
| 无记忆 | **年轮记忆系统**：学习你的投资偏好，持续进化 |
| 无风控 | **三层风控**：合规审查+FOMO检测+仓位管理 |
| 通用市场 | **A股垂直优化**：6级数据源降级，A股全覆盖 |

---

## 📊 效果展示

### 🤖 3D智能体可视化
![3D智能体可视化](screenshots/3D可视化.gif)

### 📈 多维度分析看板
![可视化分析](screenshots/可视化分析.gif)

---

## 🚀 5分钟快速体验

```bash
# 1️⃣ 克隆项目
git clone https://github.com/cliu-debug/aquant-agent.git
cd aquant-agent

# 2️⃣ 安装依赖
pip install -r requirements.txt

# 3️⃣ 配置LLM（三选一）
# 方式A：本地模型（推荐，完全免费）
# 下载 llama.cpp 运行 gemma4 模型，默认 http://127.0.0.1:8080

# 方式B：OpenRouter免费API
export LLM_PROVIDER=openrouter
export OPENROUTER_API_KEY=your_key

# 方式C：国产LLM（通义千问/DeepSeek/智谱）
export LLM_PROVIDER=qwen
export QWEN_API_KEY=your_key

# 4️⃣ 运行Demo
python examples/demo.py --code 600519.SH --name 贵州茅台

# 5️⃣ 启动Web界面
python -m astock_agents.web.app
# 访问 http://localhost:8000
```

---

## ✨ 核心亮点

### 🤝 10个专业智能体协同

```
┌─────────────────────────────────────────────────────────────┐
│                    AQuant-Agent 智能体团队                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📊 技术分析师    📈 基本面分析师    😊 情绪分析师            │
│  📰 新闻分析师    💰 资金流向分析师  🌍 宏观分析师            │
│                                                              │
│           🐂 多头研究员 ←──博弈论辩论──→ 🐻 空头研究员        │
│                                                              │
│                    🎯 交易员 ←──→ 🛡️ 风险管理               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 🧠 三层混合决策架构

| 层级 | 职责 | 示例 |
|------|------|------|
| **规则引擎层** | 快速过滤、硬性约束 | 涨跌停过滤、ST股排除 |
| **LLM增强层** | 语义理解、推理决策 | 新闻情绪解读、形态识别 |
| **风控强制层** | 安全边界、合规审查 | 仓位限制、FOMO检测 |

### 🔄 年轮记忆系统

```python
# 系统会记住你的投资偏好
user_memory.learn(
    user_id="user_001",
    action="买入",
    stock="贵州茅台",
    reason="看好白酒板块",
    outcome="盈利15%"
)

# 下次分析时自动参考
recommendation = user_memory.recall("白酒板块")
# → "您上次看好白酒板块盈利15%，建议关注..."
```

### 🎭 博弈论多空辩论

```python
# 模拟真实投研会议
debate = DebateEngine(
    bull_researcher=BullResearcher(),  # 多头观点
    bear_researcher=BearResearcher(),  # 空头观点
    rounds=3  # 三轮对抗
)

result = debate.run(stock_data)
# → 纳什均衡决策，避免单一视角偏见
```

---

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                      AQuant-Agent                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │    数据层     │   │   智能体层    │   │    应用层     │   │
│  │              │   │              │   │              │   │
│  │ • Mootdx     │   │ • Technical  │   │ • CLI        │   │
│  │ • Akshare    │   │ • Fundamental│   │ • Web UI     │   │
│  │ • Tencent    │   │ • Sentiment  │   │ • REST API   │   │
│  │ • Eastmoney  │   │ • News       │   │ • WebSocket  │   │
│  │ • Baidu      │   │ • Bull/Bear  │   │              │   │
│  │ • Cninfo     │   │ • CapitalFlow│   │              │   │
│  │              │   │ • Risk       │   │              │   │
│  └──────────────┘   └──────────────┘   └──────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           工作流编排 (LangGraph StateGraph)           │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐ │   │
│  │  │数据获取 │→│分析师 │→│辩论 │→│交易 │ │   │
│  │  │  Node  │  │  Node   │  │  Node   │  │ Node   │ │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    服务层                             │   │
│  │  • 合规审查 • FOMO检测 • 回测引擎 • 风控管理          │   │
│  │  • 仓位计算 • 通知推送 • 定时调度 • 审计追踪          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

详细架构请参考 [架构文档](docs/ARCHITECTURE.md)

---

## 🔌 多LLM支持

| 提供商 | 免费额度 | 推荐模型 |
|--------|----------|----------|
| **本地模型** ✨ | 完全免费 | gemma4, llama3, Qwen |
| **OpenRouter** | 每日免费 | google/gemma-4-31b-it:free |
| **通义千问** | 有免费额度 | qwen-turbo |
| **DeepSeek** | 有免费额度 | deepseek-chat |
| **智谱AI** | 有免费额度 | glm-4 |
| **OpenAI** | 付费 | GPT-4o |
| **Anthropic** | 付费 | Claude-3.5 |

---

## 📚 使用指南

### Python API

```python
from astock_agents.workflow.analysis_workflow import AnalysisWorkflow

# 创建工作流
workflow = AnalysisWorkflow()

# 执行分析
result = workflow.run(stock_code="600519.SH", stock_name="贵州茅台")

print(f"最终信号: {result.final_signal}")        # BUY/SELL/HOLD
print(f"置信度: {result.final_confidence}%")   # 0-100
print(f"技术分析: {result.technical_analysis.summary}")
print(f"多空辩论: {result.debate.bull_thesis}")
```

### REST API

```bash
# 分析股票
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{"stock_code": "600519.SH", "stock_name": "贵州茅台"}'

# 获取热门股票
curl "http://localhost:8000/api/stocks/popular"

# 策略回测
curl -X POST "http://localhost:8000/api/backtest" \
  -H "Content-Type: application/json" \
  -d '{"strategy": "MACD", "stock_code": "000001.SZ"}'
```

详细使用请参考 [使用指南](docs/USER_GUIDE.md)

---

## 🧪 测试

```bash
# 运行所有测试
pytest

# 带覆盖率报告
pytest --cov=astock_agents --cov-report=html
```

---

## 📁 项目结构

```
aquant-agent/
├── astock_agents/           # 主包
│   ├── agents/              # 10个智能体
│   ├── data/                # 6级数据源
│   ├── services/            # 22个服务
│   ├── workflow/            # LangGraph工作流
│   ├── models/              # Pydantic数据模型
│   └── web/                 # FastAPI Web服务
├── frontend/                # Vue3前端
├── tests/                   # 单元测试
├── docs/                    # 技术文档
└── examples/                # 示例代码
```

---

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

详细指南请参考 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 许可证

本项目采用 **CC BY-NC 4.0** (Creative Commons Attribution-NonCommercial 4.0) 许可证。

**允许**：
- 个人学习、研究使用
- 修改和再分发

**禁止**：
- 商业用途
- SaaS产品
- 盈利性服务

详细信息请参考 [LICENSE](LICENSE) 文件

---

## ⚠️ 免责声明

**本系统提供的分析结果仅供参考，不构成任何投资建议。**

股市有风险，投资需谨慎。使用本系统进行投资决策造成的任何损失，开发者不承担任何责任。请结合自身风险承受能力，独立做出投资决策。

---

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - LLM应用框架
- [LangGraph](https://github.com/langchain-ai/langgraph) - 工作流编排
- [Akshare](https://github.com/akfamily/akshare) - 金融数据接口
- [Mootdx](https://github.com/moomindesigns/mootdx) - 通达信接口

---

<div align="center">

**如果这个项目对你有帮助，请给一个 ⭐️ Star 支持一下！**

Made with ❤️ by AQuant-Agent Team

</div>