"""新闻分析师智能体"""

from typing import Dict, Any, List
from datetime import datetime
from loguru import logger

from astock_agents.agents.base_agent import BaseAgent
from astock_agents.models import StockData, NewsAnalysis, Signal


class NewsAnalyst(BaseAgent):
    """新闻分析师 - 负责新闻、公告、宏观事件分析"""
    
    def __init__(self, llm=None, config=None):
        super().__init__(
            name="新闻分析师",
            role="通过新闻公告、政策变化、宏观事件评估外部影响",
            llm=llm,
            config=config
        )
    
    def analyze(self, stock_data: StockData, **kwargs) -> NewsAnalysis:
        """执行新闻分析"""
        logger.info(f"[{self.name}] 开始新闻分析: {stock_data.stock_code}")
        
        # 获取新闻和公告
        key_news = self._get_key_news(stock_data)
        key_announcements = self._get_key_announcements(stock_data)
        
        # 宏观影响分析
        macro_impact = self._analyze_macro_impact(stock_data)
        
        # 行业动态
        industry_updates = self._analyze_industry_updates(stock_data)
        
        # 风险事件
        risk_events = self._identify_risk_events(key_news, key_announcements)
        
        # 生成信号
        signal, confidence = self._generate_signal(key_news, key_announcements, risk_events)
        
        # 生成摘要
        summary = self._generate_summary(
            stock_data, key_news, key_announcements, macro_impact, risk_events, signal
        )
        
        analysis = NewsAnalysis(
            key_news=key_news,
            key_announcements=key_announcements,
            macro_impact=macro_impact,
            industry_updates=industry_updates,
            risk_events=risk_events,
            summary=summary,
            signal=signal,
            confidence=confidence
        )
        
        self.log_analysis(analysis.dict())
        return analysis
    
    def _get_key_news(self, stock_data: StockData) -> List[Dict[str, Any]]:
        """获取关键新闻"""
        # 使用stock_data中已有的新闻数据
        news = stock_data.recent_news or []
        
        # 格式化新闻
        formatted_news = []
        for item in news[:10]:  # 限制数量
            formatted_news.append({
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "date": item.get("date", ""),
                "summary": item.get("summary", "")[:100] + "..." if len(item.get("summary", "")) > 100 else item.get("summary", ""),
            })
        
        return formatted_news
    
    def _get_key_announcements(self, stock_data: StockData) -> List[Dict[str, Any]]:
        """获取重要公告"""
        # 使用stock_data中已有的公告数据
        announcements = stock_data.recent_announcements or []
        
        # 格式化公告
        formatted = []
        for item in announcements[:10]:
            formatted.append({
                "title": item.get("title", ""),
                "type": item.get("type", ""),
                "date": item.get("date", ""),
            })
        
        return formatted
    
    def _analyze_macro_impact(self, stock_data: StockData) -> str:
        """分析宏观影响"""
        # 简化处理，实际应该接入宏观数据
        industry = stock_data.industry or "未知"
        
        # 基于行业的宏观分析模板
        macro_analysis_map = {
            "银行": "关注货币政策、利率变化对银行业的影响",
            "房地产": "关注房地产政策调控、利率环境变化",
            "医药": "关注医保政策、集采政策、创新药审批",
            "新能源": "关注双碳政策、补贴政策、技术迭代",
            "科技": "关注科技产业政策、中美科技关系",
        }
        
        return macro_analysis_map.get(industry, "关注宏观经济形势和政策变化")
    
    def _analyze_industry_updates(self, stock_data: StockData) -> str:
        """分析行业动态"""
        industry = stock_data.industry
        
        if not industry:
            return "行业信息待补充"
        
        return f"{industry}行业动态追踪中，建议关注行业龙头动向和政策变化"
    
    def _identify_risk_events(
        self,
        news: List[Dict],
        announcements: List[Dict]
    ) -> List[str]:
        """识别风险事件"""
        risk_events = []
        
        # 关键词风险识别
        risk_keywords = [
            "监管", "处罚", "立案调查", "业绩下滑", "亏损",
            "减持", "解禁", "质押", "违约", "诉讼"
        ]
        
        for item in news + announcements:
            title = item.get("title", "")
            for keyword in risk_keywords:
                if keyword in title:
                    risk_events.append(f"[{keyword}] {title[:30]}...")
                    break
        
        return list(set(risk_events))[:5]  # 去重并限制数量
    
    def _generate_signal(
        self,
        news: List[Dict],
        announcements: List[Dict],
        risk_events: List[str]
    ) -> tuple:
        """生成交易信号"""
        score = 50  # 中性
        
        # 风险事件扣分
        if risk_events:
            score -= min(30, len(risk_events) * 10)
        
        # 公告数量加分（活跃度）
        if len(announcements) > 5:
            score += 5
        
        if score >= 60:
            signal = Signal.BUY
        elif score <= 40:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD
        
        confidence = min(100, max(0, abs(score - 50) * 2))
        
        return signal, confidence
    
    def _generate_summary(
        self,
        stock_data: StockData,
        news: List[Dict],
        announcements: List[Dict],
        macro_impact: str,
        risk_events: List[str],
        signal: Signal
    ) -> str:
        """生成分析摘要"""
        lines = [
            f"{stock_data.stock_name}({stock_data.stock_code})新闻分析：",
            f"",
            f"【宏观影响】{macro_impact}",
            f"",
            f"【新闻动态】近期共{len(news)}条相关新闻",
            f"【公告情况】近期共{len(announcements)}条公告",
            f"",
        ]
        
        if risk_events:
            lines.append(f"【风险提示】发现{len(risk_events)}项风险事件：")
            for event in risk_events[:3]:
                lines.append(f"  • {event}")
            lines.append("")
        
        lines.append(f"【新闻信号】{signal.value}")
        
        return "\n".join(lines)