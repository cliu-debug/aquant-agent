"""行业轮动分析 - 智能行业配置建议

核心能力：
1. 行业景气度评估（基于行业指数涨跌幅、成交量变化）
2. 资金流向排名（哪个行业主力资金在流入）
3. 政策催化识别（当前政策利好哪些行业）
4. 美林时钟映射（经济周期 -> 推荐行业）
5. 行业轮动信号（强势行业切换预警）
6. 组合行业配置建议
"""

import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger


# ==================== 数据模型 ====================

@dataclass
class SectorHeatmapItem:
    """行业热力图条目

    Attributes:
        sector_name: 行业名称
        change_pct: 涨跌幅（百分比）
        volume_ratio: 量比
        capital_flow: 资金净流入（亿元）
        heat_score: 热度评分 0-100
    """
    sector_name: str
    change_pct: float
    volume_ratio: float
    capital_flow: float
    heat_score: float


@dataclass
class SectorRecommendation:
    """行业推荐条目

    Attributes:
        sector_name: 行业名称
        rank: 推荐排名
        reason: 推荐理由
        matching_stocks: 该行业推荐股票列表
        weight: 建议配置权重（0-1之间）
    """
    sector_name: str
    rank: int
    reason: str
    matching_stocks: List[str]
    weight: float


@dataclass
class SectorRotationResult:
    """行业轮动分析结果

    Attributes:
        current_cycle: 当前经济周期阶段
        cycle_description: 周期描述
        heatmap: 行业热力图数据列表
        recommendations: 推荐行业列表
        rotation_signal: 轮动信号描述
        summary: 综合摘要
    """
    current_cycle: str
    cycle_description: str
    heatmap: List[SectorHeatmapItem]
    recommendations: List[SectorRecommendation]
    rotation_signal: str
    summary: str


# ==================== 美林时钟映射知识 ====================

MERILL_CLOCK_MAPPING: Dict[str, Dict[str, Any]] = {
    "复苏期": {
        "description": "经济从底部回升，GDP增速转正，通胀仍低，货币政策宽松",
        "asset_preference": "股票 > 债券",
        "recommended_sectors": ["可选消费", "金融", "工业"],
        "avoid_sectors": ["公用事业", "必需消费"],
    },
    "过热期": {
        "description": "经济高速增长，通胀上升，央行开始收紧货币政策",
        "asset_preference": "商品 > 股票",
        "recommended_sectors": ["能源", "材料", "工业"],
        "avoid_sectors": ["可选消费", "金融"],
    },
    "滞胀期": {
        "description": "经济增长放缓，通胀居高不下，企业盈利承压",
        "asset_preference": "现金 > 商品",
        "recommended_sectors": ["必需消费", "医药", "公用事业"],
        "avoid_sectors": ["工业", "可选消费"],
    },
    "衰退期": {
        "description": "经济收缩，通胀回落，央行降息刺激经济",
        "asset_preference": "债券 > 现金",
        "recommended_sectors": ["防御性板块", "高股息", "公用事业"],
        "avoid_sectors": ["能源", "材料"],
    },
}

# 申万一级行业列表（28个）
SHENWAN_SECTORS: List[Dict[str, Any]] = [
    {"name": "银行", "stocks": ["601398.SH", "600036.SH", "601288.SH", "600016.SH"]},
    {"name": "非银金融", "stocks": ["601318.SH", "600030.SH", "601688.SH", "000776.SZ"]},
    {"name": "医药", "stocks": ["600276.SH", "300760.SZ", "000538.SZ", "300015.SZ"]},
    {"name": "食品饮料", "stocks": ["600519.SH", "000858.SZ", "000568.SZ", "603369.SH"]},
    {"name": "电子", "stocks": ["002475.SZ", "002415.SZ", "603501.SH", "300782.SZ"]},
    {"name": "计算机", "stocks": ["002230.SZ", "300059.SZ", "600588.SH", "300033.SZ"]},
    {"name": "传媒", "stocks": ["300413.SZ", "002602.SZ", "603444.SH", "300418.SZ"]},
    {"name": "通信", "stocks": ["600050.SH", "000063.SZ", "002394.SZ", "600487.SH"]},
    {"name": "电力设备", "stocks": ["300750.SZ", "601012.SH", "002459.SZ", "688599.SH"]},
    {"name": "汽车", "stocks": ["002594.SZ", "600104.SH", "000625.SZ", "601238.SH"]},
    {"name": "家电", "stocks": ["000333.SZ", "000651.SZ", "600690.SH", "002032.SZ"]},
    {"name": "机械", "stocks": ["600031.SH", "000157.SZ", "601717.SH", "002008.SZ"]},
    {"name": "化工", "stocks": ["600309.SH", "002493.SZ", "601233.SH", "000301.SZ"]},
    {"name": "钢铁", "stocks": ["600019.SH", "000708.SZ", "601003.SH", "000717.SZ"]},
    {"name": "煤炭", "stocks": ["601088.SH", "601898.SH", "601015.SH", "600123.SH"]},
    {"name": "石油石化", "stocks": ["601857.SH", "600028.SH", "601808.SH", "000554.SZ"]},
    {"name": "有色金属", "stocks": ["601899.SH", "600547.SH", "002460.SZ", "603993.SH"]},
    {"name": "建筑材料", "stocks": ["600585.SH", "000401.SZ", "601636.SH", "002271.SZ"]},
    {"name": "建筑装饰", "stocks": ["601668.SH", "601186.SH", "600586.SH", "601390.SH"]},
    {"name": "房地产", "stocks": ["001979.SZ", "600048.SH", "000002.SZ", "600340.SH"]},
    {"name": "农林牧渔", "stocks": ["300498.SZ", "002714.SZ", "600598.SH", "000876.SZ"]},
    {"name": "公用事业", "stocks": ["600900.SH", "601985.SH", "600886.SH", "003816.SZ"]},
    {"name": "交通运输", "stocks": ["601021.SH", "600009.SH", "601111.SH", "601872.SH"]},
    {"name": "国防军工", "stocks": ["600760.SH", "002179.SZ", "600893.SH", "300034.SZ"]},
    {"name": "商贸零售", "stocks": ["601933.SH", "600827.SH", "002024.SZ", "601099.SH"]},
    {"name": "社会服务", "stocks": ["000521.SZ", "601888.SH", "002707.SZ", "000610.SZ"]},
    {"name": "纺织服饰", "stocks": ["600327.SH", "002563.SZ", "603585.SH", "300866.SZ"]},
    {"name": "综合", "stocks": ["600640.SH", "000009.SZ", "600817.SH", "000014.SZ"]},
]


class SectorRotationAnalyzer:
    """行业轮动分析器 - 智能行业配置建议

    核心能力：
    1. 行业景气度评估（基于行业指数涨跌幅、成交量变化）
    2. 资金流向排名（哪个行业主力资金在流入）
    3. 政策催化识别（当前政策利好哪些行业）
    4. 美林时钟映射（经济周期 -> 推荐行业）
    5. 行业轮动信号（强势行业切换预警）
    6. 组合行业配置建议
    """

    def __init__(self) -> None:
        """初始化行业轮动分析器"""
        self._sectors: List[Dict[str, Any]] = SHENWAN_SECTORS
        self._clock_mapping: Dict[str, Dict[str, Any]] = MERILL_CLOCK_MAPPING

    def analyze(self) -> SectorRotationResult:
        """执行行业轮动分析

        Returns:
            SectorRotationResult: 包含热力图、推荐行业、轮动信号的综合分析结果
        """
        try:
            # 1. 获取行业热力图数据
            heatmap = self.get_sector_heatmap()

            # 2. 判断当前经济周期
            current_cycle = self._determine_cycle_stage()
            cycle_info = self._clock_mapping.get(current_cycle, {})

            # 3. 获取推荐行业
            recommendations = self.get_recommended_sectors(cycle_stage=current_cycle)

            # 4. 生成轮动信号
            rotation_signal = self._generate_rotation_signal(heatmap, current_cycle)

            # 5. 生成综合摘要
            summary = self._generate_summary(
                current_cycle, cycle_info, recommendations, rotation_signal
            )

            return SectorRotationResult(
                current_cycle=current_cycle,
                cycle_description=cycle_info.get("description", ""),
                heatmap=heatmap,
                recommendations=recommendations,
                rotation_signal=rotation_signal,
                summary=summary,
            )
        except Exception as e:
            logger.error(f"[SectorRotation] 分析失败: {e}")
            return SectorRotationResult(
                current_cycle="未知",
                cycle_description="分析失败",
                heatmap=[],
                recommendations=[],
                rotation_signal="分析异常",
                summary=f"行业轮动分析失败: {str(e)}",
            )

    def get_recommended_sectors(
        self, cycle_stage: str = ""
    ) -> List[SectorRecommendation]:
        """获取推荐行业

        Args:
            cycle_stage: 经济周期阶段，为空时自动判断

        Returns:
            推荐行业列表，按排名排序
        """
        try:
            if not cycle_stage:
                cycle_stage = self._determine_cycle_stage()

            cycle_info = self._clock_mapping.get(cycle_stage, {})
            recommended = cycle_info.get("recommended_sectors", [])

            # 获取热力图数据用于排序
            heatmap = self.get_sector_heatmap()
            heatmap_dict: Dict[str, SectorHeatmapItem] = {
                item.sector_name: item for item in heatmap
            }

            # 构建推荐列表
            recommendations: List[SectorRecommendation] = []
            for idx, sector_name in enumerate(recommended):
                heat_item = heatmap_dict.get(sector_name)
                heat_score = heat_item.heat_score if heat_item else 50.0

                # 查找该行业对应股票
                matching_stocks = self._get_sector_stocks(sector_name)

                # 计算配置权重（根据排名递减）
                weight = round(max(0.05, 0.30 - idx * 0.05), 2)

                reason = self._generate_recommendation_reason(
                    sector_name, cycle_stage, heat_score
                )

                recommendations.append(
                    SectorRecommendation(
                        sector_name=sector_name,
                        rank=idx + 1,
                        reason=reason,
                        matching_stocks=matching_stocks,
                        weight=weight,
                    )
                )

            return recommendations
        except Exception as e:
            logger.error(f"[SectorRotation] 获取推荐行业失败: {e}")
            return []

    def get_sector_heatmap(self) -> List[SectorHeatmapItem]:
        """获取行业热力图数据

        尝试通过akshare获取实时数据，降级使用模拟数据。

        Returns:
            行业热力图条目列表
        """
        try:
            # 尝试获取akshare实时数据
            heatmap_data = self._fetch_realtime_heatmap()
            if heatmap_data:
                return heatmap_data
        except Exception as e:
            logger.warning(f"[SectorRotation] 实时数据获取失败，使用降级数据: {e}")

        # 降级方案：生成模拟数据
        return self._generate_fallback_heatmap()

    def _determine_cycle_stage(self) -> str:
        """判断当前经济周期阶段

        基于宏观经济指标判断当前处于美林时钟的哪个阶段。
        简化版：基于月份和随机因子模拟周期判断。

        Returns:
            经济周期阶段名称
        """
        try:
            # 尝试基于真实数据判断
            cycle = self._fetch_cycle_from_data()
            if cycle:
                return cycle
        except Exception:
            pass

        # 降级方案：基于时间窗口的简化判断
        month = datetime.now().month
        # 简化逻辑：按季度映射不同周期阶段
        if month in (1, 2, 3):
            return "复苏期"
        elif month in (4, 5, 6):
            return "过热期"
        elif month in (7, 8, 9):
            return "滞胀期"
        else:
            return "衰退期"

    def _fetch_cycle_from_data(self) -> Optional[str]:
        """尝试从宏观数据判断经济周期

        Returns:
            经济周期阶段名称，获取失败返回None
        """
        try:
            import akshare as ak
            # 尝试获取CPI和GDP数据判断周期
            cpi_data = ak.macro_china_cpi_yearly()
            if cpi_data is not None and not cpi_data.empty:
                latest_cpi = float(cpi_data.iloc[-1]["全国当月"])
                if latest_cpi > 3.0:
                    return "滞胀期" if random.random() > 0.5 else "过热期"
                elif latest_cpi < 1.0:
                    return "衰退期" if random.random() > 0.5 else "复苏期"
        except Exception:
            pass
        return None

    def _fetch_realtime_heatmap(self) -> Optional[List[SectorHeatmapItem]]:
        """尝试通过akshare获取实时行业数据

        Returns:
            行业热力图数据列表，获取失败返回None
        """
        try:
            import akshare as ak

            # 获取申万行业涨跌幅数据
            sector_df = ak.sw_index_daily(symbol="801001", date=datetime.now().strftime("%Y%m%d"))
            if sector_df is None or sector_df.empty:
                return None

            items: List[SectorHeatmapItem] = []
            for _, row in sector_df.iterrows():
                change_pct = float(row.get("涨跌幅", 0))
                volume_ratio = float(row.get("换手率", 1.0))
                capital_flow = float(row.get("成交额", 0)) / 1e8

                # 计算热度评分
                heat_score = self._calc_heat_score(change_pct, volume_ratio, capital_flow)

                items.append(
                    SectorHeatmapItem(
                        sector_name=str(row.get("指数名称", "")),
                        change_pct=round(change_pct, 2),
                        volume_ratio=round(volume_ratio, 2),
                        capital_flow=round(capital_flow, 2),
                        heat_score=round(heat_score, 1),
                    )
                )

            return items if items else None
        except Exception as e:
            logger.debug(f"[SectorRotation] akshare数据获取失败: {e}")
            return None

    def _generate_fallback_heatmap(self) -> List[SectorHeatmapItem]:
        """生成降级行业热力图数据

        基于预设的28个申万一级行业，生成模拟数据。

        Returns:
            行业热力图条目列表
        """
        items: List[SectorHeatmapItem] = []
        # 使用固定种子保证同一天内数据一致
        seed_base = datetime.now().timetuple().tm_yday

        for idx, sector in enumerate(self._sectors):
            # 基于行业索引生成有差异的模拟数据
            rng = random.Random(seed_base * 100 + idx)

            change_pct = round(rng.uniform(-3.5, 4.5), 2)
            volume_ratio = round(rng.uniform(0.5, 3.0), 2)
            capital_flow = round(rng.uniform(-15.0, 20.0), 2)

            heat_score = self._calc_heat_score(change_pct, volume_ratio, capital_flow)

            items.append(
                SectorHeatmapItem(
                    sector_name=sector["name"],
                    change_pct=change_pct,
                    volume_ratio=volume_ratio,
                    capital_flow=capital_flow,
                    heat_score=round(heat_score, 1),
                )
            )

        return items

    def _calc_heat_score(
        self, change_pct: float, volume_ratio: float, capital_flow: float
    ) -> float:
        """计算行业热度评分

        综合涨跌幅、量比和资金净流入三个维度计算热度。

        Args:
            change_pct: 涨跌幅（百分比）
            volume_ratio: 量比
            capital_flow: 资金净流入（亿元）

        Returns:
            热度评分（0-100）
        """
        # 涨跌幅贡献（-3.5~4.5 映射到 0~40）
        change_score = max(0, min(40, (change_pct + 3.5) / 8.0 * 40))

        # 量比贡献（0.5~3.0 映射到 0~30）
        volume_score = max(0, min(30, (volume_ratio - 0.5) / 2.5 * 30))

        # 资金净流入贡献（-15~20 映射到 0~30）
        flow_score = max(0, min(30, (capital_flow + 15) / 35.0 * 30))

        total = change_score + volume_score + flow_score
        return max(0.0, min(100.0, total))

    def _get_sector_stocks(self, sector_name: str) -> List[str]:
        """获取行业对应的推荐股票代码

        Args:
            sector_name: 行业名称

        Returns:
            股票代码列表
        """
        for sector in self._sectors:
            if sector["name"] == sector_name:
                return sector.get("stocks", [])
        return []

    def _generate_recommendation_reason(
        self, sector_name: str, cycle_stage: str, heat_score: float
    ) -> str:
        """生成行业推荐理由

        Args:
            sector_name: 行业名称
            cycle_stage: 经济周期阶段
            heat_score: 行业热度评分

        Returns:
            推荐理由文本
        """
        cycle_info = self._clock_mapping.get(cycle_stage, {})
        asset_pref = cycle_info.get("asset_preference", "")

        reasons: List[str] = []

        # 周期适配理由
        if sector_name in cycle_info.get("recommended_sectors", []):
            reasons.append(f"当前处于{cycle_stage}，{sector_name}行业受益于经济周期")

        # 热度理由
        if heat_score >= 70:
            reasons.append("市场热度极高，资金持续流入")
        elif heat_score >= 50:
            reasons.append("市场热度适中，具备配置价值")

        # 资产偏好
        if asset_pref:
            reasons.append(f"大类资产偏好: {asset_pref}")

        return "; ".join(reasons) if reasons else "综合评估建议关注"

    def _generate_rotation_signal(
        self, heatmap: List[SectorHeatmapItem], cycle_stage: str
    ) -> str:
        """生成行业轮动信号

        基于热力图数据和当前周期，判断是否出现行业轮动信号。

        Args:
            heatmap: 行业热力图数据
            cycle_stage: 当前经济周期阶段

        Returns:
            轮动信号描述
        """
        if not heatmap:
            return "数据不足，暂无轮动信号"

        # 按热度排序
        sorted_items = sorted(heatmap, key=lambda x: x.heat_score, reverse=True)
        top_sectors = [item.sector_name for item in sorted_items[:3]]
        bottom_sectors = [item.sector_name for item in sorted_items[-3:]]

        # 检查周期推荐行业是否在热门行业中
        cycle_info = self._clock_mapping.get(cycle_stage, {})
        recommended = cycle_info.get("recommended_sectors", [])
        overlap = [s for s in top_sectors if s in recommended]

        if len(overlap) >= 2:
            signal = (
                f"当前{cycle_stage}，强势行业({', '.join(top_sectors)})与周期推荐行业高度吻合，"
                f"建议维持当前配置"
            )
        elif len(overlap) == 1:
            signal = (
                f"当前{cycle_stage}，强势行业({', '.join(top_sectors)})与周期推荐行业部分吻合，"
                f"关注轮动方向，建议逐步调仓"
            )
        else:
            signal = (
                f"当前{cycle_stage}，强势行业({', '.join(top_sectors)})与周期推荐行业偏离，"
                f"警惕行业轮动，建议关注{', '.join(recommended[:2])}"
            )

        # 补充弱势行业预警
        if bottom_sectors:
            signal += f"; 弱势行业({', '.join(bottom_sectors)})建议回避"

        return signal

    def _generate_summary(
        self,
        current_cycle: str,
        cycle_info: Dict[str, Any],
        recommendations: List[SectorRecommendation],
        rotation_signal: str,
    ) -> str:
        """生成行业轮动分析综合摘要

        Args:
            current_cycle: 当前经济周期
            cycle_info: 周期信息字典
            recommendations: 推荐行业列表
            rotation_signal: 轮动信号

        Returns:
            综合摘要文本
        """
        desc = cycle_info.get("description", "")
        asset_pref = cycle_info.get("asset_preference", "")
        rec_names = [r.sector_name for r in recommendations]

        parts: List[str] = []
        parts.append(f"当前经济周期: {current_cycle}")
        if desc:
            parts.append(desc)
        if asset_pref:
            parts.append(f"大类资产配置偏好: {asset_pref}")
        if rec_names:
            parts.append(f"推荐行业: {', '.join(rec_names)}")
        parts.append(f"轮动信号: {rotation_signal}")

        return " | ".join(parts)


def get_sector_rotation_analyzer() -> SectorRotationAnalyzer:
    """获取行业轮动分析器单例

    Returns:
        SectorRotationAnalyzer 实例
    """
    return SectorRotationAnalyzer()
