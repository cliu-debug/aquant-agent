<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  getSchedulerStatus,
  startScheduler,
  stopScheduler,
} from '@/services/api'

/** 调度器状态数据 */
const schedulerStatus = ref<Record<string, unknown> | null>(null)
/** 加载状态 */
const loading = ref(false)
/** 错误信息 */
const error = ref<string | null>(null)
/** 操作中状态 */
const actionLoading = ref(false)

/** 调度任务列表（类型安全） */
const schedulerJobs = computed((): Array<Record<string, unknown>> => {
  if (!schedulerStatus.value) return []
  const jobs = schedulerStatus.value.jobs ?? schedulerStatus.value.tasks
  if (!Array.isArray(jobs)) return []
  return jobs as Array<Record<string, unknown>>
})

/** 加载调度器状态 */
async function loadStatus(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const res = await getSchedulerStatus()
    schedulerStatus.value = res?.data ?? res ?? null
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载调度器状态失败'
  } finally {
    loading.value = false
  }
}

/** 启动调度器 */
async function handleStart(): Promise<void> {
  actionLoading.value = true
  error.value = null
  try {
    await startScheduler()
    await loadStatus()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '启动调度器失败'
  } finally {
    actionLoading.value = false
  }
}

/** 停止调度器 */
async function handleStop(): Promise<void> {
  actionLoading.value = true
  error.value = null
  try {
    await stopScheduler()
    await loadStatus()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '停止调度器失败'
  } finally {
    actionLoading.value = false
  }
}

/** 调度器是否运行中 */
function isRunning(): boolean {
  if (!schedulerStatus.value) return false
  return String(schedulerStatus.value.status || '').toLowerCase() === 'running'
      || String(schedulerStatus.value.is_running || '').toLowerCase() === 'true'
      || schedulerStatus.value.is_running === true
}

/** 格式化时间 */
function formatTime(val: unknown): string {
  return String(val || '').substring(0, 19).replace('T', ' ')
}

onMounted(loadStatus)
</script>

<template>
  <div class="scheduler-view">
    <div class="page-header">
      <h2 class="page-title">调度器管理</h2>
      <p class="page-desc">查看和控制自动化任务调度器的运行状态</p>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <!-- 状态概览 -->
    <div class="status-section">
      <div class="status-card">
        <div class="status-indicator" :class="isRunning() ? 'indicator-running' : 'indicator-stopped'">
          <span class="indicator-dot"></span>
          <span class="indicator-text">{{ isRunning() ? '运行中' : '已停止' }}</span>
        </div>
        <div class="status-actions">
          <button
            v-if="!isRunning()"
            class="btn-primary"
            :disabled="actionLoading"
            @click="handleStart"
          >
            启动调度器
          </button>
          <button
            v-else
            class="btn-danger"
            :disabled="actionLoading"
            @click="handleStop"
          >
            停止调度器
          </button>
        </div>
      </div>
    </div>

    <!-- 状态详情 -->
    <div v-if="schedulerStatus" class="section-card">
      <h3 class="section-title">状态详情</h3>
      <div class="detail-grid">
        <div class="detail-item">
          <div class="detail-label">运行状态</div>
          <div class="detail-value" :class="isRunning() ? 'value-positive' : 'value-negative'">
            {{ isRunning() ? '运行中' : '已停止' }}
          </div>
        </div>
        <div class="detail-item">
          <div class="detail-label">启动时间</div>
          <div class="detail-value">{{ formatTime(schedulerStatus.started_at || schedulerStatus.last_start) }}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">下次执行</div>
          <div class="detail-value">{{ formatTime(schedulerStatus.next_run || schedulerStatus.next_execution) }}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">上次执行</div>
          <div class="detail-value">{{ formatTime(schedulerStatus.last_run || schedulerStatus.last_execution) }}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">执行次数</div>
          <div class="detail-value">{{ schedulerStatus.total_runs ?? schedulerStatus.run_count ?? '-' }}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">调度间隔</div>
          <div class="detail-value">{{ schedulerStatus.interval ?? schedulerStatus.schedule ?? '-' }}</div>
        </div>
      </div>
    </div>

    <!-- 调度任务列表 -->
    <div v-if="schedulerJobs.length > 0" class="section-card">
      <h3 class="section-title">调度任务</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>任务名称</th>
              <th>调度规则</th>
              <th>下次执行</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in schedulerJobs" :key="String(job.name || job.id)">
              <td>{{ String(job.name || job.id || '-') }}</td>
              <td class="mono">{{ String(job.schedule || job.cron || job.interval || '-') }}</td>
              <td>{{ formatTime(job.next_run || job.next_execution) }}</td>
              <td>
                <span class="job-status" :class="job.active !== false && job.status !== 'paused' ? 'job-active' : 'job-paused'">
                  {{ job.active !== false && job.status !== 'paused' ? '活跃' : '暂停' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 无数据 -->
    <div v-if="!schedulerStatus && !loading" class="empty-state">
      无法获取调度器状态，请检查后端服务是否正常运行
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
  </div>
</template>

<style scoped>
.scheduler-view {
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

/* 状态概览 */
.status-section {
  display: flex;
  gap: 16px;
}

.status-card {
  flex: 1;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
}

.indicator-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.indicator-running .indicator-dot {
  background: var(--color-positive);
  box-shadow: 0 0 8px rgba(0, 185, 107, 0.5);
  animation: pulse 2s ease-in-out infinite;
}

.indicator-stopped .indicator-dot {
  background: var(--color-negative);
}

.indicator-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
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

/* 详情网格 */
.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.detail-item {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px 14px;
}

.detail-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.detail-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
}

.mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
}

/* 任务状态 */
.job-status {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 12px;
  font-weight: 500;
}

.job-active {
  background: rgba(0, 185, 107, 0.12);
  color: var(--color-positive);
}

.job-paused {
  background: rgba(122, 132, 153, 0.12);
  color: var(--color-text-muted);
}

@media (max-width: 768px) {
  .detail-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .status-card {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
}

@media (max-width: 480px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
