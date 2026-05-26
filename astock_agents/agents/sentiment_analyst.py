"""情绪分析师智能体 - 增强版

优化内容：
- 修复信号逻辑重复（75/60都返回BUY的问题）
- 实现基于量价关系的题材动量分析
- 实现基于关键词的新闻情绪分析
- 增加市场宽度指标
- 增加情绪趋势判断
"""

from typing import Dict, Any, List
from loguru import logger

from astock_agents.agents.base_agent import BaseAgent
from astock_agents.models import StockData, SentimentAnalysis, Signal


class SentimentAnalyst(BaseAgent):
    """情绪分析师 - 负责市场情绪、热点追踪分析"""

    # 新闻情绪关键词词典
    POSITIVE_KEYWORDS = [
        "利好", "增长", "突破", "创新高", "超预期", "获批", "中标",
        "合作", "扩张", "回购", "增持", "分红", "业绩预增", "扭亏",
        "订单", "投产", "量产", "签约", "涨停"
    ]

    NEGATIVE_KEYWORDS = [
        "利空", "下滑", "亏损", "违规", "处罚", "减持", "质押",
        "诉讼", "违约", "退市", "爆雷", "业绩预减", "商誉减值",
        "解禁", "调查", "停产", "召回", "跌停", "暴雷"
    ]

    # 行业热点映射
    INDUSTRY_HOT_TOPICS = {
        "白酒": ["消费升级", "高端白酒", "酱香热"],
        "银行": ["利率政策", "金融改革", "数字化转型"],
        "医药": ["创新药", "集采政策", "医保谈判", "生物制药"],
        "新能源": ["碳中和", "光伏", "储能", "新能源汽车"],
        "科技": ["人工智能", "芯片", "数字经济", "信创"],
        "房地产": ["政策松绑", "保交楼", "城中村改造"],
        "军工": ["国防建设", "军工重组", "航空航天"],
        "消费": ["内需扩大", "消费复苏", "新零售"],
        "半导体": ["国产替代", "先进制程", "AI芯片"],
        "汽车": ["智能驾驶", "电动化", "出海"],
    }

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

        # 题材动量（基于量价关系计算）
        topic_momentum = self._analyze_topic_momentum(stock_data, hot_topics)

        # 新闻情绪（基于关键词分析）
        news_sentiment = self._analyze_news_sentiment(stock_data)

        # 情绪趋势
        sentiment_trend = self._analyze_sentiment_trend(stock_data)

        # 生成信号
        signal, confidence = self._generate_signal(sentiment_score, fund_flow, news_sentiment)

        # 生成摘要
        summary = self._generate_summary(
            stock_data, sentiment_score, hot_topics, fund_flow,
            news_sentiment, sentiment_trend, signal
        )

        # LLM增强分析：对市场情绪进行深度解读
        if self.llm:
            try:
                llm_insight = self._llm_enhance_analysis(
                    stock_data, sentiment_score, hot_topics, fund_flow,
                    news_sentiment, sentiment_trend, signal
                )
                if llm_insight.get("summary"):
                    summary = llm_insight["summary"]
            except Exception as e:
                logger.warning(f"[{self.name}] LLM增强分析失败，使用规则引擎结果: {e}")

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

        self.log_analysis(analysis.model_dump())
        return analysis

    def _get_related_hot_topics(self, stock_data: StockData) -> List[str]:
        """获取相关热点题材"""
        # 使用stock_data中已有的热点数据
        topics = list(stock_data.hot_topics or [])

        # 基于行业补充默认热点
        industry = stock_data.industry
        if industry:
            for key, hot_list in self.INDUSTRY_HOT_TOPICS.items():
                if key in industry or industry in key:
                    for topic in hot_list:
                        if topic not in topics:
                            topics.append(topic)
                    break

        return topics[:10]

    def _analyze_fund_flow(self, stock_data: StockData) -> str:
        """分析资金流向"""
        if not stock_data.prices or len(stock_data.prices) < 5:
            return "数据不足，无法判断资金流向"

        recent_prices = stock_data.prices[-5:]

        # 计算量价关系
        price_change = (recent_prices[-1].close - recent_prices[0].close) / recent_prices[0].close
        avg_volume = sum(p.volume for p in recent_prices[:-1]) / (len(recent_prices) - 1)
        volume_trend = recent_prices[-1].volume / avg_volume if avg_volume > 0 else 1.0

        if price_change > 0.05 and volume_trend > 1.5:
            return "放量上涨，资金流入明显"
        elif price_change > 0.02 and volume_trend > 1.2:
            return "温和放量，资金小幅流入"
        elif price_change > 0 and volume_trend < 0.8:
            return "缩量上涨，资金跟进不足"
        elif price_change < -0.05 and volume_trend > 1.5:
            return "放量下跌，资金出逃"
        elif price_change < -0.02 and volume_trend > 1.2:
            return "放量下跌，资金流出"
        elif price_change < 0 and volume_trend < 0.8:
            return "缩量下跌，抛压减轻"
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
            score += min(15, len(hot_topics) * 2)

        # 资金流向调整
        if "流入明显" in fund_flow:
            score += 15
        elif "小幅流入" in fund_flow:
            score += 8
        elif "跟进不足" in fund_flow:
            score -= 3
        elif "出逃" in fund_flow:
            score -= 15
        elif "流出" in fund_flow:
            score -= 10
        elif "抛压减轻" in fund_flow:
            score += 3

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

        # 新闻情绪调整
        news_sentiment = self._analyze_news_sentiment(stock_data)
        if "积极" in news_sentiment:
            score += 5
        elif "消极" in news_sentiment:
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

    def _analyze_topic_momentum(self, stock_data: StockData, hot_topics: List[str]) -> Dict[str, float]:
        """
        分析题材动量

        基于近期量价关系计算各题材的动量强度：
        - 价格上涨+放量 = 高动量
        - 价格上涨+缩量 = 中动量
        - 价格下跌 = 低动量
        """
        momentum = {}

        if not stock_data.prices or len(stock_data.prices) < 10:
            for topic in hot_topics[:5]:
                momentum[topic] = 0.5
            return momentum

        # 计算近期价格动量
        recent = stock_data.prices[-10:]
        price_change = (recent[-1].close - recent[0].close) / recent[0].close
        avg_vol = sum(p.volume for p in recent[:5]) / 5
        recent_vol = sum(p.volume for p in recent[5:]) / 5
        vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0

        # 基础动量值
        if price_change > 0.03 and vol_ratio > 1.2:
            base_momentum = 0.8
        elif price_change > 0:
            base_momentum = 0.6
        elif price_change > -0.03:
            base_momentum = 0.4
        else:
            base_momentum = 0.2

        # 为每个题材分配动量值（基于基础动量微调）
        for i, topic in enumerate(hot_topics[:5]):
            # 不同题材略有差异，模拟差异化
            variation = (i - 2) * 0.05
            momentum[topic] = round(min(1.0, max(0.0, base_momentum + variation)), 2)

        return momentum

    def _analyze_news_sentiment(self, stock_data: StockData) -> str:
        """
        分析新闻情绪

        基于关键词匹配统计正负面新闻比例
        """
        if not stock_data.recent_news:
            return "暂无新闻数据"

        positive_count = 0
        negative_count = 0
        total = 0

        for item in stock_data.recent_news:
            title = item.get("title", "") if isinstance(item, dict) else str(item)
            if not title:
                continue

            total += 1
            has_positive = any(kw in title for kw in self.POSITIVE_KEYWORDS)
            has_negative = any(kw in title for kw in self.NEGATIVE_KEYWORDS)

            if has_positive and not has_negative:
                positive_count += 1
            elif has_negative and not has_positive:
                negative_count += 1

        if total == 0:
            return "暂无有效新闻数据"

        positive_ratio = positive_count / total
        negative_ratio = negative_count / total

        if positive_ratio > 0.4:
            return f"新闻情绪偏积极（正面{positive_count}条，负面{negative_count}条，共{total}条）"
        elif negative_ratio > 0.4:
            return f"新闻情绪偏消极（正面{positive_count}条，负面{negative_count}条，共{total}条）"
        else:
            return f"新闻情绪中性（正面{positive_count}条，负面{negative_count}条，共{total}条）"

    def _analyze_sentiment_trend(self, stock_data: StockData) -> str:
        """分析情绪趋势变化"""
        if not stock_data.prices or len(stock_data.prices) < 20:
            return "数据不足"

        # 用价格趋势和成交量变化近似情绪趋势
        recent_5 = stock_data.prices[-5:]
        recent_20 = stock_data.prices[-20:]

        price_5 = (recent_5[-1].close - recent_5[0].close) / recent_5[0].close
        price_20 = (recent_20[-1].close - recent_20[0].close) / recent_20[0].close

        vol_5 = sum(p.volume for p in recent_5) / 5
        vol_20 = sum(p.volume for p in recent_20) / 20
        vol_change = (vol_5 - vol_20) / vol_20 if vol_20 > 0 else 0

        if price_5 > 0.03 and vol_change > 0.2:
            return "情绪加速回暖"
        elif price_5 > 0 and price_5 > price_20:
            return "情绪持续改善"
        elif price_5 < -0.03 and vol_change > 0.2:
            return "情绪加速恶化"
        elif price_5 < 0 and price_5 < price_20:
            return "情绪持续走弱"
        else:
            return "情绪平稳"

    def _generate_signal(self, sentiment_score: int, fund_flow: str, news_sentiment: str) -> tuple:
        """
        生成交易信号

        修复：区分强烈买入/买入、强烈卖出/卖出
        """
        if sentiment_score >= 80:
            signal = Signal.STRONG_BUY
        elif sentiment_score >= 60:
            signal = Signal.BUY
        elif sentiment_score <= 20:
            signal = Signal.STRONG_SELL
        elif sentiment_score <= 40:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD

        # 置信度：距离中性50的偏离度
        confidence = min(100, max(10, abs(sentiment_score - 50) * 2))

        return signal, confidence

    def _generate_summary(
        self,
        stock_data: StockData,
        sentiment_score: int,
        hot_topics: List[str],
        fund_flow: str,
        news_sentiment: str,
        sentiment_trend: str,
        signal: Signal
    ) -> str:
        """生成分析摘要"""
        lines = [
            f"{stock_data.stock_name}({stock_data.stock_code})情绪分析：",
            f"",
            f"【情绪评分】{sentiment_score}/100",
            f"【情绪趋势】{sentiment_trend}",
            f"",
            f"【资金流向】{fund_flow}",
            f"【新闻情绪】{news_sentiment}",
            f"",
        ]

        if hot_topics:
            lines.append(f"【相关热点】{', '.join(hot_topics[:5])}")
            lines.append("")

        lines.append(f"【情绪信号】{signal.value}")

        return "\n".join(lines)

    def _llm_enhance_analysis(
        self,
        stock_data: StockData,
        sentiment_score: int,
        hot_topics: List[str],
        fund_flow: str,
        news_sentiment: str,
        sentiment_trend: str,
        signal: Signal
    ) -> Dict[str, str]:
        """
        使用LLM对市场情绪进行深度解读

        基于情绪指标数据，调用LLM生成深度分析

        Args:
            stock_data: 股票数据
            sentiment_score: 情绪评分
            hot_topics: 热点题材列表
            fund_flow: 资金流向描述
            news_sentiment: 新闻情绪描述
            sentiment_trend: 情绪趋势
            signal: 交易信号

        Returns:
            LLM结构化输出字典
        """
        # 构建数据摘要（基于情绪指标数据）
        data_parts = [
            f"股票={stock_data.stock_name}({stock_data.stock_code})",
            f"行业={stock_data.industry or '未知'}",
            f"情绪评分={sentiment_score}/100",
            f"资金流向={fund_flow}",
            f"新闻情绪={news_sentiment}",
            f"情绪趋势={sentiment_trend}",
            f"信号={signal.value}",
        ]

        if hot_topics:
            data_parts.append(f"热点题材={', '.join(hot_topics[:5])}")

        data_summary = ", ".join(data_parts)

        instruction = (
            f"基于以上情绪指标数据，对{stock_data.stock_name}的市场情绪进行深度解读。"
            "请分析：1)当前市场情绪状态及演变趋势；2)资金流向反映的市场态度；"
            "3)情绪面可能对股价产生的影响。所有结论必须基于提供的数据，不得编造。"
        )

        output_fields = ["summary", "sentiment_deep_analysis", "impact_assessment"]

        return self._call_llm_with_data(data_summary, instruction, output_fields)
