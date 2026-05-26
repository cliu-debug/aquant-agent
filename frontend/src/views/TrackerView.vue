<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getTrackers,
  createTracker,
  deactivateTracker,
  deleteTracker,
  getSignalTimeline,
  type TrackerItem,
  type SignalChange,
  type CreateTrackerRequest,
} from '@/services/api'

const trackers = ref<TrackerItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

/** 创建追踪对话框 */
const showCreateDialog = ref(false)
const createForm = ref<CreateTrackerRequest>({
  stock_code: '',
  stock_name: '',
})

/** 追踪详情 */
const selectedTracker = ref<TrackerItem | null>(null)
const timeline = ref<SignalChange[]>([])
const timelineLoading = ref(false)

async function loadTrackers() {
  loading.value = true
  error.value = null
  try {
    const res = await getTrackers(false)
    trackers.value = res.data || []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!createForm.value.stock_code || !createForm.value.stock_name) return
  try {
    await createTracker(createForm.value)
    showCreateDialog.value = false
    createForm.value = { stock_code: '', stock_name: '' }
    await loadTrackers()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '创建失败'
  }
}

async function handleDeactivate(trackerId: string) {
  try {
    await deactivateTracker(trackerId)
    await loadTrackers()
    if (selectedTracker.value?.id === trackerId) {
      selectedTracker.value = null
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '操作失败'
  }
}

async function handleDelete(trackerId: string) {
  try {
    await deleteTracker(trackerId)
    await loadTrackers()
    if (selectedTracker.value?.id === trackerId) {
      selectedTracker.value = null
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  }
}

async function viewDetail(tracker: TrackerItem) {
  selectedTracker.value = tracker
  timelineLoading.value = true
  try {
    const res = await getSignalTimeline(tracker.id)
    timeline.value = res.data || []
  } catch {
    timeline.value = []
  } finally {
    timelineLoading.value = false
  }
}

/** 计算追踪天数 */
function getTrackingDays(createdAt: string): string {
  if (!createdAt) return '-'
  const created = new Date(createdAt)
  const now = new Date()
  const days = Math.floor((now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24))
  return `${days}天`
}

/** 信号颜色映射 */
function getSignalColor(signal: string): string {
  const map: Record<string, string> = {
    strong_buy: 'var(--color-positive)',
    buy: 'var(--color-positive)',
    hold: 'var(--color-text-secondary)',
    sell: 'var(--color-negative)',
    strong_sell: 'var(--color-negative)',
  }
  return map[signal] || 'var(--color-text-secondary)'
}

/** 信号文字映射 */
function getSignalText(signal: string): string {
  const map: Record<string, string> = {
    strong_buy: '强烈买入',
    buy: '买入',
    hold: '持有',
    sell: '卖出',
    strong_sell: '强烈卖出',
  }
  return map[signal] || signal
}

onMounted(loadTrackers)
</script>

<template>
  <div class="tracker-view">
    <div class="page-header">
      <h2 class="page-title">追踪中心</h2>
      <button class="btn-primary" @click="showCreateDialog = true">创建追踪</button>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <div v-if="loading" class="loading-state">加载中...</div>

    <div v-else-if="trackers.length === 0" class="empty-state">暂无追踪记录</div>

    <div v-else class="content-layout">
      <!-- 追踪列表 -->
      <div class="tracker-list card">
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>股票代码</th>
                <th>股票名称</th>
                <th>状态</th>
                <th>追踪天数</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="tracker in trackers"
                :key="tracker.id"
                :class="{ selected: selectedTracker?.id === tracker.id }"
                @click="viewDetail(tracker)"
                style="cursor: pointer"
              >
                <td class="code-cell">{{ tracker.stock_code }}</td>
                <td>{{ tracker.stock_name }}</td>
                <td>
                  <span class="status-tag" :class="tracker.active ? 'status-active' : 'status-inactive'">
                    {{ tracker.active ? '追踪中' : '已停止' }}
                  </span>
                </td>
                <td>{{ getTrackingDays(tracker.created_at) }}</td>
                <td class="action-cell">
                  <button v-if="tracker.active" class="btn-secondary btn-sm" @click.stop="handleDeactivate(tracker.id)">停止</button>
                  <button class="btn-danger btn-sm" @click.stop="handleDelete(tracker.id)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 追踪详情 -->
      <div v-if="selectedTracker" class="tracker-detail card">
        <h3 class="section-title">
          {{ selectedTracker.stock_name }} ({{ selectedTracker.stock_code }})
        </h3>

        <!-- 投资逻辑 -->
        <div v-if="selectedTracker.thesis" class="thesis-section">
          <h4 class="sub-title">投资逻辑</h4>
          <div v-if="selectedTracker.thesis.reasons?.length" class="thesis-block">
            <span class="thesis-label">看多理由:</span>
            <ul class="thesis-list">
              <li v-for="(r, i) in selectedTracker.thesis.reasons" :key="i">{{ r }}</li>
            </ul>
          </div>
          <div v-if="selectedTracker.thesis.watch_indicators?.length" class="thesis-block">
            <span class="thesis-label">关注指标:</span>
            <ul class="thesis-list">
              <li v-for="(ind, i) in selectedTracker.thesis.watch_indicators" :key="i">{{ ind }}</li>
            </ul>
          </div>
          <div v-if="selectedTracker.thesis.exit_conditions?.length" class="thesis-block">
            <span class="thesis-label">退出条件:</span>
            <ul class="thesis-list">
              <li v-for="(c, i) in selectedTracker.thesis.exit_conditions" :key="i">{{ c }}</li>
            </ul>
          </div>
          <div v-if="selectedTracker.thesis.stop_loss_price" class="thesis-block">
            <span class="thesis-label">止损价:</span>
            <span class="thesis-value">{{ selectedTracker.thesis.stop_loss_price }}</span>
          </div>
          <div v-if="selectedTracker.thesis.profit_target_price" class="thesis-block">
            <span class="thesis-label">目标价:</span>
            <span class="thesis-value">{{ selectedTracker.thesis.profit_target_price }}</span>
          </div>
        </div>

        <!-- 信号时间线 -->
        <div class="timeline-section">
          <h4 class="sub-title">信号时间线</h4>
          <div v-if="timelineLoading" class="loading-state" style="padding: 20px">加载中...</div>
          <div v-else-if="timeline.length === 0" class="empty-hint">暂无信号记录</div>
          <div v-else class="timeline-list">
            <div v-for="event in timeline" :key="event.id" class="timeline-item">
              <div class="timeline-dot" :style="{ background: getSignalColor(event.signal) }"></div>
              <div class="timeline-content">
                <span class="timeline-time">{{ event.timestamp }}</span>
                <span class="timeline-signal" :style="{ color: getSignalColor(event.signal) }">
                  {{ getSignalText(event.signal) }}
                </span>
                <span v-if="event.confidence" class="timeline-confidence">
                  置信度 {{ event.confidence }}%
                </span>
                <span v-if="event.price" class="timeline-price">
                  价格 {{ event.price }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建追踪对话框 -->
    <Transition name="fade">
      <div v-if="showCreateDialog" class="dialog-overlay" @click.self="showCreateDialog = false">
        <div class="dialog card">
          <h3 class="section-title">创建追踪</h3>
          <div class="dialog-form">
            <div class="form-field">
              <label class="field-label">股票代码</label>
              <input v-model="createForm.stock_code" placeholder="600519.SH" class="input" />
            </div>
            <div class="form-field">
              <label class="field-label">股票名称</label>
              <input v-model="createForm.stock_name" placeholder="贵州茅台" class="input" />
            </div>
          </div>
          <div class="dialog-actions">
            <button class="btn-secondary" @click="showCreateDialog = false">取消</button>
            <button class="btn-primary" @click="handleCreate">确认</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.tracker-view {
  padding: 20px;
  max-width: 1100px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.sub-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 10px;
}

.content-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.code-cell {
  color: var(--color-accent);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 12px;
  font-weight: 500;
}

.status-active {
  color: var(--color-positive);
  background: rgba(0, 185, 107, 0.1);
}

.status-inactive {
  color: var(--color-text-muted);
  background: rgba(74, 81, 104, 0.1);
}

.action-cell {
  display: flex;
  gap: 6px;
}

.btn-sm {
  padding: 3px 8px;
  font-size: 12px;
}

tr.selected td {
  background: rgba(37, 99, 235, 0.08);
}

/* 投资逻辑 */
.thesis-section {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
}

.thesis-block {
  margin-bottom: 8px;
}

.thesis-label {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-right: 8px;
}

.thesis-value {
  font-size: 13px;
  color: var(--color-text-primary);
}

.thesis-list {
  margin: 4px 0 0 0;
  padding-left: 16px;
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.8;
}

/* 信号时间线 */
.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.timeline-item {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  border-left: 2px solid var(--color-border);
  padding-left: 14px;
  position: relative;
}

.timeline-dot {
  position: absolute;
  left: -5px;
  top: 12px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.timeline-content {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.timeline-time {
  font-size: 12px;
  color: var(--color-text-muted);
  font-variant-numeric: tabular-nums;
}

.timeline-signal {
  font-size: 13px;
  font-weight: 600;
}

.timeline-confidence,
.timeline-price {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.empty-hint {
  color: var(--color-text-muted);
  font-size: 13px;
  padding: 20px 0;
}

/* 对话框 */
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.dialog {
  width: 400px;
  max-width: 90vw;
}

.dialog-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
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

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 768px) {
  .content-layout { grid-template-columns: 1fr; }
}
</style>
