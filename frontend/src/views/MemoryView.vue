<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getMemoryProfile, getStockMemory } from '@/services/api'
import type { MemoryProfile, StockMemory } from '@/services/api'

/** 用户投资画像 */
const profile = ref<MemoryProfile | null>(null)
/** 加载状态 */
const loading = ref(false)
/** 错误信息 */
const error = ref<string | null>(null)

/** 股票代码查询输入 */
const stockCodeInput = ref('')
/** 股票记忆数据 */
const stockMemory = ref<StockMemory | null>(null)
/** 股票记忆加载状态 */
const memoryLoading = ref(false)
/** 股票记忆错误 */
const memoryError = ref<string | null>(null)

/** 加载用户投资画像 */
async function loadProfile(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const res = await getMemoryProfile()
    profile.value = res?.data ?? null
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载投资画像失败'
  } finally {
    loading.value = false
  }
}

/** 查询股票历史记忆 */
async function searchStockMemory(): Promise<void> {
  const code = stockCodeInput.value.trim()
  if (!code) return
  memoryLoading.value = true
  memoryError.value = null
  stockMemory.value = null
  try {
    const res = await getStockMemory(code)
    stockMemory.value = res?.data ?? null
  } catch (e) {
    memoryError.value = e instanceof Error ? e.message : '查询股票记忆失败'
  } finally {
    memoryLoading.value = false
  }
}

/** 格式化置信度 */
function formatConfidence(val: number): string {
  return (val * 100).toFixed(1) + '%'
}

/** 置信度样式类 */
function confidenceClass(val: number): string {
  if (val >= 0.7) return 'value-positive'
  if (val >= 0.4) return 'value-warning'
  return 'value-negative'
}

onMounted(loadProfile)
</script>

<template>
  <div class="memory-view">
    <div class="page-header">
      <h2 class="page-title">记忆系统</h2>
      <p class="page-desc">查看投资画像和股票历史分析记忆</p>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <!-- 投资画像 -->
    <div class="section-card">
      <h3 class="section-title">用户投资画像</h3>
      <div v-if="profile" class="profile-grid">
        <div class="profile-item">
          <div class="profile-label">偏好行业</div>
          <div class="profile-value">
            <span
              v-for="ind in profile.preferred_industries"
              :key="ind"
              class="industry-tag"
            >
              {{ ind }}
            </span>
            <span v-if="!profile.preferred_industries?.length" class="empty-tag">暂无</span>
          </div>
        </div>
        <div class="profile-item">
          <div class="profile-label">风险偏好</div>
          <div class="profile-value">{{ profile.risk_preference || '-' }}</div>
        </div>
        <div class="profile-item">
          <div class="profile-label">持仓周期</div>
          <div class="profile-value">{{ profile.holding_period || '-' }}</div>
        </div>
        <div class="profile-item">
          <div class="profile-label">分析次数</div>
          <div class="profile-value mono">{{ profile.analysis_count ?? 0 }}</div>
        </div>
      </div>
      <div v-else-if="!loading" class="empty-state">暂无投资画像数据</div>
    </div>

    <!-- 股票历史记忆查询 -->
    <div class="section-card">
      <h3 class="section-title">股票历史记忆</h3>
      <div class="search-bar">
        <input
          v-model="stockCodeInput"
          class="input search-input"
          placeholder="输入股票代码，如 600519"
          @keyup.enter="searchStockMemory"
        />
        <button
          class="btn-primary"
          :disabled="memoryLoading || !stockCodeInput.trim()"
          @click="searchStockMemory"
        >
          查询
        </button>
      </div>

      <div v-if="memoryError" class="error-msg">{{ memoryError }}</div>

      <!-- 查询结果 -->
      <div v-if="stockMemory" class="memory-result">
        <div class="memory-header">
          <span class="memory-stock">{{ stockMemory.stock_code }}</span>
          <span class="memory-name">{{ stockMemory.stock_name }}</span>
          <span class="memory-count">共 {{ stockMemory.memories?.length ?? 0 }} 条记忆</span>
        </div>

        <div v-if="stockMemory.memories?.length" class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>日期</th>
                <th>信号</th>
                <th>置信度</th>
                <th>摘要</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(mem, idx) in stockMemory.memories" :key="idx">
                <td class="mono">{{ mem.date || '-' }}</td>
                <td>
                  <span
                    class="signal-tag"
                    :class="{
                      'signal-buy': mem.signal === 'buy',
                      'signal-sell': mem.signal === 'sell',
                      'signal-hold': mem.signal === 'hold',
                    }"
                  >
                    {{ mem.signal || '-' }}
                  </span>
                </td>
                <td :class="confidenceClass(mem.confidence)" class="mono">
                  {{ formatConfidence(mem.confidence) }}
                </td>
                <td class="cell-summary">{{ mem.summary || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state">该股票暂无历史记忆</div>
      </div>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-if="memoryLoading" class="loading-state">查询中...</div>
  </div>
</template>

<style scoped>
.memory-view {
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

/* 投资画像网格 */
.profile-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.profile-item {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px 14px;
}

.profile-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.profile-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-primary);
}

.mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
}

/* 行业标签 */
.industry-tag {
  display: inline-block;
  padding: 2px 8px;
  margin: 2px 4px 2px 0;
  background: rgba(37, 99, 235, 0.1);
  color: var(--color-accent);
  border-radius: 2px;
  font-size: 12px;
}

.empty-tag {
  color: var(--color-text-muted);
  font-size: 13px;
}

/* 搜索栏 */
.search-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.search-input {
  flex: 1;
  max-width: 300px;
}

/* 记忆结果 */
.memory-result {
  margin-top: 12px;
}

.memory-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.memory-stock {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-accent);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.memory-name {
  font-size: 14px;
  color: var(--color-text-primary);
}

.memory-count {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-left: auto;
}

/* 信号标签 */
.signal-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
}

.signal-buy {
  background: rgba(0, 185, 107, 0.12);
  color: var(--color-positive);
}

.signal-sell {
  background: rgba(245, 34, 45, 0.12);
  color: var(--color-negative);
}

.signal-hold {
  background: rgba(250, 173, 20, 0.12);
  color: var(--color-warning);
}

.value-warning {
  color: var(--color-warning);
}

.cell-summary {
  max-width: 300px;
  white-space: normal;
  line-height: 1.4;
  font-size: 12px;
}

@media (max-width: 768px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
  .search-input {
    max-width: none;
  }
}
</style>
