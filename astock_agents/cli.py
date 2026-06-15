"""AQuant-Agent 命令行界面"""

import argparse
import sys
import os
from typing import Optional
from datetime import datetime

from loguru import logger


def _setup_logging(level: str = "INFO"):
    """配置日志"""
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>"
    )


def _load_config(config_path: Optional[str] = None) -> dict:
    """加载配置文件"""
    import yaml

    if config_path is None:
        config_path = os.environ.get("ASTOCK_CONFIG", "config.yaml")

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _print_banner():
    """打印横幅"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║  AQuant-Agent - A股量化智能体 v0.1.0                        ║
╚══════════════════════════════════════════════════════════════╝
""")


def cmd_analyze(args):
    """执行股票分析"""
    from astock_agents.workflow.analysis_workflow import AnalysisWorkflow
    from astock_agents.utils.report_formatter import ReportFormatter

    _setup_logging(args.log_level)
    config = _load_config(args.config)

    _print_banner()
    print(f"分析股票: {args.name or args.code}")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    # 初始化工作流
    workflow = AnalysisWorkflow(config=config)

    # 执行分析
    report = workflow.analyze(
        stock_code=args.code,
        stock_name=args.name
    )

    # 格式化输出
    formatter = ReportFormatter()

    if args.format == "json":
        print(formatter.format_json(report))
    elif args.format == "text":
        print(formatter.format_text(report, verbose=args.verbose))
    else:
        # 默认使用 rich 格式
        formatter.format_rich(report, verbose=args.verbose)

    # 保存报告
    if args.save and report:
        save_dir = config.get("output", {}).get("report_path", "./reports")
        os.makedirs(save_dir, exist_ok=True)
        filename = f"{report.stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(save_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report.full_report or "")
        print(f"\n报告已保存: {filepath}")


def cmd_batch(args):
    """批量分析"""
    from astock_agents.workflow.analysis_workflow import AnalysisWorkflow
    from astock_agents.utils.report_formatter import ReportFormatter

    _setup_logging(args.log_level)
    config = _load_config(args.config)

    _print_banner()

    # 解析股票列表
    stocks = []
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(",")
                stocks.append((parts[0].strip(), parts[1].strip() if len(parts) > 1 else None))
    else:
        # 默认热门股票
        stocks = [
            ("600519.SH", "贵州茅台"),
            ("000858.SZ", "五粮液"),
            ("000001.SZ", "平安银行"),
        ]

    workflow = AnalysisWorkflow(config=config)
    formatter = ReportFormatter()

    results = []
    for code, name in stocks:
        print(f"\n{'=' * 60}")
        print(f"分析: {name or code} ({code})")
        print(f"{'=' * 60}")

        try:
            report = workflow.analyze(stock_code=code, stock_name=name)
            signal = report.final_signal.value if report.final_signal else "N/A"
            confidence = report.final_confidence or 0
            print(f"信号: {signal}, 置信度: {confidence}%")
            results.append((code, name or code, signal, confidence))
        except Exception as e:
            print(f"分析失败: {e}")
            results.append((code, name or code, "ERROR", 0))

    # 汇总
    print(f"\n{'=' * 60}")
    print("批量分析汇总")
    print(f"{'=' * 60}")
    for code, name, signal, confidence in results:
        print(f"  {name}({code}): {signal} ({confidence}%)")


def cmd_server(args):
    """启动 Web 服务"""
    from astock_agents.web.app import run_server

    _setup_logging(args.log_level)
    print(f"启动 Web 服务: http://{args.host}:{args.port}")
    run_server(host=args.host, port=args.port)


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="AQuant-Agent - A股量化智能体",
        prog="aquant-agent"
    )
    parser.add_argument("--config", "-c", help="配置文件路径", default=None)
    parser.add_argument("--log-level", help="日志级别", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # analyze 子命令
    analyze_parser = subparsers.add_parser("analyze", help="分析单只股票")
    analyze_parser.add_argument("code", help="股票代码（如 600519.SH）")
    analyze_parser.add_argument("--name", "-n", help="股票名称", default=None)
    analyze_parser.add_argument("--format", "-f", help="输出格式", default="rich",
                                choices=["text", "json", "rich"])
    analyze_parser.add_argument("--verbose", "-v", help="详细输出", action="store_true")
    analyze_parser.add_argument("--save", "-s", help="保存报告", action="store_true")
    analyze_parser.set_defaults(func=cmd_analyze)

    # batch 子命令
    batch_parser = subparsers.add_parser("batch", help="批量分析")
    batch_parser.add_argument("--file", "-f", help="股票列表文件（每行: 代码,名称）")
    batch_parser.set_defaults(func=cmd_batch)

    # server 子命令
    server_parser = subparsers.add_parser("server", help="启动 Web 服务")
    server_parser.add_argument("--host", help="监听地址", default="0.0.0.0")
    server_parser.add_argument("--port", "-p", help="监听端口", type=int, default=8000)
    server_parser.set_defaults(func=cmd_server)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
