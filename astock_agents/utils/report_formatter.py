"""报告格式化工具"""

import json
from typing import Optional
from astock_agents.models import AnalysisReport


class ReportFormatter:
    """报告格式化器"""
    
    def format_text(self, report: AnalysisReport, verbose: bool = False) -> str:
        """格式化为纯文本"""
        if report.full_report:
            return report.full_report
        
        lines = [
            f"AStockAgents 分析报告",
            f"股票: {report.stock_name} ({report.stock_code})",
            f"分析时间: {report.analysis_date.strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        if report.final_signal:
            lines.append(f"最终信号: {report.final_signal.value}")
        
        if report.trade_proposal:
            lines.append(f"交易建议: {report.trade_proposal.direction.value}")
            lines.append(f"建议仓位: {report.trade_proposal.position_size_pct}%")
        
        if verbose:
            lines.append("")
            if report.technical:
                lines.append(report.technical.summary)
                lines.append("")
            if report.fundamental:
                lines.append(report.fundamental.summary)
                lines.append("")
        
        return "\n".join(lines)
    
    def format_rich(self, report: AnalysisReport, verbose: bool = False) -> str:
        """格式化为富文本（带颜色）"""
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel
            from rich.text import Text
            
            console = Console()
            
            # 创建主表格
            table = Table(title=f"📊 {report.stock_name} ({report.stock_code}) 分析报告")
            table.add_column("项目", style="cyan")
            table.add_column("内容", style="white")
            
            # 基本信息
            table.add_row("分析时间", report.analysis_date.strftime("%Y-%m-%d %H:%M:%S"))
            if report.current_price:
                table.add_row("当前价格", f"¥{report.current_price:.2f}")
            
            # 最终信号
            if report.final_signal:
                signal_color = "green" if "买入" in report.final_signal.value else "red" if "卖出" in report.final_signal.value else "yellow"
                table.add_row("最终信号", f"[{signal_color}]{report.final_signal.value}[/{signal_color}]")
            
            # 交易建议
            if report.trade_proposal:
                tp = report.trade_proposal
                direction_color = "green" if "买入" in tp.direction.value else "red"
                table.add_row("交易方向", f"[{direction_color}]{tp.direction.value}[/{direction_color}]")
                table.add_row("建议仓位", f"{tp.position_size_pct}%")
                if tp.entry_price:
                    table.add_row("入场价格", f"¥{tp.entry_price:.2f}")
                if tp.target_price:
                    table.add_row("目标价格", f"¥{tp.target_price:.2f}")
                if tp.stop_loss_price:
                    table.add_row("止损价格", f"¥{tp.stop_loss_price:.2f}")
                if tp.expected_return_pct:
                    table.add_row("预期收益", f"{tp.expected_return_pct:.1f}%")
                if tp.risk_reward_ratio:
                    table.add_row("盈亏比", f"1:{tp.risk_reward_ratio:.1f}")
            
            # 风险评估
            if report.risk_assessment:
                ra = report.risk_assessment
                risk_color = "red" if ra.risk_level.value == "高风险" else "yellow" if ra.risk_level.value == "中等风险" else "green"
                table.add_row("风险等级", f"[{risk_color}]{ra.risk_level.value}[/{risk_color}]")
                table.add_row("风险评分", f"{ra.risk_score}/100")
                approval = "✅ 通过" if ra.approved else "❌ 未通过"
                table.add_row("风控审批", approval)
            
            # 输出
            console.print(table)
            
            # 详细分析
            if verbose:
                if report.technical:
                    console.print(Panel(report.technical.summary, title="[cyan]技术分析[/cyan]"))
                if report.fundamental:
                    console.print(Panel(report.fundamental.summary, title="[green]基本面分析[/green]"))
                if report.sentiment:
                    console.print(Panel(report.sentiment.summary, title="[yellow]情绪分析[/yellow]"))
                if report.news:
                    console.print(Panel(report.news.summary, title="[blue]新闻分析[/blue]"))
                if report.debate:
                    debate_text = f"获胜方: {report.debate.winning_side}\n"
                    debate_text += f"多头论据: {len(report.debate.bull_arguments)}条\n"
                    debate_text += f"空头论据: {len(report.debate.bear_arguments)}条"
                    console.print(Panel(debate_text, title="[magenta]多空辩论[/magenta]"))
            
            return ""
            
        except ImportError:
            # 如果没有rich，回退到纯文本
            return self.format_text(report, verbose)
    
    def format_json(self, report: AnalysisReport) -> str:
        """格式化为JSON"""
        return json.dumps(report.model_dump(), ensure_ascii=False, indent=2, default=str)