<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue'
import * as echarts from 'echarts/core'
import { CandlestickChart, LineChart, BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { analyzeStock, getPopularStocks, type AnalyzeResponse, type PopularStock } from '@/services/api'

echarts.use([
  CandlestickChart,
  LineChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  LegendComponent,
  CanvasRenderer,
])

/** K线数据项接口 */
interface KLineItem {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

/** 智能体卡片数据接口 */
interface AgentCardData {
  id: string
  name: string
  icon: string
  signal: string
  confidence: number
  summary: string
  metrics: Array<{ label: string; value: string }>
  expanded: boolean
}

/** 信号颜色映射 */
const SIGNAL_COLORS: Record<string, string> = {
  strong_buy: '#00B96B',
  buy: '#26A69A',
  hold: '#787B86',
  sell: '#EF5350',
  strong_sell: '#C62828',
}

/** 信号中文映射 */
const SIGNAL_LABELS: Record<string, string> = {
  strong_buy: '强烈买入',
  buy: '买入',
  hold: '持有',
  sell: '卖出',
  strong_sell: '强烈卖出',
}

const stockCode = ref('')
const stockName = ref('')
const isAnalyzing = ref(false)
const analysisError = ref<string | null>(null)
const popularStocks = ref<PopularStock[]>([])
const expandedAgentId = ref<string | null>(null)

/** API响应数据 */
const analysisData = ref<AnalyzeResponse | null>(null)
const klineData = ref<KLineItem[]>([])

/** ECharts 实例 */
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

/** 智能体卡片列表 */
const agentCards = computed<AgentCardData[]>(() => {
  if (!analysisData.value) return []
  const d = analysisData.value
  const cards: AgentCardData[] = []

  if (d.technical_analysis) {
    const ta = d.technical_analysis as Record<string, unknown>
    cards.push({
      id: 'technical',
      name: '技术分析',
      icon: '📊',
      signal: String(ta.signal || 'hold'),
      confidence: Number(ta.confidence || 0),
      summary: String(ta.summary || '').substring(0, 80),
      metrics: extractMetrics(ta, ['ma_trend', 'macd_signal', 'rsi_value', 'kdj_signal', 'boll_position', 'atr_value']),
      expanded: expandedAgentId.value === 'technical',
    })
  }

  if (d.fundamental_analysis) {
    const fa = d.fundamental_analysis as Record<string, unknown>
    cards.push({
      id: 'fundamental',
      name: '基本面分析',
      icon: '📋',
      signal: String(fa.signal || 'hold'),
      confidence: Number(fa.confidence || 0),
      summary: String(fa.summary || '').substring(0, 80),
      metrics: extractMetrics(fa, ['pe_ttm', 'pb', 'roe', 'revenue_growth', 'profit_growth', 'debt_ratio']),
      expanded: expandedAgentId.value === 'fundamental',
    })
  }

  if (d.sentiment_analysis) {
    const sa = d.sentiment_analysis as Record<string, unknown>
    cards.push({
      id: 'sentiment',
      name: '情绪分析',
      icon: '💭',
      signal: String(sa.signal || 'hold'),
      confidence: Number(sa.confidence || 0),
      summary: String(sa.summary || '').substring(0, 80),
      metrics: extractMetrics(sa, ['fear_greed_index', 'sentiment_score', 'social_volume', 'news_sentiment']),
      expanded: expandedAgentId.value === 'sentiment',
    })
  }

  if (d.news_analysis) {
    const na = d.news_analysis as Record<string, unknown>
    cards.push({
      id: 'news',
      name: '新闻分析',
      icon: '📰',
      signal: String(na.signal || 'hold'),
      confidence: Number(na.confidence || 0),
      summary: String(na.summary || '').substring(0, 80),
      metrics: extractMetrics(na, ['positive_count', 'negative_count', 'neutral_count', 'impact_score']),
      expanded: expandedAgentId.value === 'news',
    })
  }

  if (d.debate) {
    const db = d.debate as Record<string, unknown>
    cards.push({
      id: 'debate',
      name: '多空辩论',
      icon: '⚖️',
      signal: String(db.winner || 'hold'),
      confidence: Number(db.cooperation_score || 0),
      summary: '多空双方辩论分析',
      metrics: extractMetrics(db, ['bull_score', 'bear_score', 'cooperation_score', 'winner']),
      expanded: expandedAgentId.value === 'debate',
    })
  }

  if (d.risk_assessment) {
    const ra = d.risk_assessment as Record<string, unknown>
    cards.push({
      id: 'risk',
      name: '风险评估',
      icon: '🛡️',
      signal: riskToSignal(String(ra.risk_level || 'medium')),
      confidence: Number(ra.risk_score || 50),
      summary: String(ra.summary || '').substring(0, 80),
      metrics: extractMetrics(ra, ['risk_level', 'var_estimate', 'max_drawdown', 'volatility']),
      expanded: expandedAgentId.value === 'risk',
    })
  }

  if (d.trade_proposal) {
    const tp = d.trade_proposal as Record<string, unknown>
    cards.push({
      id: 'trade',
      name: '交易建议',
      icon: '🎯',
      signal: String(tp.direction || 'hold'),
      confidence: Number(tp.confidence || 0),
      summary: `建议${tp.direction === 'buy' ? '买入' : tp.direction === 'sell' ? '卖出' : '持有'}`,
      metrics: extractMetrics(tp, ['direction', 'position_size_pct', 'entry_price', 'target_price', 'stop_loss_price']),
      expanded: expandedAgentId.value === 'trade',
    })
  }

  return cards
})

/** 多头论点 */
const bullArguments = computed<string[]>(() => {
  if (!analysisData.value?.debate) return []
  const db = analysisData.value.debate as Record<string, unknown>
  const args = db.bull_arguments
  if (Array.isArray(args)) return args.map(String)
  return []
})

/** 空头论点 */
const bearArguments = computed<string[]>(() => {
  if (!analysisData.value?.debate) return []
  const db = analysisData.value.debate as Record<string, unknown>
  const args = db.bear_arguments
  if (Array.isArray(args)) return args.map(String)
  return []
})

/** 最终信号颜色 */
const finalSignalColor = computed(() => {
  const sig = analysisData.value?.final_signal || 'hold'
  return SIGNAL_COLORS[sig] || SIGNAL_COLORS.hold
})

/** 最终信号标签 */
const finalSignalLabel = computed(() => {
  const sig = analysisData.value?.final_signal || 'hold'
  return SIGNAL_LABELS[sig] || '持有'
})

/** 价格变化 */
const priceChange = computed(() => {
  if (!klineData.value || klineData.value.length < 2) return { change: 0, pct: 0 }
  const last = klineData.value[klineData.value.length - 1]
  const prev = klineData.value[klineData.value.length - 2]
  const change = last.close - prev.close
  const pct = prev.close > 0 ? (change / prev.close) * 100 : 0
  return { change, pct }
})

/** 关键指标 */
const keyIndicators = computed(() => {
  const fa = analysisData.value?.fundamental_analysis as Record<string, unknown> | null
  return {
    pe: fa?.pe_ttm ? Number(fa.pe_ttm).toFixed(1) : '-',
    pb: fa?.pb ? Number(fa.pb).toFixed(2) : '-',
    roe: fa?.roe ? Number(fa.roe).toFixed(1) + '%' : '-',
    revGrowth: fa?.revenue_growth ? Number(fa.revenue_growth).toFixed(1) + '%' : '-',
  }
})

/** 数据源状态 */
const dataSources = computed(() => {
  if (!analysisData.value) return {}
  return (analysisData.value as Record<string, unknown>).data_sources_used as Record<string, string> || {}
})

/** 免责声明 */
const disclaimer = computed(() => {
  return (analysisData.value as Record<string, unknown>)?.disclaimer as string || '本分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。'
})

/** 从对象中提取指定key的指标 */
function extractMetrics(data: Record<string, unknown>, keys: string[]): Array<{ label: string; value: string }> {
  const result: Array<{ label: string; value: string }> = []
  for (const key of keys) {
    if (data[key] !== undefined && data[key] !== null) {
      const val = data[key]
      result.push({
        label: formatMetricLabel(key),
        value: typeof val === 'number' ? val.toFixed(2) : String(val),
      })
    }
  }
  return result
}

/** 格式化指标标签 */
function formatMetricLabel(key: string): string {
  const map: Record<string, string> = {
    ma_trend: 'MA趋势',
    macd_signal: 'MACD',
    rsi_value: 'RSI',
    kdj_signal: 'KDJ',
    boll_position: '布林',
    atr_value: 'ATR',
    pe_ttm: 'PE(TTM)',
    pb: 'PB',
    roe: 'ROE',
    revenue_growth: '营收增长',
    profit_growth: '利润增长',
    debt_ratio: '负债率',
    fear_greed_index: '恐惧贪婪',
    sentiment_score: '情绪分',
    social_volume: '社交量',
    news_sentiment: '新闻情绪',
    positive_count: '正面',
    negative_count: '负面',
    neutral_count: '中性',
    impact_score: '影响分',
    bull_score: '多头分',
    bear_score: '空头分',
    cooperation_score: '合作分',
    winner: '胜方',
    risk_level: '风险等级',
    var_estimate: 'VaR',
    max_drawdown: '最大回撤',
    volatility: '波动率',
    risk_score: '风险分',
    direction: '方向',
    position_size_pct: '仓位%',
    entry_price: '入场价',
    target_price: '目标价',
    stop_loss_price: '止损价',
    confidence: '置信度',
  }
  return map[key] || key
}

/** 风险等级转信号 */
function riskToSignal(level: string): string {
  if (level.includes('低') || level === 'low') return 'buy'
  if (level.includes('高') || level === 'high') return 'sell'
  if (level.includes('极') || level === 'extreme') return 'strong_sell'
  return 'hold'
}

/** 计算MA均线 */
function calculateMA(days: number, data: KLineItem[]): (number | null)[] {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < days - 1) {
      result.push(null)
    } else {
      let sum = 0
      for (let j = 0; j < days; j++) {
        sum += data[i - j].close
      }
      result.push(Number((sum / days).toFixed(2)))
    }
  }
  return result
}

/** 计算MACD */
function calculateMACD(data: KLineItem[], shortPeriod: number = 12, longPeriod: number = 26, signalPeriod: number = 9): {
  dif: (number | null)[]
  dea: (number | null)[]
  macd: (number | null)[]
} {
  const closes = data.map(d => d.close)
  const dif: (number | null)[] = []
  const dea: (number | null)[] = []
  const macd: (number | null)[] = []

  let emaShort = closes[0]
  let emaLong = closes[0]
  let emaSignal = 0

  for (let i = 0; i < closes.length; i++) {
    if (i === 0) {
      emaShort = closes[0]
      emaLong = closes[0]
      dif.push(null)
      dea.push(null)
      macd.push(null)
      continue
    }

    emaShort = (closes[i] * 2 / (shortPeriod + 1)) + emaShort * (1 - 2 / (shortPeriod + 1))
    emaLong = (closes[i] * 2 / (longPeriod + 1)) + emaLong * (1 - 2 / (longPeriod + 1))
    const difVal = emaShort - emaLong

    if (i === 1) {
      emaSignal = difVal
    } else {
      emaSignal = (difVal * 2 / (signalPeriod + 1)) + emaSignal * (1 - 2 / (signalPeriod + 1))
    }

    dif.push(Number(difVal.toFixed(4)))
    dea.push(Number(emaSignal.toFixed(4)))
    macd.push(Number(((difVal - emaSignal) * 2).toFixed(4)))
  }

  return { dif, dea, macd }
}

/** 计算RSI */
function calculateRSI(data: KLineItem[], period: number = 14): (number | null)[] {
  const result: (number | null)[] = []
  let gainSum = 0
  let lossSum = 0

  for (let i = 0; i < data.length; i++) {
    if (i === 0) {
      result.push(null)
      continue
    }

    const change = data[i].close - data[i - 1].close
    const gain = change > 0 ? change : 0
    const loss = change < 0 ? Math.abs(change) : 0

    if (i <= period) {
      gainSum += gain
      lossSum += loss
      if (i === period) {
        const avgGain = gainSum / period
        const avgLoss = lossSum / period
        const rsi = avgLoss === 0 ? 100 : 100 - (100 / (1 + avgGain / avgLoss))
        result.push(Number(rsi.toFixed(2)))
      } else {
        result.push(null)
      }
    } else {
      const prevAvgGain = gainSum / period
      const prevAvgLoss = lossSum / period
      const avgGain = (prevAvgGain * (period - 1) + gain) / period
      const avgLoss = (prevAvgLoss * (period - 1) + loss) / period
      gainSum = avgGain * period
      lossSum = avgLoss * period
      const rsi = avgLoss === 0 ? 100 : 100 - (100 / (1 + avgGain / avgLoss))
      result.push(Number(rsi.toFixed(2)))
    }
  }

  return result
}

/** 初始化ECharts K线图 */
function initChart(): void {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value, undefined, {
    renderer: 'canvas',
  })
  updateChart()
}

/** 更新K线图数据 */
function updateChart(): void {
  if (!chartInstance || klineData.value.length === 0) return

  const data = klineData.value
  const dates = data.map(d => d.date)
  const ohlc = data.map(d => [d.open, d.close, d.low, d.high])
  const volumes = data.map(d => d.volume)
  const ma5 = calculateMA(5, data)
  const ma10 = calculateMA(10, data)
  const ma20 = calculateMA(20, data)
  const ma60 = calculateMA(60, data)
  const { dif, dea, macd } = calculateMACD(data)
  const rsi = calculateRSI(data)

  chartInstance.setOption({
    animation: false,
    backgroundColor: '#131722',
    legend: {
      show: true,
      top: 2,
      left: 60,
      textStyle: { color: '#787B86', fontSize: 10 },
      itemWidth: 12,
      itemHeight: 8,
      itemGap: 8,
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', crossStyle: { color: '#363a45' } },
      backgroundColor: 'rgba(19, 23, 34, 0.95)',
      borderColor: '#363a45',
      textStyle: { color: '#D1D4DC', fontSize: 11, fontFamily: 'Consolas, monospace' },
    },
    axisPointer: {
      link: [{ xAxisIndex: [0, 1, 2] }],
    },
    grid: [
      { left: 50, right: 50, top: 24, height: '42%' },
      { left: 50, right: 50, top: '52%', height: '14%' },
      { left: 50, right: 50, top: '72%', height: '10%' },
      { left: 50, right: 50, top: '87%', height: '8%' },
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        gridIndex: 0,
        axisLine: { lineStyle: { color: '#363a45' } },
        axisTick: { show: false },
        axisLabel: { show: false },
        splitLine: { show: true, lineStyle: { color: '#1E222D', type: 'solid' } },
      },
      {
        type: 'category',
        data: dates,
        gridIndex: 1,
        axisLine: { lineStyle: { color: '#363a45' } },
        axisTick: { show: false },
        axisLabel: { show: false },
        splitLine: { show: false },
      },
      {
        type: 'category',
        data: dates,
        gridIndex: 2,
        axisLine: { lineStyle: { color: '#363a45' } },
        axisTick: { show: false },
        axisLabel: { show: false },
        splitLine: { show: false },
      },
      {
        type: 'category',
        data: dates,
        gridIndex: 3,
        axisLine: { lineStyle: { color: '#363a45' } },
        axisTick: { show: false },
        axisLabel: { color: '#787B86', fontSize: 9 },
        splitLine: { show: false },
      },
    ],
    yAxis: [
      {
        scale: true,
        gridIndex: 0,
        position: 'right',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#787B86', fontSize: 9, fontFamily: 'Consolas, monospace' },
        splitLine: { lineStyle: { color: '#1E222D', type: 'solid' } },
      },
      {
        scale: true,
        gridIndex: 1,
        position: 'right',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#787B86', fontSize: 9, fontFamily: 'Consolas, monospace' },
        splitLine: { lineStyle: { color: '#1E222D', type: 'dashed' } },
      },
      {
        scale: true,
        gridIndex: 2,
        position: 'right',
        min: 0,
        max: 100,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#787B86', fontSize: 9, fontFamily: 'Consolas, monospace' },
        splitLine: { lineStyle: { color: '#1E222D', type: 'dashed' } },
      },
      {
        scale: true,
        gridIndex: 3,
        position: 'right',
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#787B86', fontSize: 9, fontFamily: 'Consolas, monospace' },
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1, 2, 3],
        start: 60,
        end: 100,
      },
      {
        type: 'slider',
        xAxisIndex: [0, 1, 2, 3],
        start: 60,
        end: 100,
        height: 14,
        bottom: 2,
        borderColor: '#363a45',
        backgroundColor: '#131722',
        fillerColor: 'rgba(33, 150, 243, 0.15)',
        handleStyle: { color: '#2196F3', borderColor: '#2196F3' },
        textStyle: { color: '#787B86', fontSize: 9 },
        dataBackground: {
          lineStyle: { color: '#363a45' },
          areaStyle: { color: '#1E222D' },
        },
      },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlc,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: '#EF5350',
          color0: '#26A69A',
          borderColor: '#EF5350',
          borderColor0: '#26A69A',
        },
      },
      {
        name: 'MA5',
        type: 'line',
        data: ma5,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#F5C842' },
      },
      {
        name: 'MA10',
        type: 'line',
        data: ma10,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#2196F3' },
      },
      {
        name: 'MA20',
        type: 'line',
        data: ma20,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#E040FB' },
      },
      {
        name: 'MA60',
        type: 'line',
        data: ma60,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1, color: '#FF9800' },
      },
      {
        name: '成交量',
        type: 'bar',
        data: volumes,
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: {
          color: (params: { dataIndex: number }) => {
            const idx = params.dataIndex
            if (!data[idx]) return '#363a45'
            return data[idx].close >= data[idx].open
              ? 'rgba(38,166,154,0.6)'
              : 'rgba(239,83,80,0.6)'
          },
        },
      },
      {
        name: 'DIF',
        type: 'line',
        data: dif,
        xAxisIndex: 2,
        yAxisIndex: 2,
        showSymbol: false,
        lineStyle: { width: 1, color: '#2196F3' },
      },
      {
        name: 'DEA',
        type: 'line',
        data: dea,
        xAxisIndex: 2,
        yAxisIndex: 2,
        showSymbol: false,
        lineStyle: { width: 1, color: '#FF9800' },
      },
      {
        name: 'MACD',
        type: 'bar',
        data: macd,
        xAxisIndex: 2,
        yAxisIndex: 2,
        itemStyle: {
          color: (params: { data: number | null }) => {
            return params.data !== null && params.data >= 0
              ? 'rgba(239,83,80,0.6)'
              : 'rgba(38,166,154,0.6)'
          },
        },
      },
      {
        name: 'RSI(14)',
        type: 'line',
        data: rsi,
        xAxisIndex: 3,
        yAxisIndex: 3,
        showSymbol: false,
        lineStyle: { width: 1, color: '#E040FB' },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: '#363a45', type: 'dashed', width: 1 },
          data: [
            { yAxis: 70, label: { formatter: '70', color: '#787B86', fontSize: 9 } },
            { yAxis: 30, label: { formatter: '30', color: '#787B86', fontSize: 9 } },
          ],
        },
      },
    ],
  }, true)
}

/** 启动分析 */
async function startAnalysis(): Promise<void> {
  if (!stockCode.value.trim() || isAnalyzing.value) return

  isAnalyzing.value = true
  analysisError.value = null
  analysisData.value = null
  expandedAgentId.value = null

  try {
    const response = await analyzeStock({
      stock_code: stockCode.value.trim(),
      stock_name: stockName.value.trim() || undefined,
    })

    analysisData.value = response

    if (response.price_data && response.price_data.length > 0) {
      klineData.value = response.price_data
      await nextTick()
      updateChart()
    }
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : '未知错误'
    analysisError.value = errorMessage
  } finally {
    isAnalyzing.value = false
  }
}

/** 填充热门股票 */
function fillStock(code: string, name: string): void {
  stockCode.value = code
  stockName.value = name
}

/** 切换智能体卡片展开 */
function toggleAgentExpand(id: string): void {
  expandedAgentId.value = expandedAgentId.value === id ? null : id
}

/** 获取信号颜色 */
function getSignalColor(signal: string): string {
  return SIGNAL_COLORS[signal] || SIGNAL_COLORS.hold
}

/** 获取信号标签 */
function getSignalLabel(signal: string): string {
  return SIGNAL_LABELS[signal] || signal
}

/** 窗口resize处理 */
function handleResize(): void {
  chartInstance?.resize()
}

onMounted(async () => {
  try {
    const res = await getPopularStocks()
    popularStocks.value = res.stocks
  } catch {
    popularStocks.value = [
      { code: '600519.SH', name: '贵州茅台', industry: '白酒' },
      { code: '000858.SZ', name: '五粮液', industry: '白酒' },
      { code: '000001.SZ', name: '平安银行', industry: '银行' },
      { code: '600036.SH', name: '招商银行', industry: '银行' },
    ]
  }

  await nextTick()
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', handleResize)
})

watch(() => klineData.value.length, () => {
  nextTick(() => updateChart())
})
</script>

<template>
  <div class="tv-view">
    <!-- 顶部工具栏 -->
    <header class="tv-toolbar">
      <div class="tv-toolbar-left">
        <div class="tv-search">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#787B86" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
          <input
            v-model="stockCode"
            type="text"
            placeholder="股票代码"
            class="tv-search-input"
            @keyup.enter="startAnalysis"
            :disabled="isAnalyzing"
          />
          <input
            v-model="stockName"
            type="text"
            placeholder="名称(可选)"
            class="tv-search-input tv-search-name"
            @keyup.enter="startAnalysis"
            :disabled="isAnalyzing"
          />
          <button
            class="tv-analyze-btn"
            @click="startAnalysis"
            :disabled="isAnalyzing || !stockCode.trim()"
          >
            {{ isAnalyzing ? '⏳' : '▶' }} 分析
          </button>
        </div>
        <div class="tv-popular">
          <span class="tv-popular-label">热门</span>
          <button
            v-for="s in popularStocks"
            :key="s.code"
            class="tv-popular-tag"
            @click="fillStock(s.code, s.name)"
            :disabled="isAnalyzing"
          >
            {{ s.name }}
          </button>
        </div>
      </div>

      <!-- 价格和指标区 -->
      <div v-if="analysisData" class="tv-price-bar">
        <div class="tv-stock-identity">
          <span class="tv-stock-name">{{ analysisData.stock_name }}</span>
          <span class="tv-stock-code">{{ analysisData.stock_code }}</span>
        </div>
        <div class="tv-price-main">
          <span class="tv-price-value" :class="priceChange.pct >= 0 ? 'tv-up' : 'tv-down'">
            {{ analysisData.current_price?.toFixed(2) || '-' }}
          </span>
          <span class="tv-price-change" :class="priceChange.pct >= 0 ? 'tv-up' : 'tv-down'">
            {{ priceChange.pct >= 0 ? '+' : '' }}{{ priceChange.change.toFixed(2) }}
            ({{ priceChange.pct >= 0 ? '+' : '' }}{{ priceChange.pct.toFixed(2) }}%)
          </span>
        </div>
        <div class="tv-key-metrics">
          <div class="tv-metric">
            <span class="tv-metric-label">PE</span>
            <span class="tv-metric-value">{{ keyIndicators.pe }}</span>
          </div>
          <div class="tv-metric">
            <span class="tv-metric-label">PB</span>
            <span class="tv-metric-value">{{ keyIndicators.pb }}</span>
          </div>
          <div class="tv-metric">
            <span class="tv-metric-label">ROE</span>
            <span class="tv-metric-value">{{ keyIndicators.roe }}</span>
          </div>
          <div class="tv-metric">
            <span class="tv-metric-label">营收增</span>
            <span class="tv-metric-value">{{ keyIndicators.revGrowth }}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- 主体区域 -->
    <div class="tv-main">
      <!-- 左侧K线图 -->
      <div class="tv-chart-area">
        <div v-if="isAnalyzing" class="tv-chart-loading">
          <div class="tv-spinner"></div>
          <span>分析中...</span>
        </div>
        <div v-if="!analysisData && !isAnalyzing" class="tv-chart-empty">
          <div class="tv-empty-icon">📈</div>
          <div class="tv-empty-text">输入股票代码开始分析</div>
        </div>
        <div
          ref="chartRef"
          class="tv-chart-canvas"
          :style="{ visibility: klineData.length > 0 ? 'visible' : 'hidden' }"
        ></div>
      </div>

      <!-- 右侧分析面板 -->
      <div class="tv-panel">
        <!-- 最终信号 -->
        <div v-if="analysisData" class="tv-signal-box" :style="{ borderColor: finalSignalColor }">
          <div class="tv-signal-left">
            <span class="tv-signal-label">综合信号</span>
            <span class="tv-signal-value" :style="{ color: finalSignalColor }">
              {{ finalSignalLabel }}
            </span>
          </div>
          <div class="tv-signal-right">
            <span class="tv-signal-conf-label">置信度</span>
            <span class="tv-signal-conf-value" :style="{ color: finalSignalColor }">
              {{ analysisData.final_confidence || 0 }}%
            </span>
          </div>
        </div>

        <!-- 智能体卡片列表 -->
        <div class="tv-agents-list">
          <div
            v-for="card in agentCards"
            :key="card.id"
            class="tv-agent-card"
            :class="{ 'tv-agent-expanded': card.expanded }"
            @click="toggleAgentExpand(card.id)"
          >
            <div class="tv-agent-header">
              <div class="tv-agent-info">
                <span class="tv-agent-icon">{{ card.icon }}</span>
                <span class="tv-agent-name">{{ card.name }}</span>
              </div>
              <div class="tv-agent-signal">
                <span
                  class="tv-signal-dot"
                  :style="{ backgroundColor: getSignalColor(card.signal) }"
                ></span>
                <span class="tv-signal-text" :style="{ color: getSignalColor(card.signal) }">
                  {{ getSignalLabel(card.signal) }}
                </span>
                <span class="tv-agent-conf">{{ card.confidence }}%</span>
              </div>
            </div>
            <div v-if="card.summary" class="tv-agent-summary">{{ card.summary }}</div>
            <div v-if="card.expanded && card.metrics.length > 0" class="tv-agent-metrics">
              <div v-for="m in card.metrics" :key="m.label" class="tv-metric-row">
                <span class="tv-metric-key">{{ m.label }}</span>
                <span class="tv-metric-val">{{ m.value }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 多空辩论 -->
        <div v-if="analysisData?.debate" class="tv-debate">
          <div class="tv-debate-header">
            <span class="tv-debate-title">⚔️ 多空辩论</span>
            <span
              v-if="(analysisData.debate as Record<string, unknown>).winner"
              class="tv-debate-winner"
              :style="{
                color: String((analysisData.debate as Record<string, unknown>).winner).includes('bull')
                  ? '#26A69A'
                  : String((analysisData.debate as Record<string, unknown>).winner).includes('bear')
                    ? '#EF5350'
                  : '#787B86'
              }"
            >
              {{ String((analysisData.debate as Record<string, unknown>).winner).includes('bull') ? '多头胜' :
                 String((analysisData.debate as Record<string, unknown>).winner).includes('bear') ? '空头胜' : '平局' }}
            </span>
          </div>
          <div class="tv-debate-cols">
            <div class="tv-debate-bull">
              <div class="tv-debate-col-title">🐂 多头</div>
              <div v-for="(arg, idx) in bullArguments.slice(0, 3)" :key="idx" class="tv-debate-arg tv-bull-arg">
                {{ arg }}
              </div>
            </div>
            <div class="tv-debate-bear">
              <div class="tv-debate-col-title">🐻 空头</div>
              <div v-for="(arg, idx) in bearArguments.slice(0, 3)" :key="idx" class="tv-debate-arg tv-bear-arg">
                {{ arg }}
              </div>
            </div>
          </div>
        </div>

        <!-- 交易建议摘要 -->
        <div v-if="analysisData?.trade_proposal" class="tv-trade-summary">
          <div class="tv-trade-header">🎯 交易建议</div>
          <div class="tv-trade-grid">
            <div class="tv-trade-cell">
              <span class="tv-trade-label">方向</span>
              <span
                class="tv-trade-value"
                :style="{
                  color: String((analysisData.trade_proposal as Record<string, unknown>).direction) === 'buy'
                    ? '#26A69A'
                    : String((analysisData.trade_proposal as Record<string, unknown>).direction) === 'sell'
                      ? '#EF5350'
                      : '#787B86'
                }"
              >
                {{ String((analysisData.trade_proposal as Record<string, unknown>).direction) === 'buy'
                  ? '买入' : String((analysisData.trade_proposal as Record<string, unknown>).direction) === 'sell'
                  ? '卖出' : '持有' }}
              </span>
            </div>
            <div class="tv-trade-cell">
              <span class="tv-trade-label">仓位</span>
              <span class="tv-trade-value">{{ (analysisData.trade_proposal as Record<string, unknown>).position_size_pct }}%</span>
            </div>
            <div class="tv-trade-cell">
              <span class="tv-trade-label">入场</span>
              <span class="tv-trade-value">{{ (analysisData.trade_proposal as Record<string, unknown>).entry_price }}</span>
            </div>
            <div class="tv-trade-cell">
              <span class="tv-trade-label">目标</span>
              <span class="tv-trade-value tv-up">{{ (analysisData.trade_proposal as Record<string, unknown>).target_price }}</span>
            </div>
            <div class="tv-trade-cell">
              <span class="tv-trade-label">止损</span>
              <span class="tv-trade-value tv-down">{{ (analysisData.trade_proposal as Record<string, unknown>).stop_loss_price }}</span>
            </div>
            <div class="tv-trade-cell">
              <span class="tv-trade-label">风险</span>
              <span
                class="tv-trade-value"
                :style="{
                  color: String((analysisData.risk_assessment as Record<string, unknown> | null)?.risk_level).includes('低')
                    ? '#26A69A'
                    : String((analysisData.risk_assessment as Record<string, unknown> | null)?.risk_level).includes('高')
                      ? '#EF5350'
                      : '#FAAD14'
                }"
              >
                {{ (analysisData.risk_assessment as Record<string, unknown> | null)?.risk_level || '-' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部状态栏 -->
    <footer class="tv-footer">
      <div class="tv-footer-left">
        <span class="tv-disclaimer">⚠️ {{ disclaimer }}</span>
      </div>
      <div class="tv-footer-right">
        <template v-if="Object.keys(dataSources).length > 0">
          <span
            v-for="(source, key) in dataSources"
            :key="key"
            class="tv-data-source"
          >
            <span class="tv-source-dot"></span>
            {{ key }}: {{ source }}
          </span>
        </template>
        <span v-else class="tv-data-source">
          <span class="tv-source-dot tv-source-off"></span>
          未连接
        </span>
      </div>
    </footer>

    <!-- 错误提示 -->
    <Transition name="tv-fade">
      <div v-if="analysisError" class="tv-error-toast">
        <span>❌ {{ analysisError }}</span>
        <button class="tv-error-close" @click="analysisError = null">×</button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.tv-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #131722;
  color: #D1D4DC;
  font-size: 12px;
  overflow: hidden;
}

/* ===== 顶部工具栏 ===== */
.tv-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 36px;
  padding: 0 8px;
  background: #1E222D;
  border-bottom: 1px solid #363a45;
  flex-shrink: 0;
  gap: 12px;
}

.tv-toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.tv-search {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #131722;
  border: 1px solid #363a45;
  padding: 0 6px;
  height: 24px;
}

.tv-search:focus-within {
  border-color: #2196F3;
}

.tv-search-input {
  background: none;
  border: none;
  color: #D1D4DC;
  font-size: 11px;
  outline: none;
  width: 100px;
  height: 22px;
  font-family: 'Consolas', 'Courier New', monospace;
}

.tv-search-input::placeholder {
  color: #4A5168;
}

.tv-search-name {
  width: 70px;
  border-left: 1px solid #363a45;
  padding-left: 6px;
}

.tv-analyze-btn {
  padding: 0 10px;
  height: 24px;
  background: #2196F3;
  color: #fff;
  border: none;
  font-size: 11px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}

.tv-analyze-btn:hover:not(:disabled) {
  background: #1E88E5;
}

.tv-analyze-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tv-popular {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tv-popular-label {
  color: #4A5168;
  font-size: 10px;
}

.tv-popular-tag {
  padding: 1px 6px;
  background: transparent;
  border: 1px solid #363a45;
  color: #787B86;
  font-size: 10px;
  cursor: pointer;
  transition: all 0.15s;
}

.tv-popular-tag:hover:not(:disabled) {
  border-color: #2196F3;
  color: #2196F3;
}

.tv-popular-tag:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 价格指标区 */
.tv-price-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.tv-stock-identity {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.tv-stock-name {
  font-size: 13px;
  font-weight: 600;
  color: #D1D4DC;
}

.tv-stock-code {
  font-size: 10px;
  color: #787B86;
  font-family: 'Consolas', monospace;
}

.tv-price-main {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.tv-price-value {
  font-size: 16px;
  font-weight: 700;
  font-family: 'Consolas', monospace;
}

.tv-price-change {
  font-size: 11px;
  font-family: 'Consolas', monospace;
}

.tv-up { color: #EF5350; }
.tv-down { color: #26A69A; }

.tv-key-metrics {
  display: flex;
  gap: 12px;
}

.tv-metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.tv-metric-label {
  font-size: 9px;
  color: #4A5168;
}

.tv-metric-value {
  font-size: 11px;
  color: #D1D4DC;
  font-family: 'Consolas', monospace;
}

/* ===== 主体区域 ===== */
.tv-main {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* 左侧K线图 */
.tv-chart-area {
  flex: 0 0 60%;
  position: relative;
  border-right: 1px solid #363a45;
}

.tv-chart-canvas {
  width: 100%;
  height: 100%;
}

.tv-chart-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: rgba(19, 23, 34, 0.85);
  z-index: 10;
  color: #787B86;
  font-size: 12px;
}

.tv-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #363a45;
  border-top-color: #2196F3;
  border-radius: 50%;
  animation: tv-spin 0.8s linear infinite;
}

@keyframes tv-spin {
  to { transform: rotate(360deg); }
}

.tv-chart-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #4A5168;
}

.tv-empty-icon {
  font-size: 36px;
}

.tv-empty-text {
  font-size: 13px;
}

/* 右侧面板 */
.tv-panel {
  flex: 0 0 40%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #131722;
}

/* 最终信号 */
.tv-signal-box {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  border-left: 3px solid #787B86;
  background: #1E222D;
  flex-shrink: 0;
}

.tv-signal-left,
.tv-signal-right {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.tv-signal-label,
.tv-signal-conf-label {
  font-size: 10px;
  color: #787B86;
}

.tv-signal-value {
  font-size: 14px;
  font-weight: 700;
}

.tv-signal-conf-value {
  font-size: 14px;
  font-weight: 700;
  font-family: 'Consolas', monospace;
}

/* 智能体卡片列表 */
.tv-agents-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px;
}

.tv-agent-card {
  padding: 4px 6px;
  border-bottom: 1px solid #1E222D;
  cursor: pointer;
  transition: background 0.1s;
}

.tv-agent-card:hover {
  background: #1E222D;
}

.tv-agent-expanded {
  background: #1E222D;
}

.tv-agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tv-agent-info {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tv-agent-icon {
  font-size: 12px;
}

.tv-agent-name {
  font-size: 11px;
  font-weight: 500;
  color: #D1D4DC;
}

.tv-agent-signal {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tv-signal-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.tv-signal-text {
  font-size: 10px;
  font-weight: 600;
}

.tv-agent-conf {
  font-size: 10px;
  color: #787B86;
  font-family: 'Consolas', monospace;
}

.tv-agent-summary {
  font-size: 10px;
  color: #787B86;
  padding: 2px 0 2px 18px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tv-agent-metrics {
  padding: 4px 0 2px 18px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px 12px;
}

.tv-metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1px 0;
}

.tv-metric-key {
  font-size: 10px;
  color: #4A5168;
}

.tv-metric-val {
  font-size: 10px;
  color: #D1D4DC;
  font-family: 'Consolas', monospace;
}

/* 多空辩论 */
.tv-debate {
  border-top: 1px solid #363a45;
  padding: 6px 8px;
  flex-shrink: 0;
  background: #1E222D;
}

.tv-debate-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.tv-debate-title {
  font-size: 11px;
  font-weight: 600;
  color: #D1D4DC;
}

.tv-debate-winner {
  font-size: 11px;
  font-weight: 700;
}

.tv-debate-cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.tv-debate-col-title {
  font-size: 10px;
  font-weight: 600;
  margin-bottom: 2px;
}

.tv-debate-bull .tv-debate-col-title {
  color: #26A69A;
}

.tv-debate-bear .tv-debate-col-title {
  color: #EF5350;
}

.tv-debate-arg {
  font-size: 10px;
  line-height: 1.4;
  padding: 1px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tv-bull-arg {
  color: #26A69A;
}

.tv-bear-arg {
  color: #EF5350;
}

/* 交易建议 */
.tv-trade-summary {
  border-top: 1px solid #363a45;
  padding: 6px 8px;
  flex-shrink: 0;
  background: #1E222D;
}

.tv-trade-header {
  font-size: 11px;
  font-weight: 600;
  color: #D1D4DC;
  margin-bottom: 4px;
}

.tv-trade-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2px 8px;
}

.tv-trade-cell {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.tv-trade-label {
  font-size: 9px;
  color: #4A5168;
}

.tv-trade-value {
  font-size: 11px;
  font-weight: 600;
  color: #D1D4DC;
  font-family: 'Consolas', monospace;
}

/* ===== 底部状态栏 ===== */
.tv-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  background: #1E222D;
  border-top: 1px solid #363a45;
  flex-shrink: 0;
}

.tv-footer-left {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tv-disclaimer {
  font-size: 9px;
  color: #4A5168;
}

.tv-footer-right {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.tv-data-source {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 9px;
  color: #787B86;
}

.tv-source-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #26A69A;
}

.tv-source-off {
  background: #4A5168;
}

/* 错误提示 */
.tv-error-toast {
  position: fixed;
  top: 44px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(239, 83, 80, 0.15);
  border: 1px solid rgba(239, 83, 80, 0.3);
  color: #EF5350;
  font-size: 11px;
  z-index: 100;
}

.tv-error-close {
  background: none;
  border: none;
  color: #EF5350;
  cursor: pointer;
  font-size: 14px;
  padding: 0 4px;
}

/* 动画 */
.tv-fade-enter-active,
.tv-fade-leave-active {
  transition: opacity 0.2s ease;
}

.tv-fade-enter-from,
.tv-fade-leave-to {
  opacity: 0;
}

/* 响应式 */
@media (max-width: 1024px) {
  .tv-main {
    flex-direction: column;
  }
  .tv-chart-area {
    flex: 0 0 50%;
    border-right: none;
    border-bottom: 1px solid #363a45;
  }
  .tv-panel {
    flex: 1;
  }
  .tv-key-metrics {
    display: none;
  }
}

@media (max-width: 768px) {
  .tv-search-name {
    display: none;
  }
  .tv-popular {
    display: none;
  }
  .tv-price-bar {
    gap: 8px;
  }
}
</style>
