<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  getNotificationHistory,
  getNotificationChannels,
  testNotification,
} from '@/services/api'

/** 通知历史列表 */
const notificationHistory = ref<Array<Record<string, unknown>>>([])
/** 通知渠道列表 */
const channels = ref<Array<Record<string, unknown>>>([])
/** 加载状态 */
const loading = ref(false)
/** 错误信息 */
const error = ref<string | null>(null)
/** 当前激活的标签页 */
const activeTab = ref<'history' | 'channels'>('history')
/** 测试通知发送中 */
const testLoading = ref(false)
/** 测试通知结果 */
const testResult = ref<string | null>(null)

/** 加载通知历史 */
async function loadHistory(): Promise<void> {
  try {
    const res = await getNotificationHistory()
    notificationHistory.value = res?.data ?? res?.notifications ?? (Array.isArray(res) ? res : [])
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载通知历史失败'
  }
}

/** 加载通知渠道 */
async function loadChannels(): Promise<void> {
  try {
    const res = await getNotificationChannels()
    channels.value = res?.data ?? res?.channels ?? (Array.isArray(res) ? res : [])
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载通知渠道失败'
  }
}

/** 加载全部数据 */
async function loadAll(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    await Promise.all([loadHistory(), loadChannels()])
  } finally {
    loading.value = false
  }
}

/** 发送测试通知 */
async function handleTestNotification(): Promise<void> {
  testLoading.value = true
  testResult.value = null
  try {
    const res = await testNotification()
    testResult.value = res?.message ?? res?.detail ?? '测试通知已发送'
  } catch (e) {
    testResult.value = e instanceof Error ? e.message : '测试通知发送失败'
  } finally {
    testLoading.value = false
  }
}

/** 通知类型图标文字 */
function channelTypeLabel(type: string): string {
  const t = String(type).toLowerCase()
  if (t.includes('email') || t.includes('mail')) return '邮件'
  if (t.includes('wechat') || t.includes('weixin')) return '微信'
  if (t.includes('dingtalk') || t.includes('ding')) return '钉钉'
  if (t.includes('webhook')) return 'Webhook'
  if (t.includes('sms')) return '短信'
  return String(type)
}

/** 通知级别样式 */
function levelClass(level: string): string {
  const l = String(level).toLowerCase()
  if (l === 'critical' || l === 'error' || l === 'high') return 'level-critical'
  if (l === 'warning' || l === 'medium') return 'level-warning'
  if (l === 'info' || l === 'low') return 'level-info'
  return ''
}

/** 格式化时间 */
function formatTime(val: unknown): string {
  return String(val || '').substring(0, 16).replace('T', ' ')
}

onMounted(loadAll)
</script>

<template>
  <div class="notification-view">
    <div class="page-header">
      <h2 class="page-title">通知中心</h2>
      <p class="page-desc">查看通知历史记录、管理通知渠道配置、测试通知发送</p>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <!-- 标签页切换 -->
    <div class="tab-bar">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'history' }"
        @click="activeTab = 'history'"
      >
        通知历史
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'channels' }"
        @click="activeTab = 'channels'"
      >
        渠道配置
      </button>
    </div>

    <!-- 通知历史 -->
    <div v-if="activeTab === 'history'" class="section-card">
      <div class="section-header">
        <h3 class="section-title">通知记录</h3>
        <button
          class="btn-secondary btn-sm"
          :disabled="testLoading"
          @click="handleTestNotification"
        >
          发送测试通知
        </button>
      </div>

      <!-- 测试结果提示 -->
      <div v-if="testResult" class="test-result">
        {{ testResult }}
      </div>

      <div v-if="notificationHistory.length === 0 && !loading" class="empty-state">
        暂无通知记录
      </div>
      <div v-else class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>时间</th>
              <th>类型</th>
              <th>级别</th>
              <th>标题</th>
              <th>渠道</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in notificationHistory" :key="String(item.id)">
              <td>{{ formatTime(item.created_at || item.timestamp) }}</td>
              <td>{{ String(item.type || item.category || '-') }}</td>
              <td>
                <span class="level-tag" :class="levelClass(String(item.level || item.priority))">
                  {{ String(item.level || item.priority || '-') }}
                </span>
              </td>
              <td class="title-cell">{{ String(item.title || item.subject || '-') }}</td>
              <td>{{ channelTypeLabel(String(item.channel || item.via || '-')) }}</td>
              <td>
                <span class="status-tag" :class="String(item.status) === 'sent' || String(item.status) === 'delivered' ? 'status-sent' : String(item.status) === 'failed' ? 'status-failed' : 'status-pending'">
                  {{ String(item.status || '-') }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 渠道配置 -->
    <div v-if="activeTab === 'channels'" class="section-card">
      <h3 class="section-title">通知渠道</h3>
      <div v-if="channels.length === 0 && !loading" class="empty-state">
        暂无已配置的通知渠道
      </div>
      <div v-else class="channel-grid">
        <div
          v-for="channel in channels"
          :key="String(channel.id || channel.name)"
          class="channel-card"
        >
          <div class="channel-header">
            <span class="channel-type-badge">{{ channelTypeLabel(String(channel.type || channel.name)) }}</span>
            <span class="channel-status" :class="channel.enabled !== false && channel.active !== false ? 'channel-active' : 'channel-inactive'">
              {{ channel.enabled !== false && channel.active !== false ? '已启用' : '已禁用' }}
            </span>
          </div>
          <div class="channel-body">
            <div class="channel-info-row">
              <span class="channel-info-label">名称</span>
              <span class="channel-info-value">{{ String(channel.name || channel.label || '-') }}</span>
            </div>
            <div class="channel-info-row">
              <span class="channel-info-label">类型</span>
              <span class="channel-info-value">{{ channelTypeLabel(String(channel.type || '-')) }}</span>
            </div>
            <div v-if="channel.config || channel.settings" class="channel-info-row">
              <span class="channel-info-label">配置</span>
              <span class="channel-info-value mono">{{ String(JSON.stringify(channel.config || channel.settings)).substring(0, 60) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
  </div>
</template>

<style scoped>
.notification-view {
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
}

.tab-btn:hover {
  color: var(--color-text-primary);
}

.tab-btn.active {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
}

/* 区块卡片 */
.section-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 0;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}

/* 测试结果 */
.test-result {
  padding: 10px 14px;
  background: rgba(37, 99, 235, 0.06);
  border: 1px solid rgba(37, 99, 235, 0.15);
  border-radius: var(--radius);
  font-size: 13px;
  color: var(--color-accent);
  margin-bottom: 12px;
}

/* 级别标签 */
.level-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 12px;
  font-weight: 500;
}

.level-critical {
  background: rgba(245, 34, 45, 0.12);
  color: var(--color-negative);
}

.level-warning {
  background: rgba(250, 173, 20, 0.12);
  color: var(--color-warning);
}

.level-info {
  background: rgba(37, 99, 235, 0.12);
  color: var(--color-accent);
}

/* 发送状态 */
.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 12px;
  font-weight: 500;
}

.status-sent {
  background: rgba(0, 185, 107, 0.12);
  color: var(--color-positive);
}

.status-failed {
  background: rgba(245, 34, 45, 0.12);
  color: var(--color-negative);
}

.status-pending {
  background: rgba(250, 173, 20, 0.12);
  color: var(--color-warning);
}

.title-cell {
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 渠道网格 */
.channel-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.channel-card {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
}

.channel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--color-border);
}

.channel-type-badge {
  padding: 2px 8px;
  background: rgba(37, 99, 235, 0.1);
  border: 1px solid rgba(37, 99, 235, 0.2);
  border-radius: 2px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-accent);
}

.channel-status {
  font-size: 12px;
  font-weight: 500;
}

.channel-active {
  color: var(--color-positive);
}

.channel-inactive {
  color: var(--color-text-muted);
}

.channel-body {
  padding: 10px 14px;
}

.channel-info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.channel-info-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.channel-info-value {
  font-size: 13px;
  color: var(--color-text-primary);
}

.mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
}

@media (max-width: 1024px) {
  .channel-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .channel-grid {
    grid-template-columns: 1fr;
  }
}
</style>
