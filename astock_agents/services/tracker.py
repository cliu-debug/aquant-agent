"""单股票追踪服务 - 投资逻辑记录、信号变化追踪、分析快照对比

功能：
1. 创建和管理单股票追踪记录
2. 记录投资逻辑（买入理由、观察指标、退出条件）
3. 保存分析快照，追踪信号变化
4. 对比不同日期的分析结果，识别噪音vs信号
5. SQLite持久化存储
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from loguru import logger

from astock_agents.db.database import Database


# ============================================================
# 数据模型（dataclass，不依赖Pydantic，保持轻量）
# ============================================================


@dataclass
class InvestmentThesis:
    """投资核心逻辑

    Attributes:
        reasons: 买入理由列表
        watch_indicators: 观察指标列表
        exit_conditions: 退出条件列表
        stop_loss_price: 止损价，为空表示未设置
        profit_target_price: 止盈价，为空表示未设置
    """

    reasons: List[str] = field(default_factory=list)
    watch_indicators: List[str] = field(default_factory=list)
    exit_conditions: List[str] = field(default_factory=list)
    stop_loss_price: Optional[float] = None
    profit_target_price: Optional[float] = None


@dataclass
class SignalChange:
    """信号变化记录

    Attributes:
        date: 变化日期
        old_signal: 旧信号
        new_signal: 新信号
        score_change: 评分变化值
        reason: 变化原因
        is_noise: 是否为噪音（vs 真实信号）
        impact_level: 影响级别（high/medium/low）
    """

    date: str = ""
    old_signal: str = ""
    new_signal: str = ""
    score_change: int = 0
    reason: str = ""
    is_noise: bool = False
    impact_level: str = "low"


@dataclass
class AnalysisSnapshot:
    """分析快照

    Attributes:
        date: 快照日期
        signal: 信号类型（买入/卖出/持有等）
        score: 综合评分
        confidence: 置信度（0.0~1.0）
        technical_summary: 技术面摘要
        fundamental_summary: 基本面摘要
        sentiment_summary: 情绪面摘要
        key_changes: 关键变化列表
    """

    date: str = ""
    signal: str = ""
    score: int = 0
    confidence: float = 0.0
    technical_summary: str = ""
    fundamental_summary: str = ""
    sentiment_summary: str = ""
    key_changes: List[str] = field(default_factory=list)


@dataclass
class StockTracker:
    """单股票追踪记录

    Attributes:
        id: 追踪唯一标识
        stock_code: 股票代码
        stock_name: 股票名称
        investment_thesis: 投资逻辑，为空表示未设置
        start_date: 开始追踪日期
        last_analysis_date: 最后分析日期，为空表示尚未分析
        snapshots: 分析快照列表
        signal_changes: 信号变化记录列表
        is_active: 是否活跃追踪中
    """

    id: str = ""
    stock_code: str = ""
    stock_name: str = ""
    investment_thesis: Optional[InvestmentThesis] = None
    start_date: str = ""
    last_analysis_date: Optional[str] = None
    snapshots: List[AnalysisSnapshot] = field(default_factory=list)
    signal_changes: List[SignalChange] = field(default_factory=list)
    is_active: bool = True


# ============================================================
# 噪音判断用的短期技术指标关键词
# ============================================================

_NOISE_INDICATORS = {"RSI", "KDJ", "MACD", "布林带", "BOLL", "WR", "DMI", "OBV"}


# ============================================================
# TrackerService 服务类
# ============================================================


class TrackerService:
    """单股票追踪服务

    提供股票追踪记录的创建、查询、更新、信号变化分析和快照对比功能。
    数据持久化到SQLite，通过Database类管理连接。
    """

    def __init__(self, db: Optional[Database] = None):
        """初始化追踪服务

        Args:
            db: 数据库实例，为空时自动创建默认实例
        """
        self._db = db or Database()
        self._init_tables()
        logger.info("[追踪服务] 初始化完成")

    def _init_tables(self) -> None:
        """创建 stock_trackers 表（如果不存在）"""
        conn = self._db._get_conn()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_trackers (
                    id TEXT PRIMARY KEY,
                    stock_code TEXT NOT NULL,
                    stock_name TEXT NOT NULL,
                    investment_thesis TEXT,
                    start_date TEXT NOT NULL,
                    last_analysis_date TEXT,
                    snapshots TEXT,
                    signal_changes TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_trackers_stock_code ON stock_trackers(stock_code)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_trackers_is_active ON stock_trackers(is_active)"
            )
            conn.commit()
        except Exception as e:
            logger.error(f"[追踪服务] 建表失败: {e}")
        finally:
            conn.close()

    # ----------------------------------------------------------
    # 创建追踪
    # ----------------------------------------------------------

    def create_tracker(
        self,
        stock_code: str,
        stock_name: str,
        thesis: Optional[InvestmentThesis] = None,
    ) -> Optional[StockTracker]:
        """创建单股票追踪记录

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            thesis: 投资逻辑，为空时不设置

        Returns:
            创建的追踪记录，失败时返回None
        """
        try:
            # 检查是否已存在活跃追踪
            existing = self.get_tracker_by_stock(stock_code)
            if existing and existing.is_active:
                logger.warning(f"[追踪服务] 股票 {stock_code} 已存在活跃追踪: {existing.id}")
                return None

            tracker_id = uuid.uuid4().hex[:12]
            today = datetime.now().strftime("%Y-%m-%d")
            tracker = StockTracker(
                id=tracker_id,
                stock_code=stock_code,
                stock_name=stock_name,
                investment_thesis=thesis,
                start_date=today,
                last_analysis_date=None,
                snapshots=[],
                signal_changes=[],
                is_active=True,
            )

            self._save_tracker(tracker)
            logger.info(f"[追踪服务] 创建追踪: {stock_name}({stock_code}), ID={tracker_id}")
            return tracker
        except Exception as e:
            logger.error(f"[追踪服务] 创建追踪失败: {e}")
            return None

    # ----------------------------------------------------------
    # 查询追踪
    # ----------------------------------------------------------

    def get_tracker(self, tracker_id: str) -> Optional[StockTracker]:
        """按追踪ID获取追踪记录

        Args:
            tracker_id: 追踪唯一标识

        Returns:
            追踪记录，不存在时返回None
        """
        try:
            conn = self._db._get_conn()
            try:
                row = conn.execute(
                    "SELECT * FROM stock_trackers WHERE id=?", (tracker_id,)
                ).fetchone()
            finally:
                conn.close()
            if not row:
                return None
            return self._row_to_tracker(row)
        except Exception as e:
            logger.error(f"[追踪服务] 获取追踪失败: {e}")
            return None

    def get_tracker_by_stock(self, stock_code: str) -> Optional[StockTracker]:
        """按股票代码获取活跃追踪记录

        Args:
            stock_code: 股票代码

        Returns:
            追踪记录，不存在时返回None
        """
        try:
            conn = self._db._get_conn()
            try:
                row = conn.execute(
                    "SELECT * FROM stock_trackers WHERE stock_code=? AND is_active=1 ORDER BY start_date DESC LIMIT 1",
                    (stock_code,),
                ).fetchone()
            finally:
                conn.close()
            if not row:
                return None
            return self._row_to_tracker(row)
        except Exception as e:
            logger.error(f"[追踪服务] 按股票代码获取追踪失败: {e}")
            return None

    def list_trackers(self, active_only: bool = True) -> List[StockTracker]:
        """列出所有追踪记录

        Args:
            active_only: 是否只返回活跃追踪，默认True

        Returns:
            追踪记录列表
        """
        try:
            conn = self._db._get_conn()
            try:
                if active_only:
                    rows = conn.execute(
                        "SELECT * FROM stock_trackers WHERE is_active=1 ORDER BY start_date DESC"
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM stock_trackers ORDER BY start_date DESC"
                    ).fetchall()
            finally:
                conn.close()
            return [self._row_to_tracker(row) for row in rows]
        except Exception as e:
            logger.error(f"[追踪服务] 列出追踪失败: {e}")
            return []

    # ----------------------------------------------------------
    # 更新投资逻辑
    # ----------------------------------------------------------

    def update_thesis(self, tracker_id: str, thesis: InvestmentThesis) -> bool:
        """更新投资逻辑

        Args:
            tracker_id: 追踪唯一标识
            thesis: 新的投资逻辑

        Returns:
            是否更新成功
        """
        try:
            tracker = self.get_tracker(tracker_id)
            if not tracker:
                logger.warning(f"[追踪服务] 追踪不存在: {tracker_id}")
                return False

            tracker.investment_thesis = thesis
            self._save_tracker(tracker)
            logger.info(f"[追踪服务] 更新投资逻辑: {tracker.stock_code}, ID={tracker_id}")
            return True
        except Exception as e:
            logger.error(f"[追踪服务] 更新投资逻辑失败: {e}")
            return False

    # ----------------------------------------------------------
    # 添加分析快照
    # ----------------------------------------------------------

    def add_snapshot(self, tracker_id: str, snapshot: AnalysisSnapshot) -> bool:
        """添加分析快照，自动检测信号变化

        Args:
            tracker_id: 追踪唯一标识
            snapshot: 分析快照

        Returns:
            是否添加成功
        """
        try:
            tracker = self.get_tracker(tracker_id)
            if not tracker:
                logger.warning(f"[追踪服务] 追踪不存在: {tracker_id}")
                return False

            # 如果存在上一次快照，分析信号变化
            if tracker.snapshots:
                old_snapshot = tracker.snapshots[-1]
                if old_snapshot.signal != snapshot.signal:
                    signal_change = self.analyze_signal_change(old_snapshot, snapshot)
                    signal_change.date = snapshot.date
                    tracker.signal_changes.append(signal_change)

            tracker.snapshots.append(snapshot)
            tracker.last_analysis_date = snapshot.date
            self._save_tracker(tracker)
            logger.info(
                f"[追踪服务] 添加快照: {tracker.stock_code}, 日期={snapshot.date}, 信号={snapshot.signal}"
            )
            return True
        except Exception as e:
            logger.error(f"[追踪服务] 添加快照失败: {e}")
            return False

    # ----------------------------------------------------------
    # 获取信号变化时间线
    # ----------------------------------------------------------

    def get_signal_timeline(
        self, tracker_id: str, days: int = 30
    ) -> List[SignalChange]:
        """获取信号变化时间线

        Args:
            tracker_id: 追踪唯一标识
            days: 回溯天数，默认30天

        Returns:
            信号变化记录列表，按日期倒序
        """
        try:
            tracker = self.get_tracker(tracker_id)
            if not tracker:
                return []

            cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            timeline = [
                sc for sc in tracker.signal_changes if sc.date >= cutoff_date
            ]
            # 按日期倒序排列
            timeline.sort(key=lambda x: x.date, reverse=True)
            return timeline
        except Exception as e:
            logger.error(f"[追踪服务] 获取信号时间线失败: {e}")
            return []

    # ----------------------------------------------------------
    # 对比两个日期的分析
    # ----------------------------------------------------------

    def compare_snapshots(
        self, tracker_id: str, date1: str, date2: str
    ) -> Dict[str, Any]:
        """对比两个日期的分析快照

        Args:
            tracker_id: 追踪唯一标识
            date1: 第一个日期（较早）
            date2: 第二个日期（较晚）

        Returns:
            对比结果字典，包含两个快照及差异分析
        """
        try:
            tracker = self.get_tracker(tracker_id)
            if not tracker:
                return {"error": "追踪不存在"}

            snap1 = self._find_snapshot(tracker, date1)
            snap2 = self._find_snapshot(tracker, date2)

            if not snap1:
                return {"error": f"未找到日期 {date1} 的快照"}
            if not snap2:
                return {"error": f"未找到日期 {date2} 的快照"}

            result: Dict[str, Any] = {
                "tracker_id": tracker_id,
                "stock_code": tracker.stock_code,
                "stock_name": tracker.stock_name,
                "snapshot_1": asdict(snap1),
                "snapshot_2": asdict(snap2),
                "diff": {
                    "score_change": snap2.score - snap1.score,
                    "confidence_change": round(snap2.confidence - snap1.confidence, 4),
                    "signal_changed": snap1.signal != snap2.signal,
                    "old_signal": snap1.signal,
                    "new_signal": snap2.signal,
                },
            }

            # 如果信号变化，附带信号变化分析
            if snap1.signal != snap2.signal:
                signal_change = self.analyze_signal_change(snap1, snap2)
                result["signal_change_analysis"] = asdict(signal_change)

            return result
        except Exception as e:
            logger.error(f"[追踪服务] 对比快照失败: {e}")
            return {"error": str(e)}

    # ----------------------------------------------------------
    # 分析信号变化原因
    # ----------------------------------------------------------

    def analyze_signal_change(
        self, old_snapshot: AnalysisSnapshot, new_snapshot: AnalysisSnapshot
    ) -> SignalChange:
        """分析信号变化原因，判断影响级别和是否噪音

        逻辑：
        - 买入→卖出 或 卖出→买入: impact_level="high"
        - 买入→持有 或 卖出→持有: impact_level="medium"
        - 其他变化: impact_level="low"
        - is_noise: 变化仅涉及短期技术指标（RSI/KDJ等）时为True

        Args:
            old_snapshot: 旧的分析快照
            new_snapshot: 新的分析快照

        Returns:
            信号变化记录
        """
        old_signal = old_snapshot.signal
        new_signal = new_snapshot.signal
        score_change = new_snapshot.score - old_snapshot.score

        # 判断影响级别
        impact_level = self._determine_impact_level(old_signal, new_signal)

        # 判断是否噪音
        is_noise = self._is_noise_change(old_snapshot, new_snapshot)

        # 提取变化原因
        reason = self._extract_change_reason(old_snapshot, new_snapshot)

        return SignalChange(
            date=new_snapshot.date,
            old_signal=old_signal,
            new_signal=new_signal,
            score_change=score_change,
            reason=reason,
            is_noise=is_noise,
            impact_level=impact_level,
        )

    # ----------------------------------------------------------
    # 停止追踪
    # ----------------------------------------------------------

    def deactivate_tracker(self, tracker_id: str) -> bool:
        """停止追踪（软删除，标记为不活跃）

        Args:
            tracker_id: 追踪唯一标识

        Returns:
            是否操作成功
        """
        try:
            tracker = self.get_tracker(tracker_id)
            if not tracker:
                logger.warning(f"[追踪服务] 追踪不存在: {tracker_id}")
                return False

            tracker.is_active = False
            self._save_tracker(tracker)
            logger.info(f"[追踪服务] 停止追踪: {tracker.stock_code}, ID={tracker_id}")
            return True
        except Exception as e:
            logger.error(f"[追踪服务] 停止追踪失败: {e}")
            return False

    # ----------------------------------------------------------
    # 删除追踪
    # ----------------------------------------------------------

    def delete_tracker(self, tracker_id: str) -> bool:
        """删除追踪记录（硬删除）

        Args:
            tracker_id: 追踪唯一标识

        Returns:
            是否删除成功
        """
        try:
            conn = self._db._get_conn()
            try:
                cursor = conn.execute(
                    "DELETE FROM stock_trackers WHERE id=?", (tracker_id,)
                )
                conn.commit()
                deleted = cursor.rowcount > 0
            finally:
                conn.close()

            if deleted:
                logger.info(f"[追踪服务] 删除追踪: ID={tracker_id}")
            else:
                logger.warning(f"[追踪服务] 追踪不存在: {tracker_id}")
            return deleted
        except Exception as e:
            logger.error(f"[追踪服务] 删除追踪失败: {e}")
            return False

    # ===========================================================
    # 内部辅助方法
    # ===========================================================

    def _save_tracker(self, tracker: StockTracker) -> None:
        """保存追踪记录到数据库（INSERT OR REPLACE）

        Args:
            tracker: 追踪记录
        """
        thesis_json = (
            json.dumps(asdict(tracker.investment_thesis), ensure_ascii=False)
            if tracker.investment_thesis
            else None
        )
        snapshots_json = json.dumps(
            [asdict(s) for s in tracker.snapshots], ensure_ascii=False
        )
        changes_json = json.dumps(
            [asdict(c) for c in tracker.signal_changes], ensure_ascii=False
        )

        conn = self._db._get_conn()
        try:
            conn.execute(
                """INSERT OR REPLACE INTO stock_trackers
                (id, stock_code, stock_name, investment_thesis, start_date,
                 last_analysis_date, snapshots, signal_changes, is_active)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    tracker.id,
                    tracker.stock_code,
                    tracker.stock_name,
                    thesis_json,
                    tracker.start_date,
                    tracker.last_analysis_date,
                    snapshots_json,
                    changes_json,
                    1 if tracker.is_active else 0,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _row_to_tracker(self, row: Any) -> StockTracker:
        """将数据库行转换为StockTracker对象

        Args:
            row: 数据库行（sqlite3.Row）

        Returns:
            StockTracker对象
        """
        # 解析投资逻辑
        thesis = None
        thesis_raw = row["investment_thesis"]
        if thesis_raw:
            try:
                thesis_data = json.loads(thesis_raw)
                thesis = InvestmentThesis(**thesis_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"[追踪服务] 解析投资逻辑失败: {e}")

        # 解析快照列表
        snapshots: List[AnalysisSnapshot] = []
        snapshots_raw = row["snapshots"]
        if snapshots_raw:
            try:
                for item in json.loads(snapshots_raw):
                    snapshots.append(AnalysisSnapshot(**item))
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"[追踪服务] 解析快照失败: {e}")

        # 解析信号变化列表
        signal_changes: List[SignalChange] = []
        changes_raw = row["signal_changes"]
        if changes_raw:
            try:
                for item in json.loads(changes_raw):
                    signal_changes.append(SignalChange(**item))
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"[追踪服务] 解析信号变化失败: {e}")

        return StockTracker(
            id=row["id"],
            stock_code=row["stock_code"],
            stock_name=row["stock_name"],
            investment_thesis=thesis,
            start_date=row["start_date"],
            last_analysis_date=row["last_analysis_date"],
            snapshots=snapshots,
            signal_changes=signal_changes,
            is_active=bool(row["is_active"]),
        )

    @staticmethod
    def _find_snapshot(
        tracker: StockTracker, date: str
    ) -> Optional[AnalysisSnapshot]:
        """在追踪记录中按日期查找快照

        Args:
            tracker: 追踪记录
            date: 目标日期

        Returns:
            匹配的快照，未找到时返回None
        """
        for snap in tracker.snapshots:
            if snap.date == date:
                return snap
        return None

    @staticmethod
    def _determine_impact_level(old_signal: str, new_signal: str) -> str:
        """判断信号变化的影响级别

        Args:
            old_signal: 旧信号
            new_signal: 新信号

        Returns:
            影响级别（high/medium/low）
        """
        buy_signals = {"买入", "强烈买入", "buy", "strong_buy"}
        sell_signals = {"卖出", "强烈卖出", "sell", "strong_sell"}
        hold_signals = {"持有", "观望", "hold", "neutral"}

        old_lower = old_signal.strip().lower()
        new_lower = new_signal.strip().lower()

        old_is_buy = old_lower in buy_signals or "买" in old_signal
        old_is_sell = old_lower in sell_signals or "卖" in old_signal
        new_is_buy = new_lower in buy_signals or "买" in new_signal
        new_is_sell = new_lower in sell_signals or "卖" in new_signal

        # 买入→卖出 或 卖出→买入：高级别
        if (old_is_buy and new_is_sell) or (old_is_sell and new_is_buy):
            return "high"

        # 买入→持有 或 卖出→持有：中级别
        if (old_is_buy and new_lower in hold_signals) or (
            old_is_sell and new_lower in hold_signals
        ):
            return "medium"

        # 其他变化：低级别
        return "low"

    @staticmethod
    def _is_noise_change(
        old_snapshot: AnalysisSnapshot, new_snapshot: AnalysisSnapshot
    ) -> bool:
        """判断信号变化是否为噪音

        如果变化仅涉及短期技术指标（RSI/KDJ等），则判定为噪音。

        Args:
            old_snapshot: 旧的分析快照
            new_snapshot: 新的分析快照

        Returns:
            是否为噪音
        """
        # 合并两次快照的关键变化
        all_changes = old_snapshot.key_changes + new_snapshot.key_changes

        if not all_changes:
            return False

        # 检查是否所有变化都仅涉及短期技术指标
        noise_indicator_count = 0
        for change in all_changes:
            if any(indicator in change for indicator in _NOISE_INDICATORS):
                noise_indicator_count += 1

        # 如果涉及噪音指标的变化占多数，则判定为噪音
        return noise_indicator_count > len(all_changes) / 2

    @staticmethod
    def _extract_change_reason(
        old_snapshot: AnalysisSnapshot, new_snapshot: AnalysisSnapshot
    ) -> str:
        """从快照中提取变化原因

        优先使用新快照的key_changes，拼接为原因描述。

        Args:
            old_snapshot: 旧的分析快照
            new_snapshot: 新的分析快照

        Returns:
            变化原因描述
        """
        if new_snapshot.key_changes:
            return "; ".join(new_snapshot.key_changes)

        # 回退到技术面/基本面/情绪面摘要差异
        parts = []
        if old_snapshot.technical_summary != new_snapshot.technical_summary:
            parts.append(f"技术面: {new_snapshot.technical_summary}")
        if old_snapshot.fundamental_summary != new_snapshot.fundamental_summary:
            parts.append(f"基本面: {new_snapshot.fundamental_summary}")
        if old_snapshot.sentiment_summary != new_snapshot.sentiment_summary:
            parts.append(f"情绪面: {new_snapshot.sentiment_summary}")

        return "; ".join(parts) if parts else "信号变化原因未明确"


# ============================================================
# 全局单例
# ============================================================

_tracker_service_instance: Optional[TrackerService] = None


def get_tracker_service() -> TrackerService:
    """获取全局追踪服务单例

    Returns:
        TrackerService实例
    """
    global _tracker_service_instance
    if _tracker_service_instance is None:
        _tracker_service_instance = TrackerService()
    return _tracker_service_instance
