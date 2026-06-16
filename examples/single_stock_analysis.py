#!/usr/bin/env python3
"""
单股票分析示例

Usage:
    python single_stock_analysis.py --code 000001.SZ --name 平安银行
    python single_stock_analysis.py --code 000001.SZ --verbose
"""

import argparse
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from astock_agents.workflow import AnalysisWorkflow
from astock_agents.utils.report_formatter import ReportFormatter


def main():
    parser = argparse.ArgumentParser(description="AQuant-Agent 单股票分析")
    parser.add_argument(
        "--code",
        type=str,
        required=True,
        help="股票代码，如 000001.SZ、600519.SH"
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="股票名称（可选）"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细报告"
    )
    parser.add_argument(
        "--format",
        type=str,
        default="rich",
        choices=["rich", "text", "json"],
        help="输出格式"
    )
    
    args = parser.parse_args()
    
    print(f"🚀 启动 AQuant-Agent 分析...")
    print(f"📊 分析股票: {args.code} {args.name or ''}")
    print("-" * 60)
    
    # 初始化工作流
    workflow = AnalysisWorkflow()
    
    # 执行分析
    try:
        report = workflow.analyze(
            stock_code=args.code,
            stock_name=args.name
        )
        
        # 格式化输出
        formatter = ReportFormatter()
        
        if args.format == "rich":
            output = formatter.format_rich(report, verbose=args.verbose)
        elif args.format == "json":
            output = formatter.format_json(report)
        else:
            output = formatter.format_text(report, verbose=args.verbose)
        
        print(output)
        
        # 保存报告
        if report.full_report:
            output_file = f"report_{args.code.replace('.', '_')}.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report.full_report)
            print(f"\n💾 报告已保存: {output_file}")
        
        return 0
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())