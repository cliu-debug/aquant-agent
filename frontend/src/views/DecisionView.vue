<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getPendingDecisions,
  getDecisionHistory,
  executeDecision,
  cancelDecision,
  reviewDecision,
} from '@/services/api'

/** 待执行决策列表 */
const pendingDecisions = ref<Array<Record<string, unknown>>>([])
/** 决策历史列表 */
const decisionHistory = ref<Array<Record<string, unknown>>>([])
/** 加载状态 */
const loading = ref(false)
/** 错误信息 */
const error = ref<string | null>(null)
/** 当前激活的标签页 */
const activeTab = ref<'pending' | 'history'>('pending')
/** 复盘弹窗可见性 */
const reviewDialogVisible = ref(false)
/** 当前复盘的决策ID */
const reviewingDecisionId = ref<string>('')
/** 复盘表单 */
const reviewForm = ref<{ outcome: string; actual_pnl: number }>({
  outcome: '',
  actual_pnl: 0,
})
/** 取消弹窗可见性 */
const cancelDialogVisible = ref(false)
/** 当前取消的决策ID */
const cancelingDecisionId = ref<string>('')
/** 取消原因 */
const cancelReason = ref('')
/** 操作中状态 */
const actionLoading = ref(false)

/** 加载待执行决策 */
async function loadPendingDecisions(): Promise<void> {
  try {
    const res = await getPendingDecisions()
    pendingDecisions.value = res?.data ?? res?.decisions ?? (Array.isArray(res) ? res : [])
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载待执行决策失败'
  }
}

/** 加载决策历史 */
async function loadDecisionHistory(): Promise<void> {
  try {
    const res = await getDecisionHistory()
    decisionHistory.value = res?.data ?? res?.decisions ?? (Array.isArray(res) ? res : [])
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载决策历史失败'
  }
}

/** 加载全部数据 */
async function loadAll(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    await Promise.all([loadPendingDecisions(), loadDecisionHistory()])
  } finally {
    loading.value = false
  }
}

/** 执行决策 */
async function handleExecute(decisionId: string): Promise<void> {
  actionLoading.value = true
  try {
    await executeDecision(decisionId)
    await loadAll()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '执行决策失败'
  } finally {
    actionLoading.value = false
  }
}

/** 打开取消弹窗 */
function openCancelDialog(decisionId: string): void {
  cancelingDecisionId.value = decisionId
  cancelReason.value = ''
  cancelDialogVisible.value = true
}

/** 确认取消决策 */
async function handleCancel(): Promise<void> {
  actionLoading.value = true
  try {
    await cancelDecision(cancelingDecisionId.value, cancelReason.value)
    cancelDialogVisible.value = false
    await loadAll()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '取消决策失败'
  } finally {
    actionLoading.value = false
  }
}

/** 打开复盘弹窗 */
function openReviewDialog(decisionId: string): void {
  reviewingDecisionId.value = decisionId
  reviewForm.value = { outcome: '', actual_pnl: 0 }
  reviewDialogVisible.value = true
}

/** 提交复盘 */
async function handleReview(): Promise<void> {
  if (!reviewForm.value.outcome) return
  actionLoading.value = true
  try {
    await reviewDecision(
      reviewingDecisionId.value,
      reviewForm.value.outcome,
      reviewForm.value.actual_pnl
    )
    reviewDialogVisible.value = false
    await loadAll()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '复盘提交失败'
  } finally {
    actionLoading.value = false
  }
}

/** 获取决策状态标签样式 */
function statusClass(status: string): string {
  const s = String(status).toLowerCase()
  if (s === 'executed' || s === 'completed') return 'status-success'
  if (s === 'cancelled') return 'status-cancelled'
  if (s === 'pending') return 'status-pending'
  if (s === 'reviewed') return 'status-reviewed'
  return ''
}

/** 格式化时间 */
function formatTime(val: unknown): string {
  return String(val || '').substring(0, 16).replace('T', ' ')
}

onMounted(loadAll)
</script>

<template>
  <div class="decision-view">
    <div class="page-header">
      <h2 class="page-title">决策中心</h2>
      <p class="page-desc">管理投资决策的执行、取消与复盘，追踪决策全生命周期</p>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <!-- 标签页切换 -->
    <div class="tab-bar">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'pending' }"
        @click="activeTab = 'pending'"
      >
        待执行决策
        <span v-if="pendingDecisions.length" class="tab-badge">{{ pendingDecisions.length }}</span>
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'history' }"
        @click="activeTab = 'history'"
      >
        决策历史
      </button>
    </div>

    <!-- 待执行决策列表 -->
    <div v-if="activeTab === 'pending'" class="section-card">
      <div v-if="pendingDecisions.length === 0 && !loading" class="empty-state">
        暂无待执行决策
      </div>
      <div v-else class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>决策ID</th>
              <th>股票</th>
              <th>信号</th>
              <th>置信度</th>
              <th>建议操作</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in pendingDecisions" :key="String(item.id)">
              <td class="mono">{{ String(item.id || '').substring(0, 8) }}</td>
              <td>{{ String(item.stock_name || item.stock_code || '-') }}</td>
              <td>
                <span class="signal-tag" :class="String(item.signal) === '买入' ? 'signal-buy' : String(item.signal) === '卖出' ? 'signal-sell' : 'signal-hold'">
                  {{ String(item.signal || '-') }}
                </span>
              </td>
              <td>{{ item.confidence != null ? Number(item.confidence).toFixed(1) + '%' : '-' }}</td>
              <td>{{ String(item.action || item.proposal || '-') }}</td>
              <td>{{ formatTime(item.created_at) }}</td>
              <td class="action-cell">
                <button
                  class="btn-primary btn-sm"
                  :disabled="actionLoading"
                  @click="handleExecute(String(item.id))"
                >
                  执行
                </button>
                <button
                  class="btn-danger btn-sm"
                  :disabled="actionLoading"
                  @click="openCancelDialog(String(item.id))"
                >
                  取消
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 决策历史列表 -->
    <div v-if="activeTab === 'history'" class="section-card">
      <div v-if="decisionHistory.length === 0 && !loading" class="empty-state">
        暂无决策历史
      </div>
      <div v-else class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>决策ID</th>
              <th>股票</th>
              <th>信号</th>
              <th>状态</th>
              <th>执行时间</th>
              <th>复盘</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in decisionHistory" :key="String(item.id)">
              <td class="mono">{{ String(item.id || '').substring(0, 8) }}</td>
              <td>{{ String(item.stock_name || item.stock_code || '-') }}</td>
              <td>
                <span class="signal-tag" :class="String(item.signal) === '买入' ? 'signal-buy' : String(item.signal) === '卖出' ? 'signal-sell' : 'signal-hold'">
                  {{ String(item.signal || '-') }}
                </span>
              </td>
              <td>
                <span class="status-tag" :class="statusClass(String(item.status))">
                  {{ String(item.status || '-') }}
                </span>
              </td>
              <td>{{ formatTime(item.executed_at || item.created_at) }}</td>
              <td>{{ item.reviewed ? '已复盘' : '未复盘' }}</td>
              <td class="action-cell">
                <button
                  v-if="!item.reviewed && (item.status === 'executed' || item.status === 'completed')"
                  class="btn-secondary btn-sm"
                  :disabled="actionLoading"
                  @click="openReviewDialog(String(item.id))"
                >
                  复盘
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 取消弹窗 -->
    <div v-if="cancelDialogVisible" class="dialog-overlay" @click.self="cancelDialogVisible = false">
      <div class="dialog-box">
        <h3 class="dialog-title">取消决策</h3>
        <div class="form-field">
          <label class="field-label">取消原因</label>
          <textarea
            v-model="cancelReason"
            class="input textarea"
            placeholder="请输入取消原因（可选）"
            rows="3"
          ></textarea>
        </div>
        <div class="dialog-actions">
          <button class="btn-secondary" @click="cancelDialogVisible = false">返回</button>
          <button class="btn-danger" :disabled="actionLoading" @click="handleCancel">确认取消</button>
        </div>
      </div>
    </div>

    <!-- 复盘弹窗 -->
    <div v-if="reviewDialogVisible" class="dialog-overlay" @click.self="reviewDialogVisible = false">
      <div class="dialog-box">
        <h3 class="dialog-title">决策复盘</h3>
        <div class="form-field">
          <label class="field-label">实际结果</label>
          <select v-model="reviewForm.outcome" class="input">
            <option value="">请选择</option>
            <option value="profit">盈利</option>
            <option value="loss">亏损</option>
            <option value="breakeven">持平</option>
          </select>
        </div>
        <div class="form-field">
          <label class="field-label">实际盈亏金额</label>
          <input
            v-model.number="reviewForm.actual_pnl"
            type="number"
            class="input"
            placeholder="0.00"
            step="0.01"
          />
        </div>
        <div class="dialog-actions">
          <button class="btn-secondary" @click="reviewDialogVisible = false">返回</button>
          <button
            class="btn-primary"
            :disabled="actionLoading || !reviewForm.outcome"
            @click="handleReview"
          >
            提交复盘
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
  </div>
</template>

<style scoped>
.decision-view {
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

/* 标签页 */
.tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--color-border);
}

.tab-btn {
  padding: 10px 20px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--color-text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.tab-btn:hover {
  color: var(--color-text-primary);
}

.tab-btn.active {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
}

.tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: var(--color-accent);
  color: #fff;
  border-radius: 9px;
  font-size: 11px;
  font-weight: 600;
}

/* 区块卡片 */
.section-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
}

/* 信号标签 */
.signal-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 12px;
  font-weight: 600;
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

/* 状态标签 */
.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 12px;
  font-weight: 500;
}

.status-pending {
  background: rgba(250, 173, 20, 0.12);
  color: var(--color-warning);
}

.status-success {
  background: rgba(0, 185, 107, 0.12);
  color: var(--color-positive);
}

.status-cancelled {
  background: rgba(122, 132, 153, 0.12);
  color: var(--color-text-muted);
}

.status-reviewed {
  background: rgba(37, 99, 235, 0.12);
  color: var(--color-accent);
}

/* 操作按钮 */
.action-cell {
  display: flex;
  gap: 6px;
  align-items: center;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}

.mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
}

/* 弹窗 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog-box {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 24px;
  width: 400px;
  max-width: 90vw;
}

.dialog-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.field-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.textarea {
  resize: vertical;
  min-height: 60px;
  font-family: inherit;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

@media (max-width: 768px) {
  .action-cell {
    flex-direction: column;
    gap: 4px;
  }
}
</style>
