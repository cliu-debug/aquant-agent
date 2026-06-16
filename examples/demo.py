#!/usr/bin/env python
"""
AQuant-Agent 完整演示脚本

演示多智能体协同分析系统的完整工作流程：
1. 数据获取 - 从多个数据源获取股票数据
2. 技术分析 - 技术指标计算和形态识别
3. 基本面分析 - 财务数据分析
4. 情绪分析 - 市场情绪评估
5. 多空辩论 - 多空观点对抗
6. 风险评估 - 综合风险分析
7. 最终决策 - 生成投资建议
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")


def print_banner():
    """打印横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     █████╗ ███╗   ██╗████████╗ ██████╗ █████╗               ║
║    ██╔══██╗████╗  ██║╚══██╔══╝██╔════╝██╔══██╗              ║
║    ███████║██╔██╗ ██║   ██║   ██║     ███████║              ║
║    ██╔══██║██║╚██╗██║   ██║   ██║     ██╔══██║              ║
║    ██║  ██║██║ ╚████║   ██║   ╚██████╗██║  ██║              ║
║    ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝╚═╝  ╚═╝              ║
║                                                              ║
║     多智能体协同股票分析系统 v1.0                            ║
║     Multi-Agent Stock Analysis System                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def create_mock_stock_data(stock_code: str, stock_name: str, days: int = 120):
    """创建模拟股票数据（用于演示）"""
    import numpy as np
    
    from astock_agents.models.stock_data import StockData, StockPrice, FinancialReport
    
    # 设置随机种子以获得可重复的结果
    np.random.seed(hash(stock_code) % 2**32)
    
    stock = StockData(
        stock_code=stock_code,
        stock_name=stock_name,
        industry="白酒" if "茅台" in stock_name or "五粮液" in stock_name else "银行" if "银行" in stock_name else "科技",
        pe_ttm=35.0 if "茅台" in stock_name else 8.0 if "银行" in stock_name else 25.0,
        pb=10.0 if "茅台" in stock_name else 0.6 if "银行" in stock_name else 3.0,
        market_cap=2.2e12 if "茅台" in stock_name else 3e11 if "银行" in stock_name else 5e11
    )
    
    # 根据股票类型设置基础价格
    if "茅台" in stock_name:
        base_price = 1800.0
        volatility = 30.0
    elif "五粮液" in stock_name:
        base_price = 150.0
        volatility = 5.0
    elif "银行" in stock_name:
        base_price = 10.0
        volatility = 0.5
    else:
        base_price = 50.0
        volatility = 3.0
    
    # 生成价格数据
    trend_factor = np.random.choice([-1, 1]) * np.random.uniform(0.1, 0.5)
    
    for i in range(days):
        # 趋势 + 波动 + 随机噪声
        trend = i * trend_factor
        cycle = np.sin(i * 0.1) * volatility
        noise = np.random.normal(0, volatility * 0.3)
        
        close = base_price + trend + cycle + noise
        high = close + abs(np.random.normal(0, volatility * 0.2))
        low = close - abs(np.random.normal(0, volatility * 0.2))
        open_price = close + np.random.normal(0, volatility * 0.1)
        volume = int(1000000 + np.random.exponential(500000))
        
        price = StockPrice(
            date=datetime(2024, 1, 1) + timedelta(days=i),
            open=round(open_price, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=round(close, 2),
            volume=volume
        )
        stock.prices.append(price)
    
    # 添加财务数据
    stock.financial_reports.append(FinancialReport(
        report_date=datetime(2024, 3, 31),
        report_type="一季报",
        revenue=40e9 if "茅台" in stock_name else 30e9,
        net_profit=24e9 if "茅台" in stock_name else 10e9,
        roe=0.12,
        gross_margin=0.92 if "茅台" in stock_name else 0.45
    ))
    
    return stock


def run_technical_analysis(stock_data):
    """运行技术分析"""
    logger.info(f"📊 技术分析师开始分析 {stock_data.stock_name}...")
    
    from astock_agents.agents.technical_analyst import TechnicalAnalyst
    
    analyst = TechnicalAnalyst()
    result = analyst.analyze(stock_data)
    
    print("\n" + "=" * 60)
    print("📈 技术分析结果")
    print("=" * 60)
    print(f"趋势判断: {result.trend} (强度: {result.trend_strength})")
    print(f"交易信号: {result.signal.value}")
    print(f"置信度: {result.confidence}%")
    
    # 技术指标摘要
    indicators = result.indicators
    if indicators:
        print("\n【技术指标】")
        if 'rsi' in indicators:
            rsi = indicators['rsi']
            print(f"  RSI: {rsi.get('value', 'N/A')} ({rsi.get('zone', '')})")
        if 'macd' in indicators:
            macd = indicators['macd']
            print(f"  MACD: DIF={macd.get('dif', 'N/A')}, DEA={macd.get('dea', 'N/A')}, {macd.get('cross_signal', '')}")
        if 'kdj' in indicators:
            kdj = indicators['kdj']
            print(f"  KDJ: K={kdj.get('k', 'N/A')}, D={kdj.get('d', 'N/A')}, J={kdj.get('j', 'N/A')}")
        if 'atr' in indicators:
            atr = indicators['atr']
            print(f"  ATR: {atr.get('pct', 'N/A')}% ({atr.get('volatility', '')})")
    
    # 形态识别
    if result.patterns:
        print(f"\n【形态识别】{', '.join(result.patterns[:5])}")
    
    # 支撑阻力
    if result.support_levels:
        print(f"\n【支撑位】{result.support_levels}")
    if result.resistance_levels:
        print(f"【阻力位】{result.resistance_levels}")
    
    return result


def run_fundamental_analysis(stock_data):
    """运行基本面分析"""
    logger.info(f"📋 基本面分析师开始分析 {stock_data.stock_name}...")
    
    from astock_agents.agents.fundamental_analyst import FundamentalAnalyst
    
    analyst = FundamentalAnalyst()
    result = analyst.analyze(stock_data)
    
    print("\n" + "=" * 60)
    print("📊 基本面分析结果")
    print("=" * 60)
    print(f"估值评估: {result.valuation_level if hasattr(result, 'valuation_level') else '中性'}")
    print(f"盈利能力: {result.profitability if hasattr(result, 'profitability') else '良好'}")
    print(f"成长性: {result.growth if hasattr(result, 'growth') else '稳定'}")
    
    return result


def run_sentiment_analysis(stock_data):
    """运行情绪分析"""
    logger.info(f"😊 情绪分析师开始分析 {stock_data.stock_name}...")
    
    from astock_agents.agents.sentiment_analyst import SentimentAnalyst
    
    analyst = SentimentAnalyst()
    result = analyst.analyze(stock_data)
    
    print("\n" + "=" * 60)
    print("🎭 市场情绪分析")
    print("=" * 60)
    print(f"情绪评分: {result.score if hasattr(result, 'score') else 50}/100")
    print(f"情绪状态: {result.state if hasattr(result, 'state') else '中性'}")
    
    return result


def run_bull_bear_debate(stock_data, tech_analysis, fund_analysis=None, sentiment_analysis=None):
    """运行多空辩论"""
    logger.info(f"⚖️ 多空辩论开始...")
    
    from astock_agents.agents.bull_researcher import BullResearcher
    from astock_agents.agents.bear_researcher import BearResearcher
    from astock_agents.models.analysis_report import NewsAnalysis, Signal
    
    bull = BullResearcher()
    bear = BearResearcher()
    
    # 创建默认的分析结果（如果未提供）
    if fund_analysis is None:
        from astock_agents.models.analysis_report import FundamentalAnalysis
        fund_analysis = FundamentalAnalysis(
            signal=Signal.HOLD,
            confidence=50,
            valuation_score=50,
            profitability_score=50,
            growth_score=50,
            financial_health_score=50,
            key_metrics={}
        )
    
    if sentiment_analysis is None:
        from astock_agents.models.analysis_report import SentimentAnalysis
        sentiment_analysis = SentimentAnalysis(
            signal=Signal.HOLD,
            confidence=50,
            overall_score=50,
            fund_flow="中性",
            related_hot_topics=[]
        )
    
    # 创建默认的新闻分析
    news_analysis = NewsAnalysis(
        signal=Signal.HOLD,
        confidence=50,
        key_news=[],
        key_announcements=[],
        risk_events=[],
        macro_impact="中性",
        industry_updates="无重大变化",
        summary="暂无重大新闻事件"
    )
    
    # 调用多空研究员
    bull_args = bull.analyze(
        stock_data, 
        technical=tech_analysis,
        fundamental=fund_analysis,
        sentiment=sentiment_analysis,
        news=news_analysis
    )
    bear_args = bear.analyze(
        stock_data,
        technical=tech_analysis,
        fundamental=fund_analysis,
        sentiment=sentiment_analysis,
        news=news_analysis
    )
    
    print("\n" + "=" * 60)
    print("🐂 多空辩论")
    print("=" * 60)
    
    print("\n【多头观点】")
    if hasattr(bull_args, 'arguments'):
        for arg in bull_args.arguments[:3]:
            print(f"  ✅ {arg}")
    else:
        print("  ✅ 技术指标显示上涨信号")
        print("  ✅ 均线呈多头排列")
        print("  ✅ 成交量配合良好")
    
    print("\n【空头观点】")
    if hasattr(bear_args, 'arguments'):
        for arg in bear_args.arguments[:3]:
            print(f"  ❌ {arg}")
    else:
        print("  ❌ 短期存在回调风险")
        print("  ❌ 估值处于高位")
        print("  ❌ 市场情绪谨慎")
    
    # 计算辩论结果
    bull_score = bull_args.score if hasattr(bull_args, 'score') else 50
    bear_score = bear_args.score if hasattr(bear_args, 'score') else 50
    
    print(f"\n【辩论结果】多头得分: {bull_score}, 空头得分: {bear_score}")
    
    return bull_args, bear_args


def run_risk_assessment(stock_data, tech_analysis):
    """运行风险评估"""
    logger.info(f"⚠️ 风险管理器开始评估...")
    
    from astock_agents.agents.risk_manager import RiskManager
    from astock_agents.models.analysis_report import TradeProposal, Signal
    
    manager = RiskManager()
    
    # 创建默认的交易提案
    trade_proposal = TradeProposal(
        direction=tech_analysis.signal,
        position_size_pct=10.0,  # 默认10%仓位
        time_horizon="中期",
        proposal_text="基于技术分析的交易建议"
    )
    
    result = manager.analyze(
        stock_data, 
        technical_analysis=tech_analysis,
        trade_proposal=trade_proposal
    )
    
    print("\n" + "=" * 60)
    print("⚠️ 风险评估")
    print("=" * 60)
    
    if hasattr(result, 'overall_risk'):
        print(f"整体风险: {result.overall_risk.value if hasattr(result.overall_risk, 'value') else result.overall_risk}")
    if hasattr(result, 'market_risk'):
        print(f"市场风险: {result.market_risk}")
    if hasattr(result, 'liquidity_risk'):
        print(f"流动性风险: {result.liquidity_risk}")
    if hasattr(result, 'concentration_risk'):
        print(f"集中度风险: {result.concentration_risk}")
    
    return result


def generate_final_decision(stock_data, tech_analysis, fund_analysis, sentiment_analysis, risk_assessment):
    """生成最终决策"""
    from astock_agents.models.analysis_report import Signal
    
    print("\n" + "=" * 60)
    print("🎯 最终投资建议")
    print("=" * 60)
    
    # 综合评分
    score = 50
    
    # 技术分析权重 40%
    tech_signal = tech_analysis.signal
    if tech_signal == Signal.STRONG_BUY:
        score += 20
    elif tech_signal == Signal.BUY:
        score += 10
    elif tech_signal == Signal.SELL:
        score -= 10
    elif tech_signal == Signal.STRONG_SELL:
        score -= 20
    
    # 置信度调整
    score = score * (tech_analysis.confidence / 100) + 50 * (1 - tech_analysis.confidence / 100)
    
    # 风险调整
    if risk_assessment:
        if hasattr(risk_assessment, 'overall_risk'):
            risk_value = risk_assessment.overall_risk.value if hasattr(risk_assessment.overall_risk, 'value') else str(risk_assessment.overall_risk)
            if "高" in risk_value:
                score -= 10
            elif "低" in risk_value:
                score += 5
    
    # 生成建议
    if score >= 70:
        recommendation = "强烈推荐买入"
        action = "BUY"
    elif score >= 55:
        recommendation = "建议买入"
        action = "BUY"
    elif score >= 45:
        recommendation = "建议持有观望"
        action = "HOLD"
    elif score >= 30:
        recommendation = "建议减仓"
        action = "SELL"
    else:
        recommendation = "强烈建议卖出"
        action = "SELL"
    
    print(f"\n股票: {stock_data.stock_name} ({stock_data.stock_code})")
    print(f"当前价格: {stock_data.current_price:.2f}" if stock_data.current_price else "当前价格: N/A")
    print(f"综合评分: {score:.1f}/100")
    print(f"投资建议: {recommendation}")
    print(f"操作建议: {action}")
    
    # 风险提示
    print("\n【风险提示】")
    print("  ⚠️ 本分析结果仅供参考，不构成投资建议")
    print("  ⚠️ 投资有风险，入市需谨慎")
    print("  ⚠️ 请结合自身风险承受能力做出决策")
    
    return {
        "stock_code": stock_data.stock_code,
        "stock_name": stock_data.stock_name,
        "score": score,
        "recommendation": recommendation,
        "action": action,
        "technical_signal": tech_signal.value,
        "confidence": tech_analysis.confidence
    }


def run_demo(stock_code: str = "600519.SH", stock_name: str = "贵州茅台"):
    """运行完整演示"""
    print_banner()
    
    print(f"\n🔍 开始分析股票: {stock_name} ({stock_code})")
    print(f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: 获取/创建股票数据
    logger.info("📡 正在获取股票数据...")
    stock_data = create_mock_stock_data(stock_code, stock_name, days=120)
    logger.success(f"✅ 成功获取 {len(stock_data.prices)} 天的价格数据")
    
    # Step 2: 技术分析
    tech_analysis = run_technical_analysis(stock_data)
    
    # Step 3: 基本面分析
    fund_analysis = run_fundamental_analysis(stock_data)
    
    # Step 4: 情绪分析
    sentiment_analysis = run_sentiment_analysis(stock_data)
    
    # Step 5: 多空辩论
    bull_args, bear_args = run_bull_bear_debate(stock_data, tech_analysis, fund_analysis, sentiment_analysis)
    
    # Step 6: 风险评估
    risk_assessment = run_risk_assessment(stock_data, tech_analysis)
    
    # Step 7: 最终决策
    decision = generate_final_decision(
        stock_data, tech_analysis, fund_analysis, 
        sentiment_analysis, risk_assessment
    )
    
    print("\n" + "=" * 60)
    print("✅ 分析完成!")
    print("=" * 60)
    
    return decision


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AQuant-Agent 股票分析演示")
    parser.add_argument("--code", "-c", default="600519.SH", help="股票代码")
    parser.add_argument("--name", "-n", default="贵州茅台", help="股票名称")
    parser.add_argument("--batch", "-b", action="store_true", help="批量分析模式")
    
    args = parser.parse_args()
    
    if args.batch:
        # 批量分析
        stocks = [
            ("600519.SH", "贵州茅台"),
            ("000858.SZ", "五粮液"),
            ("000001.SZ", "平安银行"),
        ]
        
        results = []
        for code, name in stocks:
            print("\n" + "=" * 80)
            result = run_demo(code, name)
            results.append(result)
        
        print("\n" + "=" * 80)
        print("📊 批量分析结果汇总")
        print("=" * 80)
        for r in results:
            print(f"{r['stock_name']}: {r['recommendation']} (评分: {r['score']:.1f})")
    else:
        # 单股分析
        run_demo(args.code, args.name)


if __name__ == "__main__":
    main()
