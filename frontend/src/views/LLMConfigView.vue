<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getLLMConfig, testLLMConnection } from '@/services/api'
import type { LLMProviderConfig } from '@/services/api'

/** LLM 提供商配置列表 */
const providers = ref<LLMProviderConfig[]>([])
/** 加载状态 */
const loading = ref(false)
/** 错误信息 */
const error = ref<string | null>(null)
/** 正在测试的提供商名称 */
const testingProvider = ref<string | null>(null)
/** 测试结果映射：provider -> { success, message, latency_ms } */
const testResults = ref<Record<string, { success: boolean; message: string; latency_ms?: number }>>({})

/** 预定义的6个提供商 */
const PRESET_PROVIDERS = [
  { key: 'openai', label: 'OpenAI' },
  { key: 'anthropic', label: 'Anthropic' },
  { key: 'qwen', label: '通义千问' },
  { key: 'deepseek', label: 'DeepSeek' },
  { key: 'ollama', label: 'Ollama' },
  { key: 'zhipu', label: '智谱AI' },
]

/** 加载 LLM 配置 */
async function loadConfig(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const res = await getLLMConfig()
    providers.value = res?.providers ?? []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载LLM配置失败'
  } finally {
    loading.value = false
  }
}

/** 根据 provider key 查找配置 */
function findProvider(key: string): LLMProviderConfig | undefined {
  return providers.value.find((p) => p.provider === key)
}

/** 获取连接状态样式类 */
function statusClass(provider: LLMProviderConfig | undefined): string {
  if (!provider) return 'status-unknown'
  switch (provider.status) {
    case 'connected':
      return 'status-connected'
    case 'disconnected':
      return 'status-disconnected'
    default:
      return 'status-unknown'
  }
}

/** 获取连接状态文字 */
function statusText(provider: LLMProviderConfig | undefined): string {
  if (!provider) return '未配置'
  switch (provider.status) {
    case 'connected':
      return '已连接'
    case 'disconnected':
      return '未连接'
    default:
      return '未知'
  }
}

/** 测试 LLM 连接 */
async function handleTest(providerKey: string): Promise<void> {
  testingProvider.value = providerKey
  try {
    const res = await testLLMConnection(providerKey)
    testResults.value[providerKey] = {
      success: res.success,
      message: res.message,
      latency_ms: res.latency_ms,
    }
    // 刷新配置以更新状态
    await loadConfig()
  } catch (e) {
    testResults.value[providerKey] = {
      success: false,
      message: e instanceof Error ? e.message : '测试失败',
    }
  } finally {
    testingProvider.value = null
  }
}

onMounted(loadConfig)
</script>

<template>
  <div class="llm-config-view">
    <div class="page-header">
      <h2 class="page-title">LLM 配置</h2>
      <p class="page-desc">管理和测试各 LLM 提供商的连接配置</p>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <!-- 提供商卡片网格 -->
    <div class="provider-grid">
      <div
        v-for="preset in PRESET_PROVIDERS"
        :key="preset.key"
        class="provider-card"
      >
        <div class="provider-header">
          <span class="provider-name">{{ preset.label }}</span>
          <span class="provider-status" :class="statusClass(findProvider(preset.key))">
            {{ statusText(findProvider(preset.key)) }}
          </span>
        </div>

        <div class="provider-body">
          <div class="provider-field">
            <span class="field-label">模型</span>
            <span class="field-value mono">{{ findProvider(preset.key)?.model || '-' }}</span>
          </div>
          <div class="provider-field">
            <span class="field-label">API Key</span>
            <span class="field-value mono">{{ findProvider(preset.key)?.api_key_masked || '未设置' }}</span>
          </div>
          <div class="provider-field">
            <span class="field-label">已配置</span>
            <span
              class="field-value"
              :class="findProvider(preset.key)?.api_key_set ? 'value-positive' : 'value-negative'"
            >
              {{ findProvider(preset.key)?.api_key_set ? '是' : '否' }}
            </span>
          </div>
        </div>

        <!-- 测试结果 -->
        <div v-if="testResults[preset.key]" class="test-result" :class="testResults[preset.key].success ? 'test-success' : 'test-fail'">
          <span class="test-msg">{{ testResults[preset.key].message }}</span>
          <span v-if="testResults[preset.key].latency_ms" class="test-latency">
            {{ testResults[preset.key].latency_ms }}ms
          </span>
        </div>

        <div class="provider-footer">
          <button
            class="btn-primary btn-test"
            :disabled="testingProvider === preset.key"
            @click="handleTest(preset.key)"
          >
            {{ testingProvider === preset.key ? '测试中...' : '测试连接' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
  </div>
</template>

<style scoped>
.llm-config-view {
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

/* 提供商卡片网格 */
.provider-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.provider-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.provider-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-primary);
}

.provider-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.provider-status {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 2px;
  font-size: 12px;
  font-weight: 500;
}

.status-connected {
  background: rgba(0, 185, 107, 0.12);
  color: var(--color-positive);
}

.status-disconnected {
  background: rgba(245, 34, 45, 0.12);
  color: var(--color-negative);
}

.status-unknown {
  background: rgba(122, 132, 153, 0.12);
  color: var(--color-text-muted);
}

.provider-body {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
}

.provider-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.field-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.field-value {
  font-size: 13px;
  color: var(--color-text-primary);
}

.mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
}

/* 测试结果 */
.test-result {
  margin: 0 16px;
  padding: 8px 10px;
  border-radius: var(--radius);
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.test-success {
  background: rgba(0, 185, 107, 0.08);
  border: 1px solid rgba(0, 185, 107, 0.2);
  color: var(--color-positive);
}

.test-fail {
  background: rgba(245, 34, 45, 0.08);
  border: 1px solid rgba(245, 34, 45, 0.2);
  color: var(--color-negative);
}

.test-latency {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
}

.provider-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--color-border);
}

.btn-test {
  width: 100%;
  padding: 6px 12px;
  font-size: 13px;
}

@media (max-width: 1024px) {
  .provider-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .provider-grid {
    grid-template-columns: 1fr;
  }
}
</style>
