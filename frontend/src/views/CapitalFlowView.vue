<script setup lang="ts">
import { ref } from 'vue'
import { analyzeCapitalFlow } from '@/services/api'

/** 股票代码输入 */
const stockCode = ref('')
/** 股票名称输入 */
const stockName = ref('')
/** 分析结果 */
const analysisResult = ref<Record<string, unknown> | null>(null)
/** 加载状态 */
const loading = ref(false)
/** 错误信息 */
const error = ref<string | null>(null)

/** 执行资金流向分析 */
async function handleAnalyze(): Promise<void> {
  if (!stockCode.value.trim()) return
  loading.value = true
  error.value = null
  analysisResult.value = null
  try {
    const res = await analyzeCapitalFlow(stockCode.value.trim(), stockName.value.trim())
    analysisResult.value = res?.data ?? res ?? null
  } catch (e) {
    error.value = e instanceof Error ? e.message : '资金流向分析失败'
  } finally {
    loading.value = false
  }
}

/** 获取资金流向数据对象 */
function getCapitalData(): Record<string, unknown> | null {
  if (!analysisResult.value) return null
  return (analysisResult.value.capital_flow ?? analysisResult.value.main_flow ?? analysisResult.value) as Record<string, unknown> | null
}

/** 获取主力资金数据 */
function getMainFlow(): Record<string, unknown> | null {
  const data = getCapitalData()
  if (!data) return null
  return (data.main_force ?? data.main ?? data.institutional ?? null) as Record<string, unknown> | null
}

/** 获取北向资金数据 */
function getNorthFlow(): Record<string, unknown> | null {
  const data = getCapitalData()
  if (!data) return null
  return (data.northbound ?? data.north ?? data.hk_connect ?? null) as Record<string, unknown> | null
}

/** 获取融资融券数据 */
function getMarginData(): Record<string, unknown> | null {
  const data = getCapitalData()
  if (!data) return null
  return (data.margin ?? data.margin_trading ?? null) as Record<string, unknown> | null
}

/** 格式化金额（亿元） */
function formatAmount(val: unknown): string {
  if (val == null) return '-'
  const num = Number(val)
  if (isNaN(num)) return String(val)
  const absNum = Math.abs(num)
  if (absNum >= 1e8) return (num / 1e8).toFixed(2) + '亿'
  if (absNum >= 1e4) return (num / 1e4).toFixed(2) + '万'
  return num.toFixed(2)
}

/** 涨跌颜色类 */
function flowClass(val: unknown): string {
  const num = Number(val)
  if (isNaN(num)) return ''
  return num >= 0 ? 'value-positive' : 'value-negative'
}

/** 格式化带符号数字 */
function formatSigned(val: unknown): string {
  if (val == null) return '-'
  const num = Number(val)
  if (isNaN(num)) return String(val)
  return num >= 0 ? '+' + num.toFixed(2) : num.toFixed(2)
}
</script>

<template>
  <div class="capital-flow-view">
    <div class="page-header">
      <h2 class="page-title">资金流向</h2>
      <p class="page-desc">分析个股主力资金、北向资金及融资融券数据，洞察资金动向</p>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <!-- 查询面板 -->
    <div class="query-panel card">
      <div class="form-row">
        <div class="form-field">
          <label class="field-label">股票代码</label>
          <input
            v-model="stockCode"
            class="input"
            placeholder="例如 600519.SH"
            @keyup.enter="handleAnalyze"
          />
        </div>
        <div class="form-field">
          <label class="field-label">股票名称</label>
          <input
            v-model="stockName"
            class="input"
            placeholder="例如 贵州茅台（可选）"
            @keyup.enter="handleAnalyze"
          />
        </div>
        <div class="form-field form-action">
          <button
            class="btn-primary"
            :disabled="loading || !stockCode.trim()"
            @click="handleAnalyze"
          >
            分析资金流向
          </button>
        </div>
      </div>
    </div>

    <!-- 分析结果 -->
    <template v-if="analysisResult">
      <!-- 概览指标 -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-label">股票</div>
          <div class="metric-value">{{ analysisResult.stock_name || analysisResult.stock_code || stockCode }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">分析时间</div>
          <div class="metric-value">{{ String(analysisResult.timestamp || analysisResult.analyzed_at || '').substring(0, 16).replace('T', ' ') }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">资金信号</div>
          <div class="metric-value" :class="flowClass(analysisResult.net_inflow ?? analysisResult.net_flow)">
            {{ analysisResult.signal || analysisResult.flow_signal || '-' }}
          </div>
        </div>
      </div>

      <!-- 主力资金 -->
      <div v-if="getMainFlow()" class="section-card">
        <h3 class="section-title">主力资金</h3>
        <div class="flow-grid">
          <div class="flow-item">
            <div class="flow-label">净流入</div>
            <div class="flow-value" :class="flowClass(getMainFlow()?.net_inflow ?? getMainFlow()?.net)">
              {{ formatSigned(getMainFlow()?.net_inflow ?? getMainFlow()?.net) }}
            </div>
          </div>
          <div class="flow-item">
            <div class="flow-label">流入金额</div>
            <div class="flow-value value-positive">{{ formatAmount(getMainFlow()?.inflow ?? getMainFlow()?.buy) }}</div>
          </div>
          <div class="flow-item">
            <div class="flow-label">流出金额</div>
            <div class="flow-value value-negative">{{ formatAmount(getMainFlow()?.outflow ?? getMainFlow()?.sell) }}</div>
          </div>
          <div class="flow-item">
            <div class="flow-label">净流入占比</div>
            <div class="flow-value">{{ getMainFlow()?.net_pct != null ? Number(getMainFlow()?.net_pct).toFixed(2) + '%' : '-' }}</div>
          </div>
        </div>
      </div>

      <!-- 北向资金 -->
      <div v-if="getNorthFlow()" class="section-card">
        <h3 class="section-title">北向资金</h3>
        <div class="flow-grid">
          <div class="flow-item">
            <div class="flow-label">净买入</div>
            <div class="flow-value" :class="flowClass(getNorthFlow()?.net_inflow ?? getNorthFlow()?.net)">
              {{ formatSigned(getNorthFlow()?.net_inflow ?? getNorthFlow()?.net) }}
            </div>
          </div>
          <div class="flow-item">
            <div class="flow-label">买入金额</div>
            <div class="flow-value value-positive">{{ formatAmount(getNorthFlow()?.inflow ?? getNorthFlow()?.buy) }}</div>
          </div>
          <div class="flow-item">
            <div class="flow-label">卖出金额</div>
            <div class="flow-value value-negative">{{ formatAmount(getNorthFlow()?.outflow ?? getNorthFlow()?.sell) }}</div>
          </div>
          <div class="flow-item">
            <div class="flow-label">持仓变化</div>
            <div class="flow-value">{{ formatAmount(getNorthFlow()?.holding_change ?? getNorthFlow()?.position_change) }}</div>
          </div>
        </div>
      </div>

      <!-- 融资融券 -->
      <div v-if="getMarginData()" class="section-card">
        <h3 class="section-title">融资融券</h3>
        <div class="flow-grid">
          <div class="flow-item">
            <div class="flow-label">融资余额</div>
            <div class="flow-value">{{ formatAmount(getMarginData()?.margin_balance ?? getMarginData()?.financing_balance) }}</div>
          </div>
          <div class="flow-item">
            <div class="flow-label">融资买入</div>
            <div class="flow-value">{{ formatAmount(getMarginData()?.margin_buy ?? getMarginData()?.financing_buy) }}</div>
          </div>
          <div class="flow-item">
            <div class="flow-label">融券余额</div>
            <div class="flow-value">{{ formatAmount(getMarginData()?.short_balance ?? getMarginData()?.securities_balance) }}</div>
          </div>
          <div class="flow-item">
            <div class="flow-label">融券卖出</div>
            <div class="flow-value">{{ formatAmount(getMarginData()?.short_sell ?? getMarginData()?.securities_sell) }}</div>
          </div>
        </div>
      </div>

      <!-- 原始数据摘要 -->
      <div v-if="analysisResult.summary || analysisResult.analysis" class="section-card">
        <h3 class="section-title">分析摘要</h3>
        <div class="summary-text">{{ String(analysisResult.summary || analysisResult.analysis) }}</div>
      </div>
    </template>

    <!-- 无结果 -->
    <div v-if="!analysisResult && !loading && !error" class="empty-state">
      输入股票代码开始分析资金流向
    </div>

    <div v-if="loading" class="loading-state">正在分析资金流向...</div>
  </div>
</template>

<style scoped>
.capital-flow-view {
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

/* 查询面板 */
.query-panel {
  margin-bottom: 0;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 12px;
  align-items: end;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.form-action {
  display: flex;
  align-items: flex-end;
}

/* 指标网格 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.metric-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 14px 16px;
}

.metric-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
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
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border);
}

/* 资金流向网格 */
.flow-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.flow-item {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px 14px;
}

.flow-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.flow-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
}

/* 分析摘要 */
.summary-text {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  .flow-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .flow-grid {
    grid-template-columns: 1fr;
  }
}
</style>
