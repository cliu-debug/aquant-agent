"""新闻分析师智能体"""

from typing import Dict, Any, List
from datetime import datetime
from loguru import logger

from astock_agents.agents.base_agent import BaseAgent
from astock_agents.models import StockData, NewsAnalysis, Signal


class NewsAnalyst(BaseAgent):
    """新闻分析师 - 负责新闻、公告、宏观事件分析"""

    # 负面风险关键词及其严重等级（高/中/低）
    RISK_KEYWORDS: Dict[str, str] = {
        # 高风险
        "立案调查": "高",
        "处罚": "高",
        "违约": "高",
        "退市": "高",
        "重大诉讼": "高",
        "欺诈": "高",
        "暴雷": "高",
        # 中风险
        "监管": "中",
        "业绩下滑": "中",
        "亏损": "中",
        "减持": "中",
        "质押": "中",
        "诉讼": "中",
        "解禁": "中",
        "商誉减值": "中",
        "坏账": "中",
        # 低风险
        "预警": "低",
        "下调": "低",
        "不及预期": "低",
        "放缓": "低",
        "承压": "低",
    }

    # 正面新闻关键词
    POSITIVE_KEYWORDS: List[str] = [
        "利好", "增长", "突破", "创新高", "获批", "中标",
        "合作", "签约", "回购", "增持", "分红", "业绩预增",
        "订单", "扩产", "上线", "发布", "量产", "扭亏",
        "超预期", "景气", "龙头", "领先",
    ]

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

        # LLM增强分析：基于真实新闻内容进行情感分析和影响评估
        if self.llm:
            try:
                llm_insight = self._llm_enhance_analysis(
                    stock_data, key_news, key_announcements, risk_events, signal
                )
                if llm_insight.get("summary"):
                    summary = llm_insight["summary"]
            except Exception as e:
                logger.warning(f"[{self.name}] LLM增强分析失败，使用规则引擎结果: {e}")

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
        
        self.log_analysis(analysis.model_dump())
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
        """分析宏观影响，覆盖10+行业"""
        industry = stock_data.industry or "未知"

        # 基于行业的宏观分析模板
        macro_analysis_map = {
            "银行": "关注货币政策、利率变化、LPR调整对银行业净息差的影响",
            "房地产": "关注房地产政策调控、利率环境变化、房企融资政策及销售数据",
            "医药": "关注医保政策、集采政策、创新药审批、医保目录调整",
            "新能源": "关注双碳政策、补贴政策、技术迭代、光伏/风电装机数据",
            "科技": "关注科技产业政策、中美科技关系、半导体国产化进展",
            "消费": "关注消费刺激政策、社零数据、居民收入与消费信心指数",
            "汽车": "关注新能源车补贴政策、智能网联政策、汽车出口数据",
            "军工": "关注国防预算、地缘政治局势、军工订单与交付节奏",
            "半导体": "关注芯片产业政策、国产替代进程、全球半导体周期",
            "化工": "关注环保政策、大宗商品价格走势、产能出清进度",
            "钢铁": "关注供给侧改革、铁矿石价格、基建投资力度",
            "煤炭": "关注能源保供政策、煤价调控、双碳转型节奏",
            "有色金属": "关注全球大宗商品价格、新能源金属需求、库存变化",
            "电力": "关注电价改革、新能源并网政策、电力供需格局",
            "通信": "关注5G/6G建设进度、运营商资本开支、通信设备国产化",
        }

        return macro_analysis_map.get(industry, "关注宏观经济形势和政策变化")
    
    def _analyze_industry_updates(self, stock_data: StockData) -> str:
        """分析行业动态，基于行业的动态分析模板"""
        industry = stock_data.industry

        if not industry:
            return "行业信息待补充"

        # 行业动态分析模板
        industry_templates = {
            "银行": "银行业动态：关注信贷投放节奏、不良率变化、净息差走势及理财业务转型进展",
            "房地产": "房地产行业动态：关注销售面积与金额、土拍热度、房企融资渠道及保交楼进展",
            "医药": "医药行业动态：关注新药获批进度、集采中标情况、医保谈判结果及创新药出海进展",
            "新能源": "新能源行业动态：关注光伏/风电/储能装机量、产业链价格走势及技术路线迭代",
            "科技": "科技行业动态：关注AI大模型落地进展、云计算需求、信创推进及海外市场拓展",
            "消费": "消费行业动态：关注社零增速、线上/线下渠道变化、品牌升级及消费新趋势",
            "汽车": "汽车行业动态：关注新能源车渗透率、智能化进展、出口数据及价格战态势",
            "军工": "军工行业动态：关注军品订单交付、新型号列装进展及军民融合项目推进",
            "半导体": "半导体行业动态：关注晶圆厂产能利用率、先进制程突破、设备国产化率及下游需求",
            "化工": "化工行业动态：关注产品价格价差、产能投放节奏及环保限产影响",
            "钢铁": "钢铁行业动态：关注粗钢产量、库存变化、钢价走势及下游需求恢复情况",
            "煤炭": "煤炭行业动态：关注产量与进口量、港口库存、长协煤价及转型布局进展",
            "有色金属": "有色金属行业动态：关注铜铝锌价格、锂钴镍供需格局及再生金属发展",
            "电力": "电力行业动态：关注发电量增速、新能源装机占比及电改政策推进",
            "通信": "通信行业动态：关注5G用户渗透率、算力网络建设及物联网应用场景拓展",
        }

        template = industry_templates.get(industry)
        if template:
            return template

        return f"{industry}行业动态追踪中，建议关注行业龙头动向和政策变化"
    
    def _identify_risk_events(
        self,
        news: List[Dict],
        announcements: List[Dict]
    ) -> List[Dict[str, str]]:
        """
        识别风险事件，为每个风险关键词分配严重等级

        Returns:
            结构化风险列表，每项包含 keyword、level、title 字段
        """
        risk_events: List[Dict[str, str]] = []
        seen_titles: set = set()

        for item in news + announcements:
            title = item.get("title", "")
            for keyword, level in self.RISK_KEYWORDS.items():
                if keyword in title and title not in seen_titles:
                    risk_events.append({
                        "keyword": keyword,
                        "level": level,
                        "title": title[:50] + "..." if len(title) > 50 else title,
                    })
                    seen_titles.add(title)
                    break

        # 按风险等级排序：高 > 中 > 低
        level_order = {"高": 0, "中": 1, "低": 2}
        risk_events.sort(key=lambda x: level_order.get(x["level"], 3))

        return risk_events[:5]
    
    def _generate_signal(
        self,
        news: List[Dict],
        announcements: List[Dict],
        risk_events: List[Dict[str, str]]
    ) -> tuple:
        """
        生成交易信号，综合正面/负面新闻比例与风险事件等级

        Returns:
            (signal, confidence) 元组
        """
        score = 50  # 中性

        # 统计正面新闻数量
        positive_count = 0
        for item in news + announcements:
            title = item.get("title", "")
            if any(kw in title for kw in self.POSITIVE_KEYWORDS):
                positive_count += 1

        # 统计负面新闻数量（基于风险事件）
        negative_count = len(risk_events)

        # 新闻总数
        total_items = len(news) + len(announcements)

        # 正面新闻加分
        if total_items > 0:
            positive_ratio = positive_count / total_items
            score += int(positive_ratio * 20)

        # 风险事件扣分（按等级加权）
        if risk_events:
            level_weight = {"高": 15, "中": 8, "低": 3}
            risk_deduction = sum(
                level_weight.get(event.get("level", "低"), 3) for event in risk_events
            )
            score -= min(40, risk_deduction)

        # 公告数量加分（活跃度）
        if len(announcements) > 5:
            score += 5

        # 确定信号方向
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
        risk_events: List[Dict[str, str]],
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
                level = event.get("level", "未知")
                keyword = event.get("keyword", "")
                title = event.get("title", "")
                lines.append(f"  • [{level}风险-{keyword}] {title}")
            lines.append("")

        lines.append(f"【新闻信号】{signal.value}")

        return "\n".join(lines)

    def _llm_enhance_analysis(
        self,
        stock_data: StockData,
        key_news: List[Dict],
        key_announcements: List[Dict],
        risk_events: List[Dict],
        signal: Signal
    ) -> Dict[str, str]:
        """
        使用LLM对新闻内容进行情感分析和影响评估

        基于真实新闻文本，调用LLM生成深度分析

        Args:
            stock_data: 股票数据
            key_news: 关键新闻列表
            key_announcements: 重要公告列表
            risk_events: 风险事件列表
            signal: 交易信号

        Returns:
            LLM结构化输出字典
        """
        # 构建数据摘要（只包含真实新闻数据）
        data_parts = [
            f"股票={stock_data.stock_name}({stock_data.stock_code})",
            f"行业={stock_data.industry or '未知'}",
            f"新闻数量={len(key_news)}",
            f"公告数量={len(key_announcements)}",
            f"风险事件数量={len(risk_events)}",
            f"信号={signal.value}",
        ]

        # 添加新闻标题（最多5条）
        for i, news in enumerate(key_news[:5]):
            title = news.get("title", "")
            if title:
                data_parts.append(f"新闻{i+1}={title[:50]}")

        # 添加公告标题（最多3条）
        for i, ann in enumerate(key_announcements[:3]):
            title = ann.get("title", "")
            if title:
                data_parts.append(f"公告{i+1}={title[:50]}")

        # 添加风险事件
        for i, event in enumerate(risk_events[:3]):
            level = event.get("level", "未知")
            keyword = event.get("keyword", "")
            title = event.get("title", "")
            data_parts.append(f"风险{i+1}=[{level}风险-{keyword}]{title[:30]}")

        data_summary = ", ".join(data_parts)

        instruction = (
            f"基于以上新闻和公告数据，对{stock_data.stock_name}的新闻面进行深度解读。"
            "请分析：1)新闻整体情感倾向及对股价的可能影响；2)关键风险事件评估；"
            "3)需要重点关注的信息。所有结论必须基于提供的新闻数据，不得编造新闻。"
        )

        output_fields = ["summary", "sentiment_assessment", "key_risks"]

        return self._call_llm_with_data(data_summary, instruction, output_fields)