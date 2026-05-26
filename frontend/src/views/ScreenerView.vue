<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getScreenerPresets,
  screenerScan,
  type ScreenerPreset,
} from '@/services/api'

const presets = ref<ScreenerPreset[]>([])
const loading = ref(false)
const scanning = ref(false)
const error = ref<string | null>(null)
const selectedPreset = ref<string>('')
const scanResult = ref<Record<string, unknown> | null>(null)

async function loadPresets() {
  loading.value = true
  try {
    const res = await getScreenerPresets()
    presets.value = res.presets || []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载预设失败'
  } finally {
    loading.value = false
  }
}

async function handleScan() {
  if (!selectedPreset.value) return
  scanning.value = true
  error.value = null
  scanResult.value = null
  try {
    scanResult.value = await screenerScan({ preset_name: selectedPreset.value })
  } catch (e) {
    error.value = e instanceof Error ? e.message : '扫描失败'
  } finally {
    scanning.value = false
  }
}

/** 从扫描结果提取股票列表 */
function getStockList(): Array<Record<string, unknown>> {
  if (!scanResult.value) return []
  const data = scanResult.value
  if (Array.isArray(data.stocks)) return data.stocks
  if (Array.isArray(data.results)) return data.results
  if (Array.isArray(data.data)) return data.data
  return []
}

onMounted(loadPresets)
</script>

<template>
  <div class="screener-view">
    <div class="page-header">
      <h2 class="page-title">选股</h2>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <!-- 预设策略 -->
    <div class="card preset-section">
      <h3 class="section-title">预设策略</h3>
      <div v-if="loading" class="loading-state" style="padding: 20px">加载中...</div>
      <div v-else-if="presets.length === 0" class="empty-hint">暂无预设策略</div>
      <div v-else class="preset-list">
        <div
          v-for="preset in presets"
          :key="preset.name"
          class="preset-item"
          :class="{ selected: selectedPreset === preset.name }"
          @click="selectedPreset = preset.name"
        >
          <div class="preset-name">{{ preset.name }}</div>
          <div class="preset-desc">{{ preset.description }}</div>
        </div>
      </div>

      <div class="scan-action">
        <button
          class="btn-primary"
          @click="handleScan"
          :disabled="!selectedPreset || scanning"
        >
          {{ scanning ? '扫描中...' : '开始扫描' }}
        </button>
      </div>
    </div>

    <!-- 扫描结果 -->
    <div v-if="scanResult" class="card result-section">
      <h3 class="section-title">扫描结果</h3>
      <div v-if="getStockList().length === 0" class="empty-hint">未找到符合条件的股票</div>
      <div v-else class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>股票代码</th>
              <th>股票名称</th>
              <th>行业</th>
              <th>信号</th>
              <th>评分</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(stock, i) in getStockList()" :key="i">
              <td class="code-cell">{{ stock.stock_code || stock.code || '-' }}</td>
              <td>{{ stock.stock_name || stock.name || '-' }}</td>
              <td>{{ stock.industry || '-' }}</td>
              <td>
                <span
                  class="signal-tag"
                  :class="{
                    'signal-positive': String(stock.signal || '').includes('buy'),
                    'signal-negative': String(stock.signal || '').includes('sell'),
                    'signal-neutral': !String(stock.signal || '').includes('buy') && !String(stock.signal || '').includes('sell'),
                  }"
                >
                  {{ stock.signal || '-' }}
                </span>
              </td>
              <td>{{ stock.score || stock.confidence || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.screener-view {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 14px;
}

.preset-section {
  margin-bottom: 16px;
}

.preset-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.preset-item {
  padding: 12px 14px;
  background: var(--color-bg-input);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  cursor: pointer;
  transition: all 0.15s;
}

.preset-item:hover {
  border-color: var(--color-accent);
}

.preset-item.selected {
  border-color: var(--color-accent);
  background: rgba(37, 99, 235, 0.08);
}

.preset-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.preset-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.scan-action {
  display: flex;
  justify-content: flex-end;
}

.result-section {
  margin-top: 16px;
}

.code-cell {
  color: var(--color-accent);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.signal-tag {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 2px;
  font-size: 12px;
  font-weight: 500;
}

.signal-positive {
  color: var(--color-positive);
  background: rgba(0, 185, 107, 0.1);
}

.signal-negative {
  color: var(--color-negative);
  background: rgba(245, 34, 45, 0.1);
}

.signal-neutral {
  color: var(--color-text-secondary);
  background: rgba(123, 132, 153, 0.1);
}

.empty-hint {
  color: var(--color-text-muted);
  font-size: 13px;
  padding: 20px 0;
}
</style>
