"""选股扫描器 - 条件选股、技术形态扫描、板块轮动检测"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger

from astock_agents.models.portfolio import (
    ScreenerCondition, ScreenerConditionType, ScreenerOperator,
    ScreenerPreset, ScreenerResult, ScreenerResponse
)


class StockScreener:
    """
    选股扫描器

    功能：
    1. 条件选股：基于基本面/技术面指标筛选
    2. 技术形态扫描：金叉、突破、放量等
    3. 预设方案：价值投资、成长股、动量策略等
    """

    # 内置预设方案
    BUILTIN_PRESETS = {
        "value_investing": ScreenerPreset(
            name="价值投资",
            description="低PE、低PB、高ROE、高股息率",
            conditions=[
                ScreenerCondition(field=ScreenerConditionType.PE, operator=ScreenerOperator.LT, value=20),
                ScreenerCondition(field=ScreenerConditionType.PB, operator=ScreenerOperator.LT, value=3),
                ScreenerCondition(field=ScreenerConditionType.ROE, operator=ScreenerOperator.GT, value=12),
                ScreenerCondition(field=ScreenerConditionType.DIVIDEND_YIELD, operator=ScreenerOperator.GT, value=0.02),
            ]
        ),
        "growth_stock": ScreenerPreset(
            name="成长股",
            description="高营收增长、高利润增长、中等PE",
            conditions=[
                ScreenerCondition(field=ScreenerConditionType.REVENUE_GROWTH, operator=ScreenerOperator.GT, value=20),
                ScreenerCondition(field=ScreenerConditionType.PROFIT_GROWTH, operator=ScreenerOperator.GT, value=15),
                ScreenerCondition(field=ScreenerConditionType.PE, operator=ScreenerOperator.LT, value=50),
            ]
        ),
        "momentum": ScreenerPreset(
            name="动量策略",
            description="均线多头排列、放量上涨、RSI适中",
            conditions=[
                ScreenerCondition(field=ScreenerConditionType.MA_TREND, operator=ScreenerOperator.EQ, value="多头"),
                ScreenerCondition(field=ScreenerConditionType.VOLUME_RATIO, operator=ScreenerOperator.GT, value=1.5),
                ScreenerCondition(field=ScreenerConditionType.RSI, operator=ScreenerOperator.BETWEEN, value=[40, 70]),
            ]
        ),
        "blue_chip": ScreenerPreset(
            name="蓝筹股",
            description="大市值、高ROE、低负债、高股息",
            conditions=[
                ScreenerCondition(field=ScreenerConditionType.MARKET_CAP, operator=ScreenerOperator.GT, value=500e8),
                ScreenerCondition(field=ScreenerConditionType.ROE, operator=ScreenerOperator.GT, value=10),
                ScreenerCondition(field=ScreenerConditionType.DIVIDEND_YIELD, operator=ScreenerOperator.GT, value=0.03),
            ]
        ),
        "oversold_bounce": ScreenerPreset(
            name="超跌反弹",
            description="RSI超卖、缩量企稳、远离均线",
            conditions=[
                ScreenerCondition(field=ScreenerConditionType.RSI, operator=ScreenerOperator.LT, value=30),
                ScreenerCondition(field=ScreenerConditionType.VOLUME_RATIO, operator=ScreenerOperator.LT, value=0.7),
            ]
        ),
    }

    def __init__(self, data_manager=None):
        """
        初始化选股器

        Args:
            data_manager: DataManager实例，用于获取股票数据
        """
        self.data_manager = data_manager
        self._stock_pool: List[Dict[str, Any]] = []
        logger.info("[选股器] 初始化完成")

    def get_presets(self) -> List[ScreenerPreset]:
        """获取所有预设方案"""
        return list(self.BUILTIN_PRESETS.values())

    def get_preset_by_name(self, name: str) -> Optional[ScreenerPreset]:
        """按名称获取预设方案"""
        return self.BUILTIN_PRESETS.get(name)

    def scan(self, preset_name: Optional[str] = None, conditions: Optional[List[ScreenerCondition]] = None) -> ScreenerResponse:
        """
        执行选股扫描

        Args:
            preset_name: 预设方案名称
            conditions: 自定义条件列表

        Returns:
            选股响应
        """
        # 确定使用哪个条件
        if preset_name:
            preset = self.BUILTIN_PRESETS.get(preset_name)
            if not preset:
                logger.warning(f"[选股器] 预设方案不存在: {preset_name}")
                return ScreenerResponse(preset_name=preset_name or "自定义")
            scan_conditions = preset.conditions
            display_name = preset.name
        elif conditions:
            scan_conditions = conditions
            display_name = "自定义"
        else:
            logger.warning("[选股器] 未指定选股条件")
            return ScreenerResponse(preset_name="无")

        logger.info(f"[选股器] 开始扫描: {display_name}, {len(scan_conditions)}个条件")

        # 获取股票池数据
        stock_pool = self._get_stock_pool()

        # 逐只股票筛选
        results = []
        for stock_info in stock_pool:
            match_score, matched = self._evaluate_stock(stock_info, scan_conditions)
            if match_score > 0:
                result = ScreenerResult(
                    stock_code=stock_info.get("code", ""),
                    stock_name=stock_info.get("name", ""),
                    industry=stock_info.get("industry"),
                    match_score=match_score,
                    matched_conditions=matched,
                    key_metrics=self._extract_key_metrics(stock_info),
                )
                results.append(result)

        # 按匹配度排序
        results.sort(key=lambda x: x.match_score, reverse=True)

        response = ScreenerResponse(
            preset_name=display_name,
            total_matched=len(results),
            results=results[:50],  # 最多返回50只
        )

        logger.info(f"[选股器] 扫描完成: 匹配{len(results)}只")
        return response

    def _get_stock_pool(self) -> List[Dict[str, Any]]:
        """获取股票池数据"""
        if self._stock_pool:
            return self._stock_pool

        # 尝试从数据源获取
        if self.data_manager:
            try:
                # 使用akshare获取A股列表
                import akshare as ak
                df = ak.stock_zh_a_spot_em()
                if df is not None and not df.empty:
                    self._stock_pool = []
                    for _, row in df.iterrows():
                        self._stock_pool.append({
                            "code": str(row.get("代码", "")),
                            "name": str(row.get("名称", "")),
                            "industry": str(row.get("行业", "")) if "行业" in row.index else None,
                            "price": self._safe_float(row.get("最新价")),
                            "pe": self._safe_float(row.get("市盈率-动态")),
                            "pb": self._safe_float(row.get("市净率")),
                            "market_cap": self._safe_float(row.get("总市值")),
                            "turnover_rate": self._safe_float(row.get("换手率")),
                            "volume_ratio": self._safe_float(row.get("量比")),
                            "change_pct": self._safe_float(row.get("涨跌幅")),
                        })
                    logger.info(f"[选股器] 获取股票池: {len(self._stock_pool)}只")
                    return self._stock_pool
            except Exception as e:
                logger.warning(f"[选股器] 获取A股列表失败: {e}")

        # 降级：使用内置示例数据
        return self._get_fallback_stock_pool()

    def _get_fallback_stock_pool(self) -> List[Dict[str, Any]]:
        """降级股票池（示例数据）"""
        return [
            {"code": "600519", "name": "贵州茅台", "industry": "白酒", "price": 1800, "pe": 35, "pb": 12, "market_cap": 22000e8, "roe": 30, "dividend_yield": 0.016, "turnover_rate": 0.3, "volume_ratio": 1.0, "change_pct": 1.2},
            {"code": "000858", "name": "五粮液", "industry": "白酒", "price": 150, "pe": 22, "pb": 6, "market_cap": 5800e8, "roe": 25, "dividend_yield": 0.025, "turnover_rate": 0.5, "volume_ratio": 1.2, "change_pct": 0.8},
            {"code": "000001", "name": "平安银行", "industry": "银行", "price": 12, "pe": 5, "pb": 0.6, "market_cap": 2300e8, "roe": 11, "dividend_yield": 0.05, "turnover_rate": 0.4, "volume_ratio": 0.8, "change_pct": -0.3},
            {"code": "600036", "name": "招商银行", "industry": "银行", "price": 35, "pe": 6, "pb": 1.0, "market_cap": 8800e8, "roe": 16, "dividend_yield": 0.04, "turnover_rate": 0.3, "volume_ratio": 0.9, "change_pct": 0.5},
            {"code": "000333", "name": "美的集团", "industry": "家电", "price": 65, "pe": 13, "pb": 3.5, "market_cap": 4500e8, "roe": 24, "dividend_yield": 0.035, "turnover_rate": 0.6, "volume_ratio": 1.5, "change_pct": 2.1},
            {"code": "600276", "name": "恒瑞医药", "industry": "医药", "price": 45, "pe": 55, "pb": 7, "market_cap": 2900e8, "roe": 14, "dividend_yield": 0.008, "turnover_rate": 0.8, "volume_ratio": 2.0, "change_pct": 3.5},
            {"code": "300750", "name": "宁德时代", "industry": "新能源", "price": 200, "pe": 25, "pb": 5, "market_cap": 8700e8, "roe": 18, "dividend_yield": 0.005, "turnover_rate": 1.2, "volume_ratio": 2.5, "change_pct": 4.2},
            {"code": "601318", "name": "中国平安", "industry": "保险", "price": 48, "pe": 8, "pb": 1.2, "market_cap": 8700e8, "roe": 15, "dividend_yield": 0.042, "turnover_rate": 0.3, "volume_ratio": 0.7, "change_pct": -0.5},
            {"code": "600900", "name": "长江电力", "industry": "电力", "price": 28, "pe": 20, "pb": 3.8, "market_cap": 6800e8, "roe": 16, "dividend_yield": 0.035, "turnover_rate": 0.2, "volume_ratio": 0.5, "change_pct": 0.1},
            {"code": "002475", "name": "立讯精密", "industry": "电子", "price": 35, "pe": 28, "pb": 5, "market_cap": 2500e8, "roe": 20, "dividend_yield": 0.01, "turnover_rate": 1.5, "volume_ratio": 3.0, "change_pct": 5.2},
        ]

    def _evaluate_stock(self, stock: Dict[str, Any], conditions: List[ScreenerCondition]) -> tuple:
        """
        评估单只股票是否满足条件

        Returns:
            (匹配度评分0-100, 匹配的条件列表)
        """
        matched = []
        total_conditions = len(conditions)
        if total_conditions == 0:
            return 0, []

        for condition in conditions:
            field_value = self._get_field_value(stock, condition.field)
            if field_value is None:
                continue

            if self._check_condition(field_value, condition.operator, condition.value):
                matched.append(f"{condition.field.value}{condition.operator.value}{condition.value}")

        # 匹配度 = 匹配条件数 / 总条件数 * 100
        score = int(len(matched) / total_conditions * 100) if total_conditions > 0 else 0
        return score, matched

    def _get_field_value(self, stock: Dict[str, Any], field: ScreenerConditionType) -> Optional[Any]:
        """从股票数据中获取条件字段值"""
        field_map = {
            ScreenerConditionType.PE: "pe",
            ScreenerConditionType.PB: "pb",
            ScreenerConditionType.ROE: "roe",
            ScreenerConditionType.REVENUE_GROWTH: "revenue_growth",
            ScreenerConditionType.PROFIT_GROWTH: "profit_growth",
            ScreenerConditionType.MARKET_CAP: "market_cap",
            ScreenerConditionType.TURNOVER_RATE: "turnover_rate",
            ScreenerConditionType.RSI: "rsi",
            ScreenerConditionType.VOLUME_RATIO: "volume_ratio",
            ScreenerConditionType.DIVIDEND_YIELD: "dividend_yield",
            ScreenerConditionType.MA_TREND: "ma_trend",
        }
        key = field_map.get(field)
        if key and key in stock:
            return stock[key]
        return None

    @staticmethod
    def _check_condition(value: Any, operator: ScreenerOperator, target: Any) -> bool:
        """检查条件是否满足"""
        try:
            if operator == ScreenerOperator.GT:
                return float(value) > float(target)
            elif operator == ScreenerOperator.GTE:
                return float(value) >= float(target)
            elif operator == ScreenerOperator.LT:
                return float(value) < float(target)
            elif operator == ScreenerOperator.LTE:
                return float(value) <= float(target)
            elif operator == ScreenerOperator.EQ:
                return str(value) == str(target)
            elif operator == ScreenerOperator.BETWEEN:
                if isinstance(target, (list, tuple)) and len(target) == 2:
                    return float(target[0]) <= float(value) <= float(target[1])
        except (ValueError, TypeError):
            pass
        return False

    @staticmethod
    def _extract_key_metrics(stock: Dict[str, Any]) -> Dict[str, Any]:
        """提取关键指标"""
        keys = ["price", "pe", "pb", "market_cap", "roe", "dividend_yield", "turnover_rate", "change_pct"]
        return {k: stock.get(k) for k in keys if stock.get(k) is not None}

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
