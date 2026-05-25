"""分析工作流 - 使用LangGraph编排多智能体协作"""

from typing import Dict, Any, Optional, TypedDict, Annotated
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

from astock_agents.data import DataManager
from astock_agents.agents import (
    TechnicalAnalyst, FundamentalAnalyst, SentimentAnalyst, NewsAnalyst,
    BullResearcher, BearResearcher, Trader, RiskManager
)
from astock_agents.models import (
    StockData, AnalysisReport, TechnicalAnalysis, FundamentalAnalysis,
    SentimentAnalysis, NewsAnalysis, DebateResult, TradeProposal, RiskAssessment
)


# 定义工作流状态
class WorkflowState(TypedDict):
    """工作流状态"""
    stock_code: str
    stock_name: str
    stock_data: Optional[StockData]
    
    # 各维度分析结果
    technical: Optional[TechnicalAnalysis]
    fundamental: Optional[FundamentalAnalysis]
    sentiment: Optional[SentimentAnalysis]
    news: Optional[NewsAnalysis]
    
    # 辩论结果
    debate: Optional[DebateResult]
    
    # 交易提案
    trade_proposal: Optional[TradeProposal]
    
    # 风险评估
    risk_assessment: Optional[RiskAssessment]
    
    # 最终报告
    report: Optional[AnalysisReport]
    
    # 错误信息
    error: Optional[str]


class AnalysisWorkflow:
    """分析工作流 - 编排多智能体协作完成股票分析"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化分析工作流
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 初始化数据管理器
        self.data_manager = DataManager(config)
        
        # 初始化各智能体
        self.technical_analyst = TechnicalAnalyst(config=config)
        self.fundamental_analyst = FundamentalAnalyst(config=config)
        self.sentiment_analyst = SentimentAnalyst(config=config)
        self.news_analyst = NewsAnalyst(config=config)
        self.bull_researcher = BullResearcher(config=config)
        self.bear_researcher = BearResearcher(config=config)
        self.trader = Trader(config=config)
        self.risk_manager = RiskManager(config=config)
        
        # 构建工作流图
        self.workflow = self._build_workflow()
        
        logger.info("分析工作流初始化完成")
    
    def _build_workflow(self) -> StateGraph:
        """构建工作流图"""
        # 创建状态图
        workflow = StateGraph(WorkflowState)
        
        # 添加节点
        workflow.add_node("fetch_data", self._fetch_data_node)
        workflow.add_node("technical_analysis", self._technical_analysis_node)
        workflow.add_node("fundamental_analysis", self._fundamental_analysis_node)
        workflow.add_node("sentiment_analysis", self._sentiment_analysis_node)
        workflow.add_node("news_analysis", self._news_analysis_node)
        workflow.add_node("debate", self._debate_node)
        workflow.add_node("generate_proposal", self._generate_proposal_node)
        workflow.add_node("risk_assessment", self._risk_assessment_node)
        workflow.add_node("generate_report", self._generate_report_node)
        
        # 添加边 - 第一层：数据获取后并行分析
        workflow.add_edge("fetch_data", "technical_analysis")
        workflow.add_edge("fetch_data", "fundamental_analysis")
        workflow.add_edge("fetch_data", "sentiment_analysis")
        workflow.add_edge("fetch_data", "news_analysis")
        
        # 第二层：所有分析完成后进行辩论
        workflow.add_edge("technical_analysis", "debate")
        workflow.add_edge("fundamental_analysis", "debate")
        workflow.add_edge("sentiment_analysis", "debate")
        workflow.add_edge("news_analysis", "debate")
        
        # 第三层：辩论后生成交易提案
        workflow.add_edge("debate", "generate_proposal")
        
        # 第四层：风险评估
        workflow.add_edge("generate_proposal", "risk_assessment")
        
        # 第五层：生成最终报告
        workflow.add_edge("risk_assessment", "generate_report")
        
        # 结束
        workflow.add_edge("generate_report", END)
        
        # 设置入口
        workflow.set_entry_point("fetch_data")
        
        return workflow.compile()
    
    def _fetch_data_node(self, state: WorkflowState) -> WorkflowState:
        """数据获取节点"""
        logger.info(f"[工作流] 获取数据: {state['stock_code']}")
        
        try:
            stock_data = self.data_manager.get_stock_data(
                stock_code=state['stock_code'],
                stock_name=state['stock_name'],
                days=250
            )
            
            state['stock_data'] = stock_data
            if stock_data:
                state['stock_name'] = stock_data.stock_name
            
            logger.info(f"[工作流] 数据获取完成: {stock_data.stock_name if stock_data else '失败'}")
            
        except Exception as e:
            logger.error(f"[工作流] 数据获取失败: {e}")
            state['error'] = f"数据获取失败: {str(e)}"
        
        return state
    
    def _technical_analysis_node(self, state: WorkflowState) -> WorkflowState:
        """技术分析节点"""
        logger.info("[工作流] 执行技术分析")
        
        if state.get('error') or not state.get('stock_data'):
            return state
        
        try:
            analysis = self.technical_analyst.analyze(state['stock_data'])
            state['technical'] = analysis
            logger.info(f"[工作流] 技术分析完成: {analysis.signal.value}")
        except Exception as e:
            logger.error(f"[工作流] 技术分析失败: {e}")
        
        return state
    
    def _fundamental_analysis_node(self, state: WorkflowState) -> WorkflowState:
        """基本面分析节点"""
        logger.info("[工作流] 执行基本面分析")
        
        if state.get('error') or not state.get('stock_data'):
            return state
        
        try:
            analysis = self.fundamental_analyst.analyze(state['stock_data'])
            state['fundamental'] = analysis
            logger.info(f"[工作流] 基本面分析完成: {analysis.signal.value}")
        except Exception as e:
            logger.error(f"[工作流] 基本面分析失败: {e}")
        
        return state
    
    def _sentiment_analysis_node(self, state: WorkflowState) -> WorkflowState:
        """情绪分析节点"""
        logger.info("[工作流] 执行情绪分析")
        
        if state.get('error') or not state.get('stock_data'):
            return state
        
        try:
            analysis = self.sentiment_analyst.analyze(state['stock_data'])
            state['sentiment'] = analysis
            logger.info(f"[工作流] 情绪分析完成: {analysis.signal.value}")
        except Exception as e:
            logger.error(f"[工作流] 情绪分析失败: {e}")
        
        return state
    
    def _news_analysis_node(self, state: WorkflowState) -> WorkflowState:
        """新闻分析节点"""
        logger.info("[工作流] 执行新闻分析")
        
        if state.get('error') or not state.get('stock_data'):
            return state
        
        try:
            analysis = self.news_analyst.analyze(state['stock_data'])
            state['news'] = analysis
            logger.info(f"[工作流] 新闻分析完成: {analysis.signal.value}")
        except Exception as e:
            logger.error(f"[工作流] 新闻分析失败: {e}")
        
        return state
    
    def _debate_node(self, state: WorkflowState) -> WorkflowState:
        """辩论节点"""
        logger.info("[工作流] 执行多空辩论")
        
        if state.get('error') or not all([
            state.get('technical'),
            state.get('fundamental'),
            state.get('sentiment'),
            state.get('news')
        ]):
            logger.warning("[工作流] 辩论节点缺少必要数据，跳过")
            return state
        
        try:
            # 多头研究
            bull_result = self.bull_researcher.analyze(
                stock_data=state['stock_data'],
                technical=state['technical'],
                fundamental=state['fundamental'],
                sentiment=state['sentiment'],
                news=state['news']
            )
            
            # 空头研究
            bear_result = self.bear_researcher.analyze(
                stock_data=state['stock_data'],
                technical=state['technical'],
                fundamental=state['fundamental'],
                sentiment=state['sentiment'],
                news=state['news']
            )
            
            # 构建辩论结果
            debate = DebateResult(
                bull_arguments=bull_result['arguments'],
                bull_confidence=bull_result['confidence'],
                bear_arguments=bear_result['arguments'],
                bear_confidence=bear_result['confidence'],
                debate_summary=self._summarize_debate(bull_result, bear_result),
                winning_side=self._determine_winner(bull_result, bear_result),
                key_disagreements=self._find_disagreements(bull_result, bear_result)
            )
            
            state['debate'] = debate
            logger.info(f"[工作流] 辩论完成: 获胜方 {debate.winning_side}")
            
        except Exception as e:
            logger.error(f"[工作流] 辩论失败: {e}")
        
        return state
    
    def _generate_proposal_node(self, state: WorkflowState) -> WorkflowState:
        """生成交易提案节点"""
        logger.info("[工作流] 生成交易提案")
        
        if state.get('error') or not state.get('debate'):
            logger.warning("[工作流] 缺少辩论结果，跳过交易提案")
            return state
        
        try:
            proposal = self.trader.analyze(
                stock_data=state['stock_data'],
                technical=state['technical'],
                fundamental=state['fundamental'],
                sentiment=state['sentiment'],
                news=state['news'],
                debate=state['debate']
            )
            
            state['trade_proposal'] = proposal
            logger.info(f"[工作流] 交易提案完成: {proposal.direction.value}")
            
        except Exception as e:
            logger.error(f"[工作流] 交易提案失败: {e}")
        
        return state
    
    def _risk_assessment_node(self, state: WorkflowState) -> WorkflowState:
        """风险评估节点"""
        logger.info("[工作流] 执行风险评估")
        
        if state.get('error') or not state.get('trade_proposal'):
            logger.warning("[工作流] 缺少交易提案，跳过风险评估")
            return state
        
        try:
            assessment = self.risk_manager.analyze(
                stock_data=state['stock_data'],
                trade_proposal=state['trade_proposal']
            )
            
            state['risk_assessment'] = assessment
            logger.info(f"[工作流] 风险评估完成: {assessment.risk_level.value}, 批准: {assessment.approved}")
            
        except Exception as e:
            logger.error(f"[工作流] 风险评估失败: {e}")
        
        return state
    
    def _generate_report_node(self, state: WorkflowState) -> WorkflowState:
        """生成报告节点"""
        logger.info("[工作流] 生成分析报告")
        
        if state.get('error'):
            return state
        
        try:
            report = AnalysisReport(
                stock_code=state['stock_code'],
                stock_name=state['stock_name'],
                current_price=state['stock_data'].current_price if state.get('stock_data') else None,
                technical=state.get('technical'),
                fundamental=state.get('fundamental'),
                sentiment=state.get('sentiment'),
                news=state.get('news'),
                debate=state.get('debate'),
                trade_proposal=state.get('trade_proposal'),
                risk_assessment=state.get('risk_assessment'),
                final_signal=state['trade_proposal'].direction if state.get('trade_proposal') else None,
                final_confidence=self._calculate_final_confidence(state),
                full_report=self._generate_full_report_text(state)
            )
            
            state['report'] = report
            logger.info("[工作流] 分析报告生成完成")
            
        except Exception as e:
            logger.error(f"[工作流] 生成报告失败: {e}")
            state['error'] = f"生成报告失败: {str(e)}"
        
        return state
    
    def analyze(self, stock_code: str, stock_name: Optional[str] = None) -> AnalysisReport:
        """
        执行完整分析
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
        
        Returns:
            分析报告
        """
        logger.info(f"=" * 50)
        logger.info(f"开始分析: {stock_code} {stock_name or ''}")
        logger.info(f"=" * 50)
        
        # 初始化状态
        initial_state: WorkflowState = {
            "stock_code": stock_code,
            "stock_name": stock_name or "",
            "stock_data": None,
            "technical": None,
            "fundamental": None,
            "sentiment": None,
            "news": None,
            "debate": None,
            "trade_proposal": None,
            "risk_assessment": None,
            "report": None,
            "error": None
        }
        
        # 执行工作流
        final_state = self.workflow.invoke(initial_state)
        
        # 返回报告
        if final_state.get("report"):
            return final_state["report"]
        else:
            # 生成错误报告
            return AnalysisReport(
                stock_code=stock_code,
                stock_name=stock_name or stock_code,
                error=final_state.get("error", "未知错误")
            )
    
    # 辅助方法
    def _summarize_debate(self, bull_result: Dict, bear_result: Dict) -> str:
        """总结辩论"""
        bull_count = bull_result.get('argument_count', 0)
        bear_count = bear_result.get('argument_count', 0)
        bull_conf = bull_result.get('confidence', 50)
        bear_conf = bear_result.get('confidence', 50)
        
        return f"多头提出{bull_count}条论据(置信度{bull_conf}%)，空头提出{bear_count}条论据(置信度{bear_conf}%)"
    
    def _determine_winner(self, bull_result: Dict, bear_result: Dict) -> str:
        """确定获胜方"""
        bull_conf = bull_result.get('confidence', 50)
        bear_conf = bear_result.get('confidence', 50)
        
        if bull_conf > bear_conf + 10:
            return "bull"
        elif bear_conf > bull_conf + 10:
            return "bear"
        else:
            return "neutral"
    
    def _find_disagreements(self, bull_result: Dict, bear_result: Dict) -> list:
        """找出分歧点"""
        # 简化处理
        return ["技术面与基本面信号可能存在分歧"]
    
    def _calculate_final_confidence(self, state: WorkflowState) -> int:
        """计算最终置信度"""
        confidences = []
        
        if state.get('technical'):
            confidences.append(state['technical'].confidence)
        if state.get('fundamental'):
            confidences.append(state['fundamental'].confidence)
        if state.get('sentiment'):
            confidences.append(state['sentiment'].confidence)
        if state.get('news'):
            confidences.append(state['news'].confidence)
        
        if confidences:
            return int(sum(confidences) / len(confidences))
        return 50
    
    def _generate_full_report_text(self, state: WorkflowState) -> str:
        """生成完整报告文本"""
        lines = [
            "=" * 60,
            f"AStockAgents 分析报告",
            f"股票: {state['stock_name']} ({state['stock_code']})",
            f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            ""
        ]
        
        # 技术分析
        if state.get('technical'):
            lines.append(state['technical'].summary)
            lines.append("")
        
        # 基本面分析
        if state.get('fundamental'):
            lines.append(state['fundamental'].summary)
            lines.append("")
        
        # 情绪分析
        if state.get('sentiment'):
            lines.append(state['sentiment'].summary)
            lines.append("")
        
        # 新闻分析
        if state.get('news'):
            lines.append(state['news'].summary)
            lines.append("")
        
        # 辩论结果
        if state.get('debate'):
            debate = state['debate']
            lines.append("【多空辩论】")
            lines.append(f"获胜方: {'多头' if debate.winning_side == 'bull' else '空头' if debate.winning_side == 'bear' else '平局'}")
            lines.append(f"多头论据: {len(debate.bull_arguments)}条")
            lines.append(f"空头论据: {len(debate.bear_arguments)}条")
            lines.append("")
        
        # 交易提案
        if state.get('trade_proposal'):
            lines.append(state['trade_proposal'].proposal_text)
            lines.append("")
        
        # 风险评估
        if state.get('risk_assessment'):
            risk = state['risk_assessment']
            lines.append(f"【风险评估】{risk.risk_level.value}")
            lines.append(f"风险评分: {risk.risk_score}/100")
            lines.append(f"审批结果: {'通过' if risk.approved else '未通过'}")
            lines.append("")
        
        lines.append("=" * 60)
        lines.append("报告生成完毕")
        lines.append("=" * 60)
        
        return "\n".join(lines)