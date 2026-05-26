<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { HeatmapChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, VisualMapComponent, TitleComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([HeatmapChart, GridComponent, TooltipComponent, VisualMapComponent, TitleComponent, CanvasRenderer])
import {
  getSectorRotation,
  getMarketSentiment,
  type SectorRotationResult,
  type SectorHeatmapItem,
} from '@/services/api'

/** 行业热力图条目 */
const heatmapData = ref<SectorHeatmapItem[]>([])
/** 行业轮动分析结果 */
const rotationResult = ref<SectorRotationResult | null>(null)
/** 情绪数据（来自 getMarketSentiment API） */
const sentimentData = ref<Record<string, unknown> | null>(null)
/** 加载状态 */
const loading = ref(false)
/** 错误信息 */
const error = ref<string | null>(null)
/** ECharts 实例 */
let chartInstance: echarts.ECharts | null = null
/** 热力图容器 ref */
const heatmapChartRef = ref<HTMLDivElement | null>(null)

/** 恐贪指数（优先使用情绪API数据，回退到行业热度计算） */
const fearGreedIndex = computed((): number => {
  // 优先使用情绪 API 返回的恐贪指数
  if (sentimentData.value) {
    const val = sentimentData.value.fear_greed_index
      ?? sentimentData.value.fear_greed
      ?? sentimentData.value.index
      ?? sentimentData.value.score
    if (val != null) {
      const num = Number(val)
      if (!isNaN(num)) return Math.round(Math.max(0, Math.min(100, num)))
    }
  }
  // 回退：基于行业热度综合计算
  if (!heatmapData.value.length) return 50
  const avgHeat = heatmapData.value.reduce((sum, item) => sum + item.heat_score, 0) / heatmapData.value.length
  return Math.round(Math.max(0, Math.min(100, avgHeat)))
})

/** 恐贪指数颜色 */
const fearGreedColor = computed((): string => {
  const idx = fearGreedIndex.value
  if (idx >= 75) return '#00B96B'
  if (idx >= 55) return '#8BC34A'
  if (idx >= 45) return '#FAAD14'
  if (idx >= 25) return '#FF9800'
  return '#F5222D'
})

/** 市场情绪状态文字 */
const sentimentLabel = computed((): string => {
  const idx = fearGreedIndex.value
  if (idx >= 80) return '极度贪婪'
  if (idx >= 60) return '贪婪'
  if (idx >= 40) return '中性'
  if (idx >= 20) return '恐惧'
  return '极度恐惧'
})

/** 情绪描述（来自情绪 API） */
const sentimentDescription = computed((): string => {
  if (!sentimentData.value) return ''
  return String(
    sentimentData.value.description
    ?? sentimentData.value.summary
    ?? sentimentData.value.analysis
    ?? ''
  )
})

/** 情绪分项指标（来自情绪 API） */
const sentimentMetrics = computed((): Array<{ label: string; value: number; key: string }> => {
  if (!sentimentData.value) return []
  const items: Array<{ label: string; value: number; key: string }> = []
  const data = sentimentData.value

  const metricMap: Record<string, string> = {
    market_breadth: '市场宽度',
    volatility: '波动率',
    momentum: '动量',
    volume: '成交量',
    safe_haven_demand: '避险需求',
    junk_bond_demand: '垃圾债需求',
    put_call_ratio: '认沽认购比',
    market_momentum: '市场动量',
    stock_strength: '股票强度',
  }

  for (const [key, label] of Object.entries(metricMap)) {
    const val = data[key]
    if (val != null) {
      const num = Number(val)
      if (!isNaN(num)) {
        items.push({ label, value: Math.max(0, Math.min(100, num)), key })
      }
    }
  }

  return items
})

/** 涨跌行业统计 */
const sectorStats = computed((): { up: number; down: number; flat: number } => {
  let up = 0
  let down = 0
  let flat = 0
  for (const item of heatmapData.value) {
    if (item.change_pct > 0.1) up++
    else if (item.change_pct < -0.1) down++
    else flat++
  }
  return { up, down, flat }
})

onMounted(async () => {
  await loadData()
  await nextTick()
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})

/** 加载行业轮动数据与市场情绪数据 */
async function loadData(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    // 并行请求行业轮动和情绪数据
    const [rotationRes, sentimentRes] = await Promise.allSettled([
      getSectorRotation(),
      getMarketSentiment(),
    ])

    // 处理行业轮动结果
    if (rotationRes.status === 'fulfilled') {
      rotationResult.value = rotationRes.value.data
      heatmapData.value = rotationRes.value.data.heatmap || []
    } else {
      error.value = rotationRes.reason instanceof Error ? rotationRes.reason.message : '行业数据加载失败'
    }

    // 处理情绪数据结果
    if (sentimentRes.status === 'fulfilled') {
      sentimentData.value = sentimentRes.value?.data ?? sentimentRes.value ?? null
    }
    // 情绪数据加载失败不阻塞页面

    await nextTick()
    updateChart()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '数据加载失败'
  } finally {
    loading.value = false
  }
}

/** 初始化 ECharts 热力图 */
function initChart(): void {
  if (!heatmapChartRef.value) return
  chartInstance = echarts.init(heatmapChartRef.value, 'dark')
  updateChart()
}

/** 更新热力图数据 */
function updateChart(): void {
  if (!chartInstance || !heatmapData.value.length) return

  // 按热度排序
  const sorted = [...heatmapData.value].sort((a, b) => b.heat_score - a.heat_score)

  // 构建网格布局（7列4行）
  const cols = 7
  const data: Array<[number, number, number, string]> = []
  sorted.forEach((item, idx) => {
    const row = Math.floor(idx / cols)
    const col = idx % cols
    data.push([col, row, item.heat_score, item.sector_name])
  })

  const maxRow = Math.ceil(sorted.length / cols)

  const option: echarts.EChartsCoreOption = {
    backgroundColor: 'transparent',
    tooltip: {
      formatter: (params: unknown) => {
        const p = params as { data: [number, number, number, string] }
        const d = p.data
        const item = sorted.find(s => s.sector_name === d[3])
        if (!item) return ''
        return `<div style="font-size:13px;">
          <b>${item.sector_name}</b><br/>
          涨跌幅: <span style="color:${item.change_pct >= 0 ? '#00B96B' : '#F5222D'}">${item.change_pct > 0 ? '+' : ''}${item.change_pct.toFixed(2)}%</span><br/>
          量比: ${item.volume_ratio.toFixed(2)}<br/>
          资金净流入: ${item.capital_flow > 0 ? '+' : ''}${item.capital_flow.toFixed(2)}亿<br/>
          热度: ${item.heat_score.toFixed(1)}
        </div>`
      },
    },
    grid: {
      top: 10,
      bottom: 30,
      left: 10,
      right: 10,
      containLabel: false,
    },
    xAxis: {
      type: 'category',
      data: Array.from({ length: cols }, (_, i) => i),
      show: false,
      splitArea: { show: false },
    },
    yAxis: {
      type: 'category',
      data: Array.from({ length: maxRow }, (_, i) => i),
      show: false,
      splitArea: { show: false },
    },
    visualMap: {
      min: 0,
      max: 100,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      itemWidth: 12,
      itemHeight: 100,
      textStyle: { color: '#7B8499', fontSize: 11 },
      inRange: {
        color: ['#3B1518', '#7B2020', '#B85C2C', '#D4A017', '#6B8E23', '#2E8B57', '#00B96B'],
      },
      text: ['高', '低'],
    },
    series: [
      {
        type: 'heatmap',
        data: data,
        label: {
          show: true,
          formatter: (params: unknown) => {
            const p = params as { data: [number, number, number, string] }
            return p.data[3]
          },
          fontSize: 11,
          color: '#E8ECF4',
        },
        itemStyle: {
          borderWidth: 2,
          borderColor: '#141827',
          borderRadius: 4,
        },
        emphasis: {
          itemStyle: {
            borderColor: '#2563EB',
            borderWidth: 2,
          },
        },
      },
    ],
  }

  chartInstance.setOption(option)
}

/** 窗口resize处理 */
function handleResize(): void {
  chartInstance?.resize()
}

/** 涨跌幅颜色类 */
function changeClass(pct: number): string {
  if (pct > 0) return 'value-positive'
  if (pct < 0) return 'value-negative'
  return ''
}

/** 格式化涨跌幅 */
function formatChange(pct: number): string {
  const sign = pct > 0 ? '+' : ''
  return `${sign}${pct.toFixed(2)}%`
}

/** 情绪分项指标颜色 */
function metricColor(value: number): string {
  if (value >= 70) return '#00B96B'
  if (value >= 50) return '#8BC34A'
  if (value >= 30) return '#FAAD14'
  return '#F5222D'
}
</script>

<template>
  <div class="market-view">
    <h2 class="page-title">市场总览</h2>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <!-- 顶部指标区 -->
    <div class="top-metrics">
      <!-- 恐贪指数仪表盘 -->
      <div class="metric-card gauge-card">
        <div class="metric-label">恐贪指数</div>
        <div class="gauge-container">
          <svg class="gauge-svg" viewBox="0 0 200 120">
            <!-- 背景弧 -->
            <path
              d="M 20 100 A 80 80 0 0 1 180 100"
              fill="none"
              stroke="#1E2438"
              stroke-width="12"
              stroke-linecap="round"
            />
            <!-- 值弧 -->
            <path
              d="M 20 100 A 80 80 0 0 1 180 100"
              fill="none"
              :stroke="fearGreedColor"
              stroke-width="12"
              stroke-linecap="round"
              :stroke-dasharray="`${(fearGreedIndex / 100) * 251.2} 251.2`"
            />
            <!-- 指针 -->
            <circle
              :cx="20 + (fearGreedIndex / 100) * 160"
              cy="100"
              r="6"
              :fill="fearGreedColor"
            />
          </svg>
          <div class="gauge-value" :style="{ color: fearGreedColor }">{{ fearGreedIndex }}</div>
        </div>
        <div class="gauge-label" :style="{ color: fearGreedColor }">{{ sentimentLabel }}</div>
      </div>

      <!-- 情绪温度计 -->
      <div class="metric-card thermometer-card">
        <div class="metric-label">情绪温度计</div>
        <div class="thermometer">
          <div class="thermo-scale">
            <span class="thermo-tick" style="bottom: 0%">0</span>
            <span class="thermo-tick" style="bottom: 25%">25</span>
            <span class="thermo-tick" style="bottom: 50%">50</span>
            <span class="thermo-tick" style="bottom: 75%">75</span>
            <span class="thermo-tick" style="bottom: 100%">100</span>
          </div>
          <div class="thermo-bar-bg">
            <div
              class="thermo-bar-fill"
              :style="{
                height: `${fearGreedIndex}%`,
                background: `linear-gradient(to top, #F5222D, #FF9800, #FAAD14, #8BC34A, #00B96B)`
              }"
            ></div>
          </div>
          <div class="thermo-labels">
            <span class="thermo-label-item" style="bottom: 10%">极度恐惧</span>
            <span class="thermo-label-item" style="bottom: 35%">恐惧</span>
            <span class="thermo-label-item" style="bottom: 55%">中性</span>
            <span class="thermo-label-item" style="bottom: 75%">贪婪</span>
            <span class="thermo-label-item" style="bottom: 92%">极度贪婪</span>
          </div>
        </div>
      </div>

      <!-- 涨跌统计 -->
      <div class="metric-card">
        <div class="metric-label">行业涨跌</div>
        <div class="stats-row">
          <div class="stat-item">
            <span class="stat-value value-positive">{{ sectorStats.up }}</span>
            <span class="stat-desc">上涨</span>
          </div>
          <div class="stat-item">
            <span class="stat-value" style="color: var(--color-text-muted)">{{ sectorStats.flat }}</span>
            <span class="stat-desc">平盘</span>
          </div>
          <div class="stat-item">
            <span class="stat-value value-negative">{{ sectorStats.down }}</span>
            <span class="stat-desc">下跌</span>
          </div>
        </div>
      </div>

      <!-- 经济周期 -->
      <div class="metric-card" v-if="rotationResult">
        <div class="metric-label">经济周期</div>
        <div class="metric-value cycle-value">{{ rotationResult.current_cycle }}</div>
        <div class="metric-sub">{{ rotationResult.cycle_description }}</div>
      </div>
    </div>

    <!-- 情绪分项指标 -->
    <div v-if="sentimentMetrics.length" class="section-card">
      <h3 class="section-title">分项指标</h3>
      <div class="metrics-list">
        <div
          v-for="metric in sentimentMetrics"
          :key="metric.key"
          class="metric-row"
        >
          <div class="metric-name">{{ metric.label }}</div>
          <div class="metric-bar-wrapper">
            <div class="metric-bar-bg">
              <div
                class="metric-bar-fill"
                :style="{
                  width: `${metric.value}%`,
                  background: metricColor(metric.value)
                }"
              ></div>
            </div>
          </div>
          <div class="metric-score" :style="{ color: metricColor(metric.value) }">
            {{ metric.value }}
          </div>
        </div>
      </div>
    </div>

    <!-- 情绪分析文本 -->
    <div v-if="sentimentDescription" class="section-card">
      <h3 class="section-title">情绪分析</h3>
      <div class="analysis-text">{{ sentimentDescription }}</div>
    </div>

    <!-- 行业热力图 -->
    <div class="section-card">
      <h3 class="section-title">行业热力图</h3>
      <div ref="heatmapChartRef" class="heatmap-chart"></div>
    </div>

    <!-- 行业轮动建议 -->
    <div class="section-card" v-if="rotationResult">
      <h3 class="section-title">行业轮动建议</h3>

      <!-- 轮动信号 -->
      <div class="rotation-signal-bar">
        <span class="signal-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
          </svg>
        </span>
        <span class="signal-text">{{ rotationResult.rotation_signal }}</span>
      </div>

      <!-- 推荐行业列表 -->
      <div v-if="rotationResult.recommendations.length" class="rec-grid">
        <div
          v-for="rec in rotationResult.recommendations"
          :key="rec.sector_name"
          class="rec-card"
        >
          <div class="rec-card-header">
            <span class="rec-rank-badge">TOP {{ rec.rank }}</span>
            <span class="rec-sector-name">{{ rec.sector_name }}</span>
            <span class="rec-weight-badge">{{ (rec.weight * 100).toFixed(0) }}%</span>
          </div>
          <div class="rec-card-body">
            <p class="rec-reason-text">{{ rec.reason }}</p>
            <div class="rec-stock-list" v-if="rec.matching_stocks.length">
              <span class="rec-stock-tag" v-for="code in rec.matching_stocks" :key="code">{{ code }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">暂无推荐行业</div>
    </div>

    <!-- 行业详情表格 -->
    <div class="section-card">
      <h3 class="section-title">行业详情</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>行业</th>
              <th>涨跌幅</th>
              <th>量比</th>
              <th>资金净流入(亿)</th>
              <th>热度</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in heatmapData" :key="item.sector_name">
              <td>{{ item.sector_name }}</td>
              <td :class="changeClass(item.change_pct)">{{ formatChange(item.change_pct) }}</td>
              <td>{{ item.volume_ratio.toFixed(2) }}</td>
              <td :class="changeClass(item.capital_flow)">{{ item.capital_flow > 0 ? '+' : '' }}{{ item.capital_flow.toFixed(2) }}</td>
              <td>
                <div class="heat-bar">
                  <div class="heat-fill" :style="{ width: `${item.heat_score}%`, background: item.heat_score > 60 ? '#00B96B' : item.heat_score > 40 ? '#FAAD14' : '#F5222D' }"></div>
                  <span class="heat-value">{{ item.heat_score.toFixed(0) }}</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="loading" class="loading-state">数据加载中...</div>
  </div>
</template>

<style scoped>
.market-view {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100vh;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.top-metrics {
  display: grid;
  grid-template-columns: 200px 160px repeat(2, 1fr);
  gap: 12px;
}

.metric-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
}

.metric-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.metric-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.metric-sub {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 4px;
}

/* 恐贪指数仪表盘 */
.gauge-card {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.gauge-container {
  position: relative;
  width: 160px;
  height: 90px;
}

.gauge-svg {
  width: 100%;
  height: 100%;
}

.gauge-value {
  position: absolute;
  bottom: 4px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 28px;
  font-weight: 800;
}

.gauge-label {
  font-size: 14px;
  font-weight: 600;
  text-align: center;
  margin-top: 4px;
}

/* 情绪温度计 */
.thermometer-card {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.thermometer {
  display: flex;
  gap: 8px;
  position: relative;
  height: 120px;
}

.thermo-scale {
  position: relative;
  height: 100%;
  width: 20px;
}

.thermo-tick {
  position: absolute;
  right: 0;
  font-size: 10px;
  color: var(--color-text-muted);
  transform: translateY(50%);
}

.thermo-bar-bg {
  width: 20px;
  height: 100%;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  overflow: hidden;
  position: relative;
}

.thermo-bar-fill {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  border-radius: 10px;
  transition: height 0.6s ease;
}

.thermo-labels {
  position: relative;
  height: 100%;
  width: 60px;
}

.thermo-label-item {
  position: absolute;
  left: 0;
  font-size: 10px;
  color: var(--color-text-muted);
  transform: translateY(50%);
  white-space: nowrap;
}

/* 涨跌统计 */
.stats-row {
  display: flex;
  gap: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
}

.stat-desc {
  font-size: 11px;
  color: var(--color-text-muted);
}

.cycle-value {
  color: var(--color-accent);
}

/* 区块卡片 */
.section-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 12px;
}

/* 分项指标 */
.metrics-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.metric-row {
  display: grid;
  grid-template-columns: 100px 1fr 40px;
  gap: 12px;
  align-items: center;
}

.metric-name {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.metric-bar-wrapper {
  flex: 1;
}

.metric-bar-bg {
  width: 100%;
  height: 8px;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  overflow: hidden;
}

.metric-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

.metric-score {
  font-size: 14px;
  font-weight: 700;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* 分析文本 */
.analysis-text {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
}

/* 热力图 */
.heatmap-chart {
  width: 100%;
  height: 320px;
}

/* 轮动信号 */
.rotation-signal-bar {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(37, 99, 235, 0.06);
  border: 1px solid rgba(37, 99, 235, 0.15);
  border-radius: var(--radius);
  margin-bottom: 12px;
}

.signal-icon {
  color: var(--color-accent);
  flex-shrink: 0;
  margin-top: 1px;
}

.signal-text {
  font-size: 13px;
  color: var(--color-text-primary);
  line-height: 1.5;
}

/* 推荐行业网格 */
.rec-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.rec-card {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
}

.rec-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border);
}

.rec-rank-badge {
  padding: 2px 8px;
  background: var(--color-accent);
  color: #fff;
  border-radius: 2px;
  font-size: 11px;
  font-weight: 700;
}

.rec-sector-name {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.rec-weight-badge {
  padding: 2px 8px;
  background: rgba(37, 99, 235, 0.1);
  border: 1px solid rgba(37, 99, 235, 0.2);
  border-radius: 2px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-accent);
}

.rec-card-body {
  padding: 10px 12px;
}

.rec-reason-text {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin-bottom: 8px;
}

.rec-stock-list {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.rec-stock-tag {
  padding: 2px 6px;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
  border-radius: 2px;
  font-size: 11px;
  color: var(--color-text-muted);
}

/* 热度条 */
.heat-bar {
  display: flex;
  align-items: center;
  gap: 6px;
}

.heat-fill {
  width: 60px;
  height: 6px;
  border-radius: 3px;
  position: relative;
}

.heat-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.error-msg {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: var(--radius);
  padding: 12px 16px;
  color: #ef4444;
  font-size: 13px;
}

.loading-state {
  text-align: center;
  padding: 40px;
  color: var(--color-text-muted);
}

.empty-state {
  text-align: center;
  padding: 20px;
  color: var(--color-text-muted);
  font-size: 13px;
}

@media (max-width: 1024px) {
  .top-metrics {
    grid-template-columns: repeat(2, 1fr);
  }
  .rec-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .top-metrics {
    grid-template-columns: 1fr;
  }
  .rec-grid {
    grid-template-columns: 1fr;
  }
  .heatmap-chart {
    height: 240px;
  }
  .metric-row {
    grid-template-columns: 80px 1fr 36px;
  }
}
</style>
