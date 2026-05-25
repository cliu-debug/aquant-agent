"""自选股管理 - 增删改查、分组管理、数据持久化"""

import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from astock_agents.models.portfolio import WatchlistItem, WatchlistGroup, WatchlistGroupInfo


class WatchlistManager:
    """
    自选股管理器

    功能：
    1. 自选股增删改查
    2. 分组管理
    3. JSON文件持久化
    4. 批量操作
    """

    DEFAULT_STORAGE_PATH = "./data/watchlist.json"

    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化自选股管理器

        Args:
            storage_path: 存储文件路径
        """
        self.storage_path = storage_path or self.DEFAULT_STORAGE_PATH
        self._items: List[WatchlistItem] = []
        self._load()
        logger.info(f"[自选股] 初始化完成, {len(self._items)}只股票")

    def add(self, item: WatchlistItem) -> bool:
        """添加自选股"""
        # 检查是否已存在
        existing = self.get_by_code(item.stock_code)
        if existing:
            logger.warning(f"[自选股] 已存在: {item.stock_code}")
            return False

        self._items.append(item)
        self._save()
        logger.info(f"[自选股] 添加: {item.stock_name}({item.stock_code})")
        return True

    def remove(self, stock_code: str) -> bool:
        """移除自选股"""
        before = len(self._items)
        self._items = [i for i in self._items if i.stock_code != stock_code]
        if len(self._items) < before:
            self._save()
            logger.info(f"[自选股] 移除: {stock_code}")
            return True
        return False

    def get_by_code(self, stock_code: str) -> Optional[WatchlistItem]:
        """按代码获取自选股"""
        for item in self._items:
            if item.stock_code == stock_code:
                return item
        return None

    def get_all(self, group: Optional[WatchlistGroup] = None) -> List[WatchlistItem]:
        """获取所有自选股（可按分组筛选）"""
        if group:
            return [i for i in self._items if i.group == group]
        return list(self._items)

    def update(self, stock_code: str, updates: Dict[str, Any]) -> bool:
        """更新自选股信息"""
        item = self.get_by_code(stock_code)
        if not item:
            return False

        for key, value in updates.items():
            if hasattr(item, key):
                setattr(item, key, value)

        self._save()
        logger.info(f"[自选股] 更新: {stock_code}")
        return True

    def update_analysis_result(self, stock_code: str, signal: str) -> bool:
        """更新最近分析结果"""
        return self.update(stock_code, {
            "last_analyzed_at": datetime.now(),
            "last_signal": signal,
        })

    def get_groups(self) -> List[WatchlistGroupInfo]:
        """获取所有分组信息"""
        group_counts: Dict[str, int] = {}
        for item in self._items:
            name = item.group.value
            group_counts[name] = group_counts.get(name, 0) + 1

        groups = []
        for group_enum in WatchlistGroup:
            groups.append(WatchlistGroupInfo(
                name=group_enum.value,
                count=group_counts.get(group_enum.value, 0),
            ))
        return groups

    def move_to_group(self, stock_code: str, group: WatchlistGroup) -> bool:
        """移动到指定分组"""
        return self.update(stock_code, {"group": group})

    def search(self, keyword: str) -> List[WatchlistItem]:
        """搜索自选股（按代码或名称）"""
        keyword = keyword.lower()
        return [
            i for i in self._items
            if keyword in i.stock_code.lower() or keyword in i.stock_name.lower()
        ]

    def count(self) -> int:
        """获取自选股总数"""
        return len(self._items)

    def _save(self):
        """保存到文件"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            data = [item.model_dump() for item in self._items]
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"[自选股] 保存失败: {e}")

    def _load(self):
        """从文件加载"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._items = [WatchlistItem(**item) for item in data]
        except Exception as e:
            logger.warning(f"[自选股] 加载失败: {e}, 使用空列表")
            self._items = []
