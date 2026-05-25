"""情绪分析师智能体"""

from typing import Dict, Any, List
from loguru import logger

from astock_agents.agents.base_agent import BaseAgent
from astock_agents.models import StockData, SentimentAnalysis, Signal


class SentimentAnalyst(BaseAgent):
    """情绪分析师 - 负责市场情绪、热点追踪分析"""
    
    def __init__(self, llm=None, config=None):
        super().__init__(
            name="情绪分析师",
            role="通过热点题材、资金流向、市场情绪判断市场热度",
            llm=llm,
            config=config
        )
    
    def analyze(self, stock_data: StockData, **kwargs) -> SentimentAnalysis:
        """执行情绪分析"""
        logger.info(f"[{self.name}] 开始情绪分析: {stock_data.stock_code}")
        
        # 获取热点相关数据
        hot_topics = self._get_related_hot_topics(stock_data)
        
        # 分析资金流向
        fund_flow = self._analyze_fund_flow(stock_data)
        
        # 计算情绪评分
        sentiment_score = self._calculate_sentiment_score(stock_data, hot_topics, fund_flow)
        
        # 市场情绪描述
        market_sentiment = self._describe_sentiment(sentiment_score)
        
        # 题材动量
        topic_momentum = self._analyze_topic_momentum(hot_topics)
        
        # 新闻情绪
        news_sentiment = self._analyze_news_sentiment(stock_data)
        
        # 生成信号
        signal, confidence = self._generate_signal(sentiment_score, fund_flow)
        
        # 生成摘要
        summary = self._generate_summary(
            stock_data, sentiment_score, hot_topics, fund_flow, signal
        )
        
        analysis = SentimentAnalysis(
            overall_score=sentiment_score,
            market_sentiment=market_sentiment,
            related_hot_topics=hot_topics,
            topic_momentum=topic_momentum,
            fund_flow=fund_flow,
            news_sentiment=news_sentiment,
            summary=summary,
            signal=signal,
            confidence=confidence
        )
        
        self.log_analysis(analysis.dict())
        return analysis
    
    def _get_related_hot_topics(self, stock_data: StockData) -> List[str]:
        """获取相关热点题材"""
        # 使用stock_data中已有的热点数据
        topics = stock_data.hot_topics or []
        
        # 基于行业添加默认热点
        industry = stock_data.industry
        if industry:
            # 这里可以接入同花顺热点数据
            pass
        
        return topics[:10]  # 限制数量
    
    def _analyze_fund_flow(self, stock_data: StockData) -> str:
        """分析资金流向"""
        # 基于价格数据简单分析
        if not stock_data.prices or len(stock_data.prices) < 5:
            return "数据不足，无法判断资金流向"
        
        recent_prices = stock_data.prices[-5:]
        
        # 计算量价关系
        price_change = (recent_prices[-1].close - recent_prices[0].close) / recent_prices[0].close
        volume_trend = recent_prices[-1].volume / (sum([p.volume for p in recent_prices[:-1]]) / 4)
        
        if price_change > 0.05 and volume_trend > 1.5:
            return "放量上涨，资金流入明显"
        elif price_change > 0.02 and volume_trend > 1.2:
            return "温和放量，资金小幅流入"
        elif price_change < -0.05 and volume_trend > 1.5:
            return "放量下跌，资金出逃"
        elif price_change < -0.02 and volume_trend > 1.2:
            return "缩量下跌，资金观望"
        else:
            return "量价平稳，资金流动不明显"
    
    def _calculate_sentiment_score(
        self,
        stock_data: StockData,
        hot_topics: List[str],
        fund_flow: str
    ) -> int:
        """计算情绪评分 0-100"""
        score = 50  # 中性基准
        
        # 热点加分
        if hot_topics:
            score += min(20, len(hot_topics) * 3)
        
        # 资金流向调整
        if "流入明显" in fund_flow:
            score += 15
        elif "小幅流入" in fund_flow:
            score += 8
        elif "出逃" in fund_flow:
            score -= 15
        elif "观望" in fund_flow:
            score -= 5
        
        # 价格趋势调整
        if stock_data.prices and len(stock_data.prices) >= 5:
            recent = stock_data.prices[-5:]
            price_change = (recent[-1].close - recent[0].close) / recent[0].close
            if price_change > 0.1:
                score += 10
            elif price_change > 0.05:
                score += 5
            elif price_change < -0.1:
                score -= 10
            elif price_change < -0.05:
                score -= 5
        
        return min(100, max(0, score))
    
    def _describe_sentiment(self, score: int) -> str:
        """描述市场情绪"""
        if score >= 80:
            return "极度乐观，市场热情高涨"
        elif score >= 65:
            return "偏乐观，市场情绪积极"
        elif score >= 50:
            return "中性偏乐观，情绪温和"
        elif score >= 35:
            return "中性偏谨慎，情绪偏冷"
        elif score >= 20:
            return "偏悲观，市场情绪低迷"
        else:
            return "极度悲观，市场恐慌"
    
    def _analyze_topic_momentum(self, hot_topics: List[str]) -> Dict[str, float]:
        """分析题材动量"""
        # 简化处理，实际应该追踪热点强度变化
        momentum = {}
        for topic in hot_topics[:5]:
            # 模拟动量值
            momentum[topic] = 0.5
        return momentum
    
    def _analyze_news_sentiment(self, stock_data: StockData) -> str:
        """分析新闻情绪"""
        # 基于recent_news简单分析
        if not stock_data.recent_news:
            return "暂无新闻数据"
        
        # 简化处理，实际应该用NLP分析
        return "新闻情绪待NLP分析"
    
    def _generate_signal(self, sentiment_score: int, fund_flow: str) -> tuple:
        """生成交易信号"""
        if sentiment_score >= 75:
            signal = Signal.BUY
        elif sentiment_score >= 60:
            signal = Signal.BUY
        elif sentiment_score <= 25:
            signal = Signal.SELL
        elif sentiment_score <= 40:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD
        
        confidence = min(100, max(0, abs(sentiment_score - 50) * 2))
        
        return signal, confidence
    
    def _generate_summary(
        self,
        stock_data: StockData,
        sentiment_score: int,
        hot_topics: List[str],
        fund_flow: str,
        signal: Signal
    ) -> str:
        """生成分析摘要"""
        lines = [
            f"{stock_data.stock_name}({stock_data.stock_code})情绪分析：",
            f"",
            f"【情绪评分】{sentiment_score}/100",
            f"",
            f"【资金流向】{fund_flow}",
            f"",
        ]
        
        if hot_topics:
            lines.append(f"【相关热点】{', '.join(hot_topics[:5])}")
            lines.append("")
        
        lines.append(f"【情绪信号】{signal.value}")
        
        return "\n".join(lines)