<script setup lang="ts">
import { ref, reactive } from 'vue'
import { configureDebate, getDebateHistory } from '@/services/api'
import type { DebateHistory } from '@/services/api'

/** 辩论配置参数 */
const config = reactive({
  rounds: 3,
  enable_prisoners_dilemma: true,
  enable_voting: true,
})

/** 配置保存状态 */
const saving = ref(false)
/** 配置保存消息 */
const saveMessage = ref<{ success: boolean; text: string } | null>(null)

/** 股票代码查询输入 */
const stockCodeInput = ref('')
/** 辩论历史数据 */
const debateHistory = ref<DebateHistory | null>(null)
/** 历史加载状态 */
const historyLoading = ref(false)
/** 历史错误 */
const historyError = ref<string | null>(null)

/** 保存辩论配置 */
async function handleSaveConfig(): Promise<void> {
  saving.value = true
  saveMessage.value = null
  try {
    const res = await configureDebate({
      rounds: config.rounds,
      enable_prisoners_dilemma: config.enable_prisoners_dilemma,
      enable_voting: config.enable_voting,
    })
    saveMessage.value = {
      success: res.success,
      text: res.message || '配置保存成功',
    }
  } catch (e) {
    saveMessage.value = {
      success: false,
      text: e instanceof Error ? e.message : '配置保存失败',
    }
  } finally {
    saving.value = false
  }
}

/** 查询辩论历史 */
async function searchDebateHistory(): Promise<void> {
  const code = stockCodeInput.value.trim()
  if (!code) return
  historyLoading.value = true
  historyError.value = null
  debateHistory.value = null
  try {
    const res = await getDebateHistory(code)
    debateHistory.value = res?.data ?? null
  } catch (e) {
    historyError.value = e instanceof Error ? e.message : '查询辩论历史失败'
  } finally {
    historyLoading.value = false
  }
}

/** 格式化合作度评分 */
function formatScore(val: number): string {
  return (val * 100).toFixed(1) + '%'
}

/** 合作度评分样式 */
function scoreClass(val: number): string {
  if (val >= 0.7) return 'value-positive'
  if (val >= 0.4) return 'value-warning'
  return 'value-negative'
}

/** 格式化 JSON */
function formatJson(data: unknown): string {
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}
</script>

<template>
  <div class="debate-config-view">
    <div class="page-header">
      <h2 class="page-title">博弈论配置</h2>
      <p class="page-desc">配置辩论参数，查看多空辩论历史和纳什均衡分析</p>
    </div>

    <!-- 辩论参数配置 -->
    <div class="section-card">
      <h3 class="section-title">辩论参数配置</h3>
      <div class="config-form">
        <div class="config-row">
          <label class="config-label">辩论轮数</label>
          <div class="config-control">
            <input
              v-model.number="config.rounds"
              type="range"
              min="1"
              max="5"
              step="1"
              class="range-input"
            />
            <span class="range-value mono">{{ config.rounds }}</span>
          </div>
        </div>
        <div class="config-row">
          <label class="config-label">启用囚徒困境</label>
          <div class="config-control">
            <button
              class="toggle-btn"
              :class="{ active: config.enable_prisoners_dilemma }"
              @click="config.enable_prisoners_dilemma = !config.enable_prisoners_dilemma"
            >
              {{ config.enable_prisoners_dilemma ? '已启用' : '已禁用' }}
            </button>
          </div>
        </div>
        <div class="config-row">
          <label class="config-label">启用投票</label>
          <div class="config-control">
            <button
              class="toggle-btn"
              :class="{ active: config.enable_voting }"
              @click="config.enable_voting = !config.enable_voting"
            >
              {{ config.enable_voting ? '已启用' : '已禁用' }}
            </button>
          </div>
        </div>
      </div>

      <div class="config-actions">
        <button class="btn-primary" :disabled="saving" @click="handleSaveConfig">
          {{ saving ? '保存中...' : '保存配置' }}
        </button>
      </div>

      <div v-if="saveMessage" class="save-message" :class="saveMessage.success ? 'msg-success' : 'msg-fail'">
        {{ saveMessage.text }}
      </div>
    </div>

    <!-- 辩论历史查询 -->
    <div class="section-card">
      <h3 class="section-title">辩论历史</h3>
      <div class="search-bar">
        <input
          v-model="stockCodeInput"
          class="input search-input"
          placeholder="输入股票代码，如 600519"
          @keyup.enter="searchDebateHistory"
        />
        <button
          class="btn-primary"
          :disabled="historyLoading || !stockCodeInput.trim()"
          @click="searchDebateHistory"
        >
          查询
        </button>
      </div>

      <div v-if="historyError" class="error-msg">{{ historyError }}</div>

      <!-- 辩论历史结果 -->
      <div v-if="debateHistory" class="history-result">
        <!-- 概览指标 -->
        <div class="overview-grid">
          <div class="overview-item">
            <div class="overview-label">股票代码</div>
            <div class="overview-value mono">{{ debateHistory.stock_code }}</div>
          </div>
          <div class="overview-item">
            <div class="overview-label">辩论轮数</div>
            <div class="overview-value mono">{{ debateHistory.rounds?.length ?? 0 }}</div>
          </div>
          <div class="overview-item">
            <div class="overview-label">合作度评分</div>
            <div class="overview-value" :class="scoreClass(debateHistory.cooperation_score)">
              {{ formatScore(debateHistory.cooperation_score) }}
            </div>
          </div>
        </div>

        <!-- 多轮辩论记录 -->
        <div v-if="debateHistory.rounds?.length" class="rounds-section">
          <h4 class="sub-title">辩论记录</h4>
          <div class="rounds-list">
            <div
              v-for="round in debateHistory.rounds"
              :key="round.round"
              class="round-card"
            >
              <div class="round-header">
                <span class="round-number">第 {{ round.round }} 轮</span>
              </div>
              <div class="round-body">
                <div class="argument argument-bull">
                  <span class="argument-label">多方观点</span>
                  <p class="argument-text">{{ round.bull_argument || '-' }}</p>
                </div>
                <div class="argument argument-bear">
                  <span class="argument-label">空方观点</span>
                  <p class="argument-text">{{ round.bear_argument || '-' }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 投票结果 -->
        <div v-if="debateHistory.vote_result" class="vote-section">
          <h4 class="sub-title">投票结果</h4>
          <pre class="json-content">{{ formatJson(debateHistory.vote_result) }}</pre>
        </div>

        <!-- 纳什均衡分析 -->
        <div v-if="debateHistory.nash_equilibrium" class="nash-section">
          <h4 class="sub-title">纳什均衡分析</h4>
          <pre class="json-content">{{ formatJson(debateHistory.nash_equilibrium) }}</pre>
        </div>
      </div>

      <div v-if="!debateHistory && !historyLoading && !historyError" class="empty-state">
        输入股票代码查看辩论历史
      </div>
    </div>

    <div v-if="historyLoading" class="loading-state">查询中...</div>
  </div>
</template>

<style scoped>
.debate-config-view {
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

.mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
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

.sub-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 8px;
}

/* 配置表单 */
.config-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 16px;
}

.config-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.config-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  min-width: 120px;
}

.config-control {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

/* 滑块 */
.range-input {
  flex: 1;
  max-width: 200px;
  accent-color: var(--color-accent);
  background: transparent;
}

.range-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-accent);
  min-width: 20px;
  text-align: center;
}

/* 切换按钮 */
.toggle-btn {
  padding: 4px 12px;
  border-radius: var(--radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg-primary);
  color: var(--color-text-muted);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.toggle-btn.active {
  background: rgba(37, 99, 235, 0.1);
  border-color: rgba(37, 99, 235, 0.3);
  color: var(--color-accent);
}

.config-actions {
  display: flex;
  gap: 8px;
}

/* 保存消息 */
.save-message {
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: var(--radius);
  font-size: 12px;
}

.msg-success {
  background: rgba(0, 185, 107, 0.08);
  border: 1px solid rgba(0, 185, 107, 0.2);
  color: var(--color-positive);
}

.msg-fail {
  background: rgba(245, 34, 45, 0.08);
  border: 1px solid rgba(245, 34, 45, 0.2);
  color: var(--color-negative);
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

/* 概览网格 */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.overview-item {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px 14px;
}

.overview-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.overview-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.value-warning {
  color: var(--color-warning);
}

/* 辩论轮次 */
.rounds-section {
  margin-bottom: 16px;
}

.rounds-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.round-card {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
}

.round-header {
  padding: 8px 14px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-hover);
}

.round-number {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.round-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
}

.argument {
  padding: 12px 14px;
}

.argument-bull {
  border-right: 1px solid var(--color-border);
}

.argument-label {
  display: inline-block;
  font-size: 11px;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: 2px;
  margin-bottom: 6px;
}

.argument-bull .argument-label {
  background: rgba(0, 185, 107, 0.12);
  color: var(--color-positive);
}

.argument-bear .argument-label {
  background: rgba(245, 34, 45, 0.12);
  color: var(--color-negative);
}

.argument-text {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin: 0;
}

/* JSON 内容 */
.vote-section,
.nash-section {
  margin-bottom: 12px;
}

.json-content {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  color: var(--color-text-secondary);
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
  margin: 0;
}

@media (max-width: 768px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
  .round-body {
    grid-template-columns: 1fr;
  }
  .argument-bull {
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }
  .search-input {
    max-width: none;
  }
}
</style>
