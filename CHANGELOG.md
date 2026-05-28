# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- 多智能体可视化界面设计文档
- 单股票长期追踪功能设计方案
- 功能规划方案（覆盖全链路）

### Changed
- 优化项目文档结构

### Deprecated
- (None)

### Removed
- (None)

### Fixed
- (None)

### Security
- (None)

---

## [1.0.0] - 2026-05-28

### Added
- **核心框架**
  - 基于 LangGraph 的多智能体协同分析框架
  - 8个专业分析智能体：技术分析师、基本面分析师、情绪分析师、新闻分析师、多头研究员、空头研究员、交易员、风险管理器

- **数据层**
  - 多数据源支持：Mootdx（通达信）、Tencent（腾讯财经）、Akshare
  - 数据缓存机制（5分钟TTL）
  - 自动降级策略

- **技术分析**
  - 10+技术指标：MA(5,10,20,60,120)、MACD、RSI、KDJ、Bollinger、ATR、OBV、Williams %R、CCI、ADX
  - 15+K线形态识别：吞没形态、孕线形态、早晨之星/黄昏之星、锤子线/流星线、双底/双顶、头肩顶/头肩底、三只白兵/三只乌鸦

- **多空辩论机制**
  - 多头研究员看涨论据生成
  - 空头研究员看跌论据生成
  - 综合决策建议

- **风险评估**
  - 三维度风险评估
  - 仓位建议
  - 止损策略

- **应用层**
  - CLI 命令行界面
  - FastAPI Web 服务
  - RESTful API
  - Vue 3 + TypeScript 前端界面
  - WebSocket 实时推送

- **部署**
  - Docker 支持
  - Docker Compose 支持

### Changed
- 初始版本发布

---

## [Version History]

- [1.0.0] - 初始版本发布

---

## Upgrade Guide

### Upgrading to 1.0.0
- 全新项目，无需升级指南

---

## Migration Guide

### Migrating from 0.x
- 这是第一个正式版本，无需迁移指南
