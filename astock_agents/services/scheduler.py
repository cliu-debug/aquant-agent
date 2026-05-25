"""APScheduler定时任务调度模块 - 自选股分析、健康检查、投资组合快照

通过 BackgroundScheduler 实现非阻塞定时任务调度，支持环境变量配置。

环境变量：
- ASTOCK_SCHEDULER_ENABLED: 是否启用定时任务（默认 false）
- ASTOCK_SCHEDULER_WATCHLIST_CRON: 自选股分析定时（默认 "0 9 * * 1-5" 工作日9点）
- ASTOCK_SCHEDULER_HEALTH_CRON: 健康检查定时（默认 "*/5 * * * *" 每5分钟）
- ASTOCK_SCHEDULER_PORTFOLIO_CRON: 投资组合快照定时（默认 "30 15 * * 1-5" 工作日15:30）
"""

import os
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from loguru import logger

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from astock_agents.services.watchlist import WatchlistManager
from astock_agents.workflow.analysis_workflow import AnalysisWorkflow
from astock_agents.data.manager import DataManager
from astock_agents.data.circuit_breaker import get_all_circuit_breaker_stats
from astock_agents.db.database import Database
from astock_agents.models.analysis_report import Signal


class MetricsCollector:
    """简易指标收集器 - 记录定时任务执行指标到内存和日志"""

    def __init__(self) -> None:
        """初始化指标收集器"""
        self._metrics: Dict[str, Dict[str, Any]] = {}

    def record(self, name: str, value: Any) -> None:
        """记录指标

        Args:
            name: 指标名称
            value: 指标值
        """
        self._metrics[name] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }
        logger.debug(f"[指标] {name} = {value}")

    def get(self, name: str) -> Optional[Any]:
        """获取指标值

        Args:
            name: 指标名称

        Returns:
            指标值，不存在时返回 None
        """
        entry = self._metrics.get(name)
        return entry["value"] if entry else None

    def get_all(self) -> Dict[str, Any]:
        """获取所有指标

        Returns:
            以指标名称为键、含 value 和 timestamp 的字典为值的字典
        """
        return dict(self._metrics)


class NotificationService:
    """简易通知服务 - 信号变化时触发通知（日志输出）"""

    @staticmethod
    def notify_signal_change(
        stock_code: str,
        stock_name: str,
        old_signal: Optional[str],
        new_signal: str,
    ) -> None:
        """发送信号变化通知

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            old_signal: 旧信号文本
            new_signal: 新信号文本
        """
        logger.warning(
            f"[通知] 信号变化: {stock_name}({stock_code}) "
            f"从 [{old_signal}] 变为 [{new_signal}]"
        )


class SchedulerService:
    """
    APScheduler定时任务调度服务

    功能：
    1. 自选股定时分析（工作日9点）
    2. 健康检查（每5分钟）
    3. 投资组合快照（每天收盘后）
    4. 支持动态添加/移除任务
    5. 通过环境变量配置启用/禁用和定时规则
    """

    # 默认cron表达式
    DEFAULT_WATCHLIST_CRON: str = "0 9 * * 1-5"
    DEFAULT_HEALTH_CRON: str = "*/5 * * * *"
    DEFAULT_PORTFOLIO_CRON: str = "30 15 * * 1-5"

    def __init__(
        self,
        watchlist_manager: Optional[WatchlistManager] = None,
        analysis_workflow: Optional[AnalysisWorkflow] = None,
        data_manager: Optional[DataManager] = None,
        db: Optional[Database] = None,
    ) -> None:
        """
        初始化调度服务

        Args:
            watchlist_manager: 自选股管理器，为空时自动创建
            analysis_workflow: 分析工作流，为空时自动创建
            data_manager: 数据管理器，为空时自动创建
            db: 数据库实例，为空时自动创建
        """
        self._db: Database = db or Database()
        self._watchlist_manager: WatchlistManager = watchlist_manager or WatchlistManager(db=self._db)
        self._analysis_workflow: AnalysisWorkflow = analysis_workflow or AnalysisWorkflow()
        self._data_manager: DataManager = data_manager or DataManager()

        self._metrics: MetricsCollector = MetricsCollector()
        self._notification: NotificationService = NotificationService()

        # 读取环境变量配置
        self._enabled: bool = os.environ.get(
            "ASTOCK_SCHEDULER_ENABLED", "false"
        ).lower() == "true"
        self._watchlist_cron: str = os.environ.get(
            "ASTOCK_SCHEDULER_WATCHLIST_CRON", self.DEFAULT_WATCHLIST_CRON
        )
        self._health_cron: str = os.environ.get(
            "ASTOCK_SCHEDULER_HEALTH_CRON", self.DEFAULT_HEALTH_CRON
        )
        self._portfolio_cron: str = os.environ.get(
            "ASTOCK_SCHEDULER_PORTFOLIO_CRON", self.DEFAULT_PORTFOLIO_CRON
        )

        # 初始化调度器
        self._scheduler: BackgroundScheduler = BackgroundScheduler(
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 60,
            }
        )

        logger.info(
            f"[调度器] 初始化完成, 启用={self._enabled}, "
            f"自选股cron='{self._watchlist_cron}', "
            f"健康检查cron='{self._health_cron}', "
            f"组合快照cron='{self._portfolio_cron}'"
        )

    @property
    def is_running(self) -> bool:
        """
        调度器是否运行中

        Returns:
            运行状态布尔值
        """
        return self._scheduler.running

    def start(self) -> None:
        """
        启动调度器

        注册所有默认定时任务并启动后台调度器。
        如果 ASTOCK_SCHEDULER_ENABLED 不为 true，则仅记录日志不启动。
        """
        if not self._enabled:
            logger.warning("[调度器] 未启用，设置 ASTOCK_SCHEDULER_ENABLED=true 后启动")
            return

        if self.is_running:
            logger.warning("[调度器] 已在运行中，跳过启动")
            return

        # 注册默认定时任务
        self._register_default_jobs()

        # 启动调度器
        self._scheduler.start()
        logger.info("[调度器] 已启动")

    def stop(self) -> None:
        """
        停止调度器

        安全关闭后台调度器，等待当前任务完成。
        """
        if not self.is_running:
            logger.warning("[调度器] 未在运行中，跳过停止")
            return

        self._scheduler.shutdown(wait=True)
        logger.info("[调度器] 已停止")

    def get_jobs(self) -> List[Dict[str, Any]]:
        """
        获取当前任务列表

        Returns:
            任务信息字典列表，每项包含 id、name、next_run_time、trigger
        """
        jobs = self._scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
                "trigger": str(job.trigger),
            }
            for job in jobs
        ]

    def add_job(
        self,
        job_id: str,
        func: Callable,
        trigger: str = "cron",
        **kwargs: Any,
    ) -> None:
        """
        动态添加定时任务

        Args:
            job_id: 任务唯一标识
            func: 任务执行函数
            trigger: 触发器类型（cron / interval / date）
            **kwargs: 传递给触发器的参数（如 cron 表达式参数 hour, minute 等）
        """
        try:
            self._scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
                **kwargs,
            )
            logger.info(f"[调度器] 添加任务: {job_id}")
        except Exception as e:
            logger.error(f"[调度器] 添加任务失败: {job_id}, 错误: {e}")

    def remove_job(self, job_id: str) -> None:
        """
        移除定时任务

        Args:
            job_id: 任务唯一标识
        """
        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"[调度器] 移除任务: {job_id}")
        except Exception as e:
            logger.error(f"[调度器] 移除任务失败: {job_id}, 错误: {e}")

    # ==================== 默认任务注册 ====================

    def _register_default_jobs(self) -> None:
        """注册默认定时任务（自选股分析、健康检查、组合快照）"""
        # 自选股定时分析
        self._scheduler.add_job(
            func=self.watchlist_analysis,
            trigger=CronTrigger.from_crontab(self._watchlist_cron),
            id="watchlist_analysis",
            name="自选股定时分析",
            replace_existing=True,
        )

        # 健康检查
        self._scheduler.add_job(
            func=self.health_check,
            trigger=CronTrigger.from_crontab(self._health_cron),
            id="health_check",
            name="健康检查",
            replace_existing=True,
        )

        # 投资组合快照
        self._scheduler.add_job(
            func=self.portfolio_snapshot,
            trigger=CronTrigger.from_crontab(self._portfolio_cron),
            id="portfolio_snapshot",
            name="投资组合快照",
            replace_existing=True,
        )

        logger.info("[调度器] 默认任务注册完成")

    # ==================== 定时任务实现 ====================

    def watchlist_analysis(self) -> None:
        """
        定时分析自选股

        从 WatchlistManager 获取所有自选股，逐个调用 AnalysisWorkflow.analyze()，
        将结果保存到数据库。如果信号变化（如从买入变卖出），触发通知。
        记录指标到 MetricsCollector。
        """
        try:
            items = self._watchlist_manager.get_all()
            total: int = len(items)
            success_count: int = 0
            signal_change_count: int = 0

            logger.info(f"[自选股分析] 开始分析, 共 {total} 只股票")
            self._metrics.record("watchlist_analysis_total", total)

            for item in items:
                try:
                    # 执行分析
                    report = self._analysis_workflow.analyze(
                        stock_code=item.stock_code,
                        stock_name=item.stock_name,
                    )

                    # 提取信号
                    new_signal: str = (
                        report.final_signal.value
                        if report.final_signal
                        else "未知"
                    )
                    old_signal: Optional[str] = item.last_signal

                    # 保存分析结果到数据库
                    self._db.save_analysis(
                        stock_code=item.stock_code,
                        stock_name=item.stock_name,
                        signal=new_signal,
                        confidence=report.final_confidence or 0,
                        report_json=report.model_dump_json(),
                    )

                    # 更新自选股的最近分析结果
                    self._watchlist_manager.update_analysis_result(
                        stock_code=item.stock_code,
                        signal=new_signal,
                    )

                    # 检测信号方向性反转并触发通知
                    if old_signal and old_signal != new_signal:
                        if self._is_signal_reversed(old_signal, new_signal):
                            self._notification.notify_signal_change(
                                stock_code=item.stock_code,
                                stock_name=item.stock_name,
                                old_signal=old_signal,
                                new_signal=new_signal,
                            )
                            signal_change_count += 1

                    success_count += 1
                    logger.info(
                        f"[自选股分析] {item.stock_name}({item.stock_code}) "
                        f"信号={new_signal}, 置信度={report.final_confidence}"
                    )

                except Exception as e:
                    logger.error(
                        f"[自选股分析] 分析失败: "
                        f"{item.stock_name}({item.stock_code}), 错误: {e}"
                    )

            # 记录指标
            self._metrics.record("watchlist_analysis_success", success_count)
            self._metrics.record("watchlist_analysis_failed", total - success_count)
            self._metrics.record(
                "watchlist_analysis_signal_changes", signal_change_count
            )
            self._metrics.record(
                "watchlist_analysis_last_run", datetime.now().isoformat()
            )

            logger.info(
                f"[自选股分析] 完成: 成功={success_count}, "
                f"失败={total - success_count}, 信号变化={signal_change_count}"
            )

        except Exception as e:
            logger.error(f"[自选股分析] 任务异常: {e}")

    def health_check(self) -> None:
        """
        定时健康检查

        检查数据源可用性，更新断路器状态指标，记录健康状态到日志。
        """
        try:
            # 通过 DataManager 执行健康检查
            health_status: Dict[str, Any] = self._data_manager.health_check()

            # 获取断路器状态
            cb_stats: Dict[str, Dict[str, Any]] = get_all_circuit_breaker_stats()
            open_count: int = sum(
                1
                for stats in cb_stats.values()
                if stats.get("state") == "OPEN"
            )

            # 记录指标
            self._metrics.record(
                "health_status", health_status.get("status", "unknown")
            )
            self._metrics.record("health_open_breakers", open_count)
            self._metrics.record(
                "health_data_sources",
                len(health_status.get("data_sources", [])),
            )
            self._metrics.record(
                "health_check_last_run", datetime.now().isoformat()
            )

            # 记录健康状态到日志
            if health_status.get("status") == "healthy":
                logger.info(
                    f"[健康检查] 状态=正常, "
                    f"数据源={len(health_status.get('data_sources', []))}, "
                    f"断路器OPEN={open_count}"
                )
            else:
                logger.warning(
                    f"[健康检查] 状态=降级, "
                    f"数据源={health_status.get('data_sources', [])}, "
                    f"断路器OPEN={open_count}, "
                    f"详情={health_status.get('open_breakers', [])}"
                )

        except Exception as e:
            logger.error(f"[健康检查] 任务异常: {e}")
            self._metrics.record("health_status", "error")

    def portfolio_snapshot(self) -> None:
        """
        投资组合快照（每天收盘后）

        记录当前组合总值，更新持仓指标。
        """
        try:
            from astock_agents.services.paper_trading import PaperTradingService

            # 获取投资组合
            trading_service: PaperTradingService = PaperTradingService(
                db=self._db
            )
            portfolio = trading_service.get_portfolio()

            # 提取组合指标
            total_value: float = portfolio.total_market_value or 0
            total_pnl: float = portfolio.total_pnl or 0
            total_pnl_pct: float = portfolio.total_pnl_pct or 0

            # 记录指标
            self._metrics.record("portfolio_total_value", total_value)
            self._metrics.record("portfolio_total_pnl", total_pnl)
            self._metrics.record("portfolio_total_pnl_pct", total_pnl_pct)
            self._metrics.record(
                "portfolio_position_count", len(portfolio.positions)
            )
            self._metrics.record(
                "portfolio_available_cash", portfolio.available_cash
            )
            self._metrics.record(
                "portfolio_snapshot_last_run", datetime.now().isoformat()
            )

            logger.info(
                f"[组合快照] 总值={total_value:,.0f}, "
                f"盈亏={total_pnl:,.0f}({total_pnl_pct}%), "
                f"持仓={len(portfolio.positions)}只, "
                f"可用资金={portfolio.available_cash:,.0f}"
            )

        except Exception as e:
            logger.error(f"[组合快照] 任务异常: {e}")

    # ==================== 辅助方法 ====================

    @staticmethod
    def _is_signal_reversed(old_signal: str, new_signal: str) -> bool:
        """
        判断信号是否发生方向性反转

        Args:
            old_signal: 旧信号文本
            new_signal: 新信号文本

        Returns:
            是否发生方向性反转（如从买入变卖出）
        """
        buy_signals = {Signal.BUY.value, Signal.STRONG_BUY.value}
        sell_signals = {Signal.SELL.value, Signal.STRONG_SELL.value}

        old_in_buy: bool = old_signal in buy_signals
        old_in_sell: bool = old_signal in sell_signals
        new_in_buy: bool = new_signal in buy_signals
        new_in_sell: bool = new_signal in sell_signals

        return (old_in_buy and new_in_sell) or (old_in_sell and new_in_buy)


# ==================== 全局单例 ====================

_scheduler_instance: Optional[SchedulerService] = None


def get_scheduler() -> SchedulerService:
    """
    获取全局调度器单例

    Returns:
        SchedulerService 实例
    """
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SchedulerService()
    return _scheduler_instance
