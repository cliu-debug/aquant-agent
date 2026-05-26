<script setup lang="ts">
import { ref, computed } from 'vue'
import { calculatePositionSizing, type PositionSizingParams } from '@/services/api'

/** 表单参数 */
const form = ref<{
  stock_code: string
  portfolio_value: number | null
  signal: string
  confidence: number | null
  risk_level: string
  stop_loss_pct: number | null
}>({
  stock_code: '',
  portfolio_value: null,
  signal: '买入',
  confidence: null,
  risk_level: '中等',
  stop_loss_pct: 5,
})

/** 计算结果 */
const result = ref<Record<string, unknown> | null>(null)
/** 加载状态 */
const loading = ref(false)
/** 错误信息 */
const error = ref<string | null>(null)

/** 表单是否可提交 */
const canSubmit = computed((): boolean => {
  return (
    form.value.stock_code.trim() !== '' &&
    form.value.portfolio_value != null &&
    form.value.portfolio_value > 0 &&
    form.value.confidence != null &&
    form.value.confidence >= 0 &&
    form.value.confidence <= 100 &&
    form.value.stop_loss_pct != null &&
    form.value.stop_loss_pct > 0
  )
})

/** 执行仓位计算 */
async function handleCalculate(): Promise<void> {
  if (!canSubmit.value) return
  loading.value = true
  error.value = null
  result.value = null
  try {
    const params: PositionSizingParams = {
      stock_code: form.value.stock_code.trim(),
      portfolio_value: form.value.portfolio_value!,
      signal: form.value.signal,
      confidence: form.value.confidence! / 100,
      risk_level: form.value.risk_level,
      stop_loss_pct: form.value.stop_loss_pct! / 100,
    }
    const res = await calculatePositionSizing(params)
    result.value = res?.data ?? res ?? null
  } catch (e) {
    error.value = e instanceof Error ? e.message : '仓位计算失败'
  } finally {
    loading.value = false
  }
}

/** 重置表单 */
function handleReset(): void {
  form.value = {
    stock_code: '',
    portfolio_value: null,
    signal: '买入',
    confidence: null,
    risk_level: '中等',
    stop_loss_pct: 5,
  }
  result.value = null
  error.value = null
}

/** 格式化金额 */
function formatMoney(val: unknown): string {
  if (val == null) return '-'
  const num = Number(val)
  if (isNaN(num)) return String(val)
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** 格式化百分比 */
function formatPct(val: unknown): string {
  if (val == null) return '-'
  const num = Number(val)
  if (isNaN(num)) return String(val)
  return (num * 100).toFixed(2) + '%'
}

/** 获取结果中的建议仓位 */
function getPositionSize(): Record<string, unknown> | null {
  if (!result.value) return null
  return (result.value.position ?? result.value.position_sizing ?? result.value) as Record<string, unknown> | null
}
</script>

<template>
  <div class="position-sizing-view">
    <div class="page-header">
      <h2 class="page-title">仓位计算</h2>
      <p class="page-desc">基于风险偏好和信号置信度，计算最优仓位大小及止损止盈价位</p>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <div class="content-grid">
      <!-- 输入面板 -->
      <div class="input-panel card">
        <h3 class="section-title">参数设置</h3>
        <div class="form-fields">
          <div class="form-field">
            <label class="field-label">股票代码</label>
            <input
              v-model="form.stock_code"
              class="input"
              placeholder="例如 600519.SH"
            />
          </div>
          <div class="form-field">
            <label class="field-label">账户资金（元）</label>
            <input
              v-model.number="form.portfolio_value"
              type="number"
              class="input"
              placeholder="例如 1000000"
              min="0"
              step="10000"
            />
          </div>
          <div class="form-field">
            <label class="field-label">交易信号</label>
            <select v-model="form.signal" class="input">
              <option value="买入">买入</option>
              <option value="卖出">卖出</option>
              <option value="持有">持有</option>
            </select>
          </div>
          <div class="form-field">
            <label class="field-label">信号置信度（0-100）</label>
            <input
              v-model.number="form.confidence"
              type="number"
              class="input"
              placeholder="例如 75"
              min="0"
              max="100"
              step="1"
            />
          </div>
          <div class="form-field">
            <label class="field-label">风险偏好</label>
            <select v-model="form.risk_level" class="input">
              <option value="保守">保守</option>
              <option value="中等">中等</option>
              <option value="激进">激进</option>
            </select>
          </div>
          <div class="form-field">
            <label class="field-label">止损比例（%）</label>
            <input
              v-model.number="form.stop_loss_pct"
              type="number"
              class="input"
              placeholder="例如 5"
              min="0.1"
              max="50"
              step="0.5"
            />
          </div>
        </div>
        <div class="form-actions">
          <button
            class="btn-primary"
            :disabled="loading || !canSubmit"
            @click="handleCalculate"
          >
            计算仓位
          </button>
          <button class="btn-secondary" @click="handleReset">重置</button>
        </div>
      </div>

      <!-- 结果面板 -->
      <div class="result-panel">
        <template v-if="result">
          <!-- 核心结果 -->
          <div class="result-core card">
            <h3 class="section-title">计算结果</h3>
            <div class="result-grid">
              <div class="result-item highlight">
                <div class="result-label">建议仓位比例</div>
                <div class="result-value accent">
                  {{ formatPct(getPositionSize()?.position_pct ?? getPositionSize()?.weight ?? getPositionSize()?.ratio) }}
                </div>
              </div>
              <div class="result-item highlight">
                <div class="result-label">建议投入金额</div>
                <div class="result-value accent">
                  {{ formatMoney(getPositionSize()?.position_value ?? getPositionSize()?.amount ?? getPositionSize()?.capital) }}
                </div>
              </div>
              <div class="result-item">
                <div class="result-label">建议股数</div>
                <div class="result-value">
                  {{ getPositionSize()?.shares ?? getPositionSize()?.quantity ?? '-' }}
                </div>
              </div>
              <div class="result-item">
                <div class="result-label">单股风险金额</div>
                <div class="result-value">
                  {{ formatMoney(getPositionSize()?.risk_amount ?? getPositionSize()?.risk_per_share) }}
                </div>
              </div>
            </div>
          </div>

          <!-- 止损止盈 -->
          <div class="stop-profit-card card">
            <h3 class="section-title">止损止盈</h3>
            <div class="sp-grid">
              <div class="sp-item sp-loss">
                <div class="sp-label">止损价</div>
                <div class="sp-value value-negative">
                  {{ formatMoney(getPositionSize()?.stop_loss_price ?? getPositionSize()?.stop_loss) }}
                </div>
                <div class="sp-pct">
                  {{ formatPct(getPositionSize()?.stop_loss_pct ?? getPositionSize()?.stop_loss_ratio) }}
                </div>
              </div>
              <div class="sp-divider"></div>
              <div class="sp-item sp-profit">
                <div class="sp-label">止盈价</div>
                <div class="sp-value value-positive">
                  {{ formatMoney(getPositionSize()?.take_profit_price ?? getPositionSize()?.take_profit) }}
                </div>
                <div class="sp-pct">
                  {{ formatPct(getPositionSize()?.take_profit_pct ?? getPositionSize()?.take_profit_ratio) }}
                </div>
              </div>
            </div>
          </div>

          <!-- 风险提示 -->
          <div v-if="result.risk_warning || result.warning" class="warning-card">
            <div class="warning-header">风险提示</div>
            <div class="warning-text">{{ String(result.risk_warning || result.warning) }}</div>
          </div>

          <!-- 原始数据 -->
          <div v-if="result.reasoning || result.explanation" class="section-card">
            <h3 class="section-title">计算说明</h3>
            <div class="explanation-text">{{ String(result.reasoning || result.explanation) }}</div>
          </div>
        </template>

        <!-- 无结果 -->
        <div v-if="!result && !loading" class="empty-placeholder">
          <div class="empty-icon">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2"/>
              <path d="M3 9h18"/>
              <path d="M9 21V9"/>
            </svg>
          </div>
          <div class="empty-text">设置参数后点击"计算仓位"查看结果</div>
        </div>

        <div v-if="loading" class="loading-state">正在计算仓位...</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.position-sizing-view {
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

/* 内容网格 */
.content-grid {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 16px;
  align-items: start;
}

/* 输入面板 */
.input-panel {
  position: sticky;
  top: 20px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 14px;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
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

.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

/* 结果面板 */
.result-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 结果网格 */
.result-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.result-item {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px 14px;
}

.result-item.highlight {
  border-color: rgba(37, 99, 235, 0.3);
  background: rgba(37, 99, 235, 0.04);
}

.result-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.result-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
}

.result-value.accent {
  color: var(--color-accent);
}

/* 止损止盈 */
.sp-grid {
  display: grid;
  grid-template-columns: 1fr 1px 1fr;
  gap: 0;
  align-items: center;
}

.sp-divider {
  width: 1px;
  height: 60px;
  background: var(--color-border);
}

.sp-item {
  text-align: center;
  padding: 12px;
}

.sp-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.sp-value {
  font-size: 22px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.sp-pct {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 4px;
}

/* 风险提示 */
.warning-card {
  background: rgba(250, 173, 20, 0.06);
  border: 1px solid rgba(250, 173, 20, 0.2);
  border-radius: var(--radius);
  padding: 14px 16px;
}

.warning-header {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-warning);
  margin-bottom: 6px;
}

.warning-text {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* 区块卡片 */
.section-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
}

.explanation-text {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.7;
  white-space: pre-wrap;
}

/* 空占位 */
.empty-placeholder {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  color: var(--color-text-muted);
  margin-bottom: 12px;
}

.empty-text {
  font-size: 14px;
  color: var(--color-text-muted);
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
  .input-panel {
    position: static;
  }
}

@media (max-width: 768px) {
  .result-grid {
    grid-template-columns: 1fr;
  }
}
</style>
