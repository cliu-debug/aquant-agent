<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { getMCPTools, callMCPTool } from '@/services/api'
import type { MCPToolInfo } from '@/services/api'

/** 工具列表 */
const tools = ref<MCPToolInfo[]>([])
/** 加载状态 */
const loading = ref(false)
/** 错误信息 */
const error = ref<string | null>(null)

/** 当前选中的工具名称 */
const selectedTool = ref<string | null>(null)
/** 工具调用参数 */
const callArgs = reactive<Record<string, string>>({})
/** 调用中状态 */
const calling = ref(false)
/** 调用结果 */
const callResult = ref<{ success: boolean; result: unknown } | null>(null)
/** 调用错误 */
const callError = ref<string | null>(null)

/** 加载工具列表 */
async function loadTools(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    const res = await getMCPTools()
    tools.value = res?.tools ?? []
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载工具列表失败'
  } finally {
    loading.value = false
  }
}

/** 选中工具 */
function selectTool(toolName: string): void {
  selectedTool.value = toolName
  callResult.value = null
  callError.value = null
  // 初始化参数
  const tool = tools.value.find((t) => t.name === toolName)
  if (tool?.parameters) {
    for (const param of tool.parameters) {
      callArgs[param.name] = param.default != null ? String(param.default) : ''
    }
  }
}

/** 获取当前选中的工具信息 */
function getSelectedTool(): MCPToolInfo | undefined {
  return tools.value.find((t) => t.name === selectedTool.value)
}

/** 调用工具 */
async function handleCall(): Promise<void> {
  if (!selectedTool.value) return
  calling.value = true
  callResult.value = null
  callError.value = null
  try {
    // 将字符串参数转换为适当类型
    const tool = getSelectedTool()
    const args: Record<string, unknown> = {}
    if (tool?.parameters) {
      for (const param of tool.parameters) {
        const raw = callArgs[param.name]
        if (raw === '' || raw === undefined) {
          if (param.required) {
            callError.value = `参数 ${param.name} 不能为空`
            calling.value = false
            return
          }
          continue
        }
        // 根据参数类型转换
        if (param.type === 'number' || param.type === 'integer') {
          args[param.name] = Number(raw)
        } else if (param.type === 'boolean') {
          args[param.name] = raw === 'true'
        } else {
          args[param.name] = raw
        }
      }
    }
    const res = await callMCPTool({
      tool_name: selectedTool.value,
      arguments: args,
    })
    callResult.value = { success: res.success, result: res.result }
  } catch (e) {
    callError.value = e instanceof Error ? e.message : '调用工具失败'
  } finally {
    calling.value = false
  }
}

/** 格式化 JSON 结果 */
function formatResult(data: unknown): string {
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

onMounted(loadTools)
</script>

<template>
  <div class="mcp-tools-view">
    <div class="page-header">
      <h2 class="page-title">MCP 工具</h2>
      <p class="page-desc">查看和调用 MCP 工具，测试工具功能</p>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <div class="mcp-layout">
      <!-- 工具列表 -->
      <div class="tool-list-panel">
        <div class="panel-header">
          <span class="panel-title">工具列表</span>
          <span class="tool-count">{{ tools.length }} 个工具</span>
        </div>
        <div class="tool-list">
          <button
            v-for="tool in tools"
            :key="tool.name"
            class="tool-item"
            :class="{ active: selectedTool === tool.name }"
            @click="selectTool(tool.name)"
          >
            <span class="tool-name mono">{{ tool.name }}</span>
            <span class="tool-desc">{{ tool.description }}</span>
            <span class="tool-param-count">{{ tool.parameters?.length ?? 0 }} 个参数</span>
          </button>
          <div v-if="!tools.length && !loading" class="empty-state">暂无工具</div>
        </div>
      </div>

      <!-- 工具详情和调用 -->
      <div class="tool-detail-panel">
        <template v-if="getSelectedTool()">
          <div class="detail-header">
            <h3 class="detail-title mono">{{ getSelectedTool()!.name }}</h3>
            <p class="detail-desc">{{ getSelectedTool()!.description }}</p>
          </div>

          <!-- 参数表单 -->
          <div v-if="getSelectedTool()!.parameters?.length" class="params-section">
            <h4 class="params-title">参数</h4>
            <div class="params-form">
              <div
                v-for="param in getSelectedTool()!.parameters"
                :key="param.name"
                class="param-row"
              >
                <label class="param-label">
                  <span class="param-name mono">{{ param.name }}</span>
                  <span v-if="param.required" class="param-required">必填</span>
                  <span class="param-type">{{ param.type }}</span>
                </label>
                <p class="param-desc">{{ param.description }}</p>
                <input
                  v-model="callArgs[param.name]"
                  class="input param-input"
                  :placeholder="param.default != null ? String(param.default) : `输入 ${param.name}`"
                />
              </div>
            </div>
          </div>

          <div v-else class="params-section">
            <p class="no-params">该工具无需参数</p>
          </div>

          <!-- 调用按钮 -->
          <div class="call-actions">
            <button
              class="btn-primary"
              :disabled="calling"
              @click="handleCall"
            >
              {{ calling ? '调用中...' : '调用工具' }}
            </button>
          </div>

          <!-- 调用结果 -->
          <div v-if="callError" class="error-msg">{{ callError }}</div>
          <div v-if="callResult" class="result-section">
            <h4 class="result-title">
              调用结果
              <span class="result-status" :class="callResult.success ? 'status-ok' : 'status-fail'">
                {{ callResult.success ? '成功' : '失败' }}
              </span>
            </h4>
            <pre class="result-content">{{ formatResult(callResult.result) }}</pre>
          </div>
        </template>

        <div v-else class="empty-state">请从左侧选择一个工具</div>
      </div>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
  </div>
</template>

<style scoped>
.mcp-tools-view {
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

/* 双栏布局 */
.mcp-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
  min-height: 500px;
}

/* 工具列表面板 */
.tool-list-panel {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--color-border);
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.tool-count {
  font-size: 12px;
  color: var(--color-text-muted);
}

.tool-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}

.tool-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: var(--radius);
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
  width: 100%;
  transition: background 0.15s;
}

.tool-item:hover {
  background: var(--color-bg-hover);
}

.tool-item.active {
  background: rgba(37, 99, 235, 0.1);
  border: 1px solid rgba(37, 99, 235, 0.3);
}

.tool-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.tool-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tool-param-count {
  font-size: 11px;
  color: var(--color-text-muted);
}

/* 工具详情面板 */
.tool-detail-panel {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-header {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 12px;
}

.detail-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-accent);
  margin-bottom: 4px;
}

.detail-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

/* 参数表单 */
.params-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.params-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.no-params {
  font-size: 13px;
  color: var(--color-text-muted);
}

.params-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.param-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.param-label {
  display: flex;
  align-items: center;
  gap: 6px;
}

.param-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
}

.param-required {
  font-size: 10px;
  padding: 1px 4px;
  background: rgba(245, 34, 45, 0.12);
  color: var(--color-negative);
  border-radius: 2px;
}

.param-type {
  font-size: 11px;
  color: var(--color-text-muted);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.param-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 2px;
}

.param-input {
  width: 100%;
  max-width: 400px;
}

/* 调用按钮 */
.call-actions {
  display: flex;
  gap: 8px;
}

/* 调用结果 */
.result-section {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 12px;
}

.result-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.result-status {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 2px;
  font-size: 11px;
  font-weight: 500;
}

.status-ok {
  background: rgba(0, 185, 107, 0.12);
  color: var(--color-positive);
}

.status-fail {
  background: rgba(245, 34, 45, 0.12);
  color: var(--color-negative);
}

.result-content {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
  margin: 0;
}

@media (max-width: 768px) {
  .mcp-layout {
    grid-template-columns: 1fr;
  }
  .tool-list-panel {
    max-height: 300px;
  }
}
</style>
