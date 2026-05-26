<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getMarketSentiment } from '@/services/api'

/** 情绪数据 */
const sentimentData = ref<Record<string, unknown> | null>(null)
/** 加载状态 */
const loading = ref(false)
/** 错误信息 */
const error = ref<string | null>(null)

/** 恐贪指数（0-100） */
const fearGreedIndex = computed((): number => {
  if (!sentimentData.value) return 50
  const val = sentimentData.value.fear_greed_index
    ?? sentimentData.value.fear_greed
    ?? sentimentData.value.index
    ?? sentimentData.value.score
  if (val == null) return 50
  const num = Number(val)
  return isNaN(num) ? 50 : Math.round(Math.max(0, Math.min(100, num)))
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

/** 情绪状态文字 */
const sentimentLabel = computed((): string => {
  const idx = fearGreedIndex.value
  if (idx >= 80) return '极度贪婪'
  if (idx >= 60) return '贪婪'
  if (idx >= 40) return '中性'
  if (idx >= 20) return '恐惧'
  return '极度恐惧'
})

/** 情绪描述 */
const sentimentDescription = computed((): string => {
  if (!sentimentData.value) return ''
  return String(
    sentimentData.value.description
    ?? sentimentData.value.summary
    ?? sentimentData.value.analysis
    ?? ''
  )
})

/** 情绪分项指标 */
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

/** 加载市场情绪数据 */
async function loadSentiment(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const res = await getMarketSentiment()
    sentimentData.value = res?.data ?? res ?? null
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载市场情绪数据失败'
  } finally {
    loading.value = false
  }
}

/** 指标颜色 */
function metricColor(value: number): string {
  if (value >= 70) return '#00B96B'
  if (value >= 50) return '#8BC34A'
  if (value >= 30) return '#FAAD14'
  return '#F5222D'
}

onMounted(loadSentiment)
</script>

<template>
  <div class="sentiment-view">
    <div class="page-header">
      <h2 class="page-title">市场情绪</h2>
      <p class="page-desc">基于多维度指标计算恐贪指数，量化市场情绪状态</p>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <!-- 恐贪指数仪表盘 -->
    <div class="gauge-section">
      <div class="gauge-card">
        <div class="gauge-label-top">恐贪指数</div>
        <div class="gauge-container">
          <svg class="gauge-svg" viewBox="0 0 200 120">
            <!-- 背景弧 -->
            <path
              d="M 20 100 A 80 80 0 0 1 180 100"
              fill="none"
              stroke="#1E2438"
              stroke-width="14"
              stroke-linecap="round"
            />
            <!-- 值弧 -->
            <path
              d="M 20 100 A 80 80 0 0 1 180 100"
              fill="none"
              :stroke="fearGreedColor"
              stroke-width="14"
              stroke-linecap="round"
              :stroke-dasharray="`${(fearGreedIndex / 100) * 251.2} 251.2`"
            />
            <!-- 指针圆点 -->
            <circle
              :cx="20 + (fearGreedIndex / 100) * 160"
              cy="100"
              r="7"
              :fill="fearGreedColor"
            />
          </svg>
          <div class="gauge-value" :style="{ color: fearGreedColor }">{{ fearGreedIndex }}</div>
        </div>
        <div class="gauge-status" :style="{ color: fearGreedColor }">{{ sentimentLabel }}</div>
      </div>

      <!-- 情绪温度计 -->
      <div class="thermometer-card">
        <div class="thermo-label">情绪温度计</div>
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

      <!-- 情绪状态 -->
      <div class="status-card">
        <div class="status-label">市场状态</div>
        <div class="status-value" :style="{ color: fearGreedColor }">{{ sentimentLabel }}</div>
        <div class="status-index">指数: {{ fearGreedIndex }}/100</div>
        <div v-if="sentimentData?.timestamp" class="status-time">
          更新: {{ String(sentimentData.timestamp).substring(0, 16).replace('T', ' ') }}
        </div>
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

    <!-- 分析描述 -->
    <div v-if="sentimentDescription" class="section-card">
      <h3 class="section-title">情绪分析</h3>
      <div class="analysis-text">{{ sentimentDescription }}</div>
    </div>

    <!-- 无数据 -->
    <div v-if="!sentimentData && !loading && !error" class="empty-state">
      暂无市场情绪数据
    </div>

    <div v-if="loading" class="loading-state">加载市场情绪数据...</div>
  </div>
</template>

<style scoped>
.sentiment-view {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100vh;
}

.page-header {
  margin-bottom: 4px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.page-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
}

/* 仪表盘区域 */
.gauge-section {
  display: grid;
  grid-template-columns: 240px 160px 1fr;
  gap: 12px;
}

.gauge-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.gauge-label-top {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.gauge-container {
  position: relative;
  width: 180px;
  height: 100px;
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
  font-size: 32px;
  font-weight: 800;
}

.gauge-status {
  font-size: 16px;
  font-weight: 600;
  margin-top: 4px;
}

/* 温度计 */
.thermometer-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.thermo-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
}

.thermometer {
  display: flex;
  gap: 8px;
  position: relative;
  height: 160px;
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

/* 状态卡片 */
.status-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.status-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.status-value {
  font-size: 28px;
  font-weight: 800;
  margin-bottom: 4px;
}

.status-index {
  font-size: 14px;
  color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
}

.status-time {
  font-size: 11px;
  color: var(--color-text-muted);
  margin-top: 8px;
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

@media (max-width: 1024px) {
  .gauge-section {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .gauge-section {
    grid-template-columns: 1fr;
  }
  .metric-row {
    grid-template-columns: 80px 1fr 36px;
  }
}
</style>
