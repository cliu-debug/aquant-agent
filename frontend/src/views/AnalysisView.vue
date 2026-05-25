<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAgentStore } from '@/stores/agentStore'
import { AgentStatus, WorkflowStage, LogLevel, Signal, RiskLevel } from '@/types/agent'
import type { Agent, AgentOutput } from '@/types/agent'
import { analyzeStock, getPopularStocks, type AnalyzeResponse, type PopularStock } from '@/services/api'

import AgentScene from '@/components/visualization/AgentScene.vue'
import WorkflowGraph from '@/components/workflow/WorkflowGraph.vue'
import AgentCard from '@/components/agents/AgentCard.vue'
import LogConsole from '@/components/dashboard/LogConsole.vue'
import ResultCard from '@/components/dashboard/ResultCard.vue'

const store = useAgentStore()

const stockCode = ref('')
const stockName = ref('')
const selectedAgent = ref<Agent | null>(null)
const show3D = ref(true)
const analysisError = ref<string | null>(null)
const popularStocks = ref<PopularStock[]>([])

const isAnalyzing = computed(() => store.isRunning)
const overallProgress = computed(() => store.overallProgress)

onMounted(async () => {
  store.initAgents()
  await loadPopularStocks()
})

async function loadPopularStocks() {
  try {
    const res = await getPopularStocks()
    popularStocks.value = res.stocks
  } catch {
    popularStocks.value = [
      { code: '600519.SH', name: '贵州茅台', industry: '白酒' },
      { code: '000858.SZ', name: '五粮液', industry: '白酒' },
      { code: '000001.SZ', name: '平安银行', industry: '银行' },
      { code: '600036.SH', name: '招商银行', industry: '银行' },
    ]
  }
}

/** 信号字符串映射 */
const signalMap: Record<string, Signal> = {
  strong_buy: Signal.STRONG_BUY,
  buy: Signal.BUY,
  hold: Signal.HOLD,
  sell: Signal.SELL,
  strong_sell: Signal.STRONG_SELL,
}

/** 风险等级映射 */
function mapRiskLevel(riskData: Record<string, unknown> | null): RiskLevel {
  if (!riskData) return RiskLevel.MEDIUM
  const level = riskData.risk_level as string || riskData.level as string || 'medium'
  if (level.includes('低') || level === 'low') return RiskLevel.LOW
  if (level.includes('高') || level === 'high') return RiskLevel.HIGH
  if (level.includes('极') || level === 'extreme') return RiskLevel.EXTREME
  return RiskLevel.MEDIUM
}

/** 从后端分析结果提取智能体输出 */
function extractAgentOutput(key: string, data: Record<string, unknown> | null): AgentOutput | null {
  if (!data) return null
  const summary = (data.summary as string) || (data.analysis as string) || JSON.stringify(data).substring(0, 200)
  const metrics: Record<string, number | string> = {}

  const metricKeys = ['signal', 'confidence', 'score', 'recommendation', 'trend', 'pe_ratio', 'pb_ratio', 'sentiment_score']
  for (const mk of metricKeys) {
    if (data[mk] !== undefined && data[mk] !== null) {
      const val = data[mk]
      metrics[mk] = typeof val === 'object' ? JSON.stringify(val) : String(val)
    }
  }

  const signal = data.signal ? signalMap[data.signal as string] : undefined
  const confidence = typeof data.confidence === 'number' ? data.confidence : undefined

  return { summary, keyMetrics: metrics, signal, confidence }
}

/**
 * 启动股票分析 - 真正调用后端 API
 */
async function startAnalysis(): Promise<void> {
  if (!stockCode.value.trim()) return
  if (store.isRunning) return

  analysisError.value = null
  store.reset()
  store.isRunning = true

  addSystemLog(`开始分析 ${stockCode.value}...`)

  const progressController = startProgressSimulation()

  try {
    const response = await analyzeStock({
      stock_code: stockCode.value.trim(),
      stock_name: stockName.value.trim() || undefined,
    })

    progressController.stop()

    completeAllAgents()

    updateAgentOutputs(response)

    setFinalResultFromResponse(response)

    addSystemLog(`✅ ${response.stock_name} 分析完成！信号: ${response.final_signal || '未知'}`)
  } catch (err) {
    progressController.stop()
    const errorMessage = err instanceof Error ? err.message : '未知错误'
    analysisError.value = errorMessage
    store.isRunning = false
    addSystemLog(`❌ 分析失败: ${errorMessage}`, LogLevel.ERROR)

    store.agents.forEach((agent) => {
      if (agent.status === AgentStatus.RUNNING || agent.status === AgentStatus.INITIALIZING) {
        store.updateAgentStatus(agent.id, AgentStatus.FAILED, agent.progress)
      }
    })
  }
}

/**
 * 进度模拟控制器
 * 因为后端是同步执行的，前端需要模拟各阶段进度
 */
function startProgressSimulation(): { stop: () => void } {
  let stopped = false

  const phases = [
    { stage: WorkflowStage.DATA_FETCH, agents: ['data_fetcher'], duration: 1500 },
    { stage: WorkflowStage.PARALLEL_ANALYSIS, agents: ['technical', 'fundamental', 'sentiment', 'news'], duration: 3000 },
    { stage: WorkflowStage.DEBATE, agents: ['bull', 'bear'], duration: 2000 },
    { stage: WorkflowStage.RISK_ASSESSMENT, agents: ['risk'], duration: 1500 },
    { stage: WorkflowStage.DECISION, agents: ['trader'], duration: 1000 },
  ]

  let delay = 0

  phases.forEach((phase) => {
    setTimeout(() => {
      if (stopped) return
      store.setCurrentPhase(phase.stage)

      phase.agents.forEach((agentId, index) => {
        setTimeout(() => {
          if (stopped) return
          store.updateAgentStatus(agentId, AgentStatus.RUNNING, 10)
          store.updateAgentProgress(agentId, 10, '正在分析...')

          addAgentLog(agentId, '开始执行分析任务...')

          const progressInterval = setInterval(() => {
            if (stopped) { clearInterval(progressInterval); return }
            const agent = store.agents.find(a => a.id === agentId)
            if (!agent || agent.status !== AgentStatus.RUNNING) { clearInterval(progressInterval); return }
            const newProgress = Math.min(agent.progress + Math.random() * 15, 90)
            store.updateAgentProgress(agentId, newProgress)
          }, 300)

          setTimeout(() => clearInterval(progressInterval), phase.duration + 2000)
        }, index * 200)
      })
    }, delay)

    delay += phase.duration + phase.agents.length * 200
  })

  return {
    stop: () => { stopped = true },
  }
}

/** 将所有智能体标记为完成 */
function completeAllAgents(): void {
  store.agents.forEach((agent) => {
    if (agent.status !== AgentStatus.COMPLETED && agent.status !== AgentStatus.FAILED) {
      store.updateAgentStatus(agent.id, AgentStatus.COMPLETED, 100)
      store.updateAgentProgress(agent.id, 100, '分析完成')
    }
  })
  store.setCurrentPhase(WorkflowStage.DECISION)
}

/** 从后端响应更新各智能体输出 */
function updateAgentOutputs(response: AnalyzeResponse): void {
  const outputMap: Record<string, Record<string, unknown> | null> = {
    data_fetcher: null,
    technical: response.technical_analysis,
    fundamental: response.fundamental_analysis,
    sentiment: response.sentiment_analysis,
    news: response.news_analysis,
    bull: response.debate,
    bear: response.debate,
    risk: response.risk_assessment,
    trader: response.trade_proposal,
  }

  for (const [agentId, data] of Object.entries(outputMap)) {
    const output = extractAgentOutput(agentId, data)
    if (output) {
      store.setAgentOutput(agentId, output)
    }
  }
}

/** 从后端响应设置最终结果 */
function setFinalResultFromResponse(response: AnalyzeResponse): void {
  const signal = signalMap[response.final_signal || 'hold'] || Signal.HOLD
  const confidence = response.final_confidence || 50
  const riskLevel = mapRiskLevel(response.risk_assessment)

  const agentViews: AgentOutput[] = []
  const viewMap: Array<[string, Record<string, unknown> | null]> = [
    ['technical', response.technical_analysis],
    ['fundamental', response.fundamental_analysis],
    ['sentiment', response.sentiment_analysis],
    ['news', response.news_analysis],
  ]
  for (const [key, data] of viewMap) {
    const output = extractAgentOutput(key, data)
    if (output) agentViews.push(output)
  }

  store.setFinalResult({
    stockCode: response.stock_code,
    stockName: response.stock_name,
    currentPrice: response.current_price || 0,
    changePercent: 0,
    signal,
    score: confidence,
    confidence,
    riskLevel,
    summary: response.full_report ? response.full_report.substring(0, 300) : '分析完成',
    agentViews,
  })
}

/** 添加系统日志 */
function addSystemLog(message: string, level: LogLevel = LogLevel.INFO): void {
  store.addLog({
    id: `log_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
    timestamp: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    level,
    source: 'system',
    sourceName: '系统',
    message,
  })
}

/** 添加智能体日志 */
function addAgentLog(agentId: string, message: string): void {
  const agent = store.agents.find(a => a.id === agentId)
  store.addLog({
    id: `log_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
    timestamp: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    level: LogLevel.INFO,
    source: agentId as Agent['type'],
    sourceName: agent?.name || agentId,
    message,
  })
}

function handleAgentClick(agent: Agent): void {
  selectedAgent.value = selectedAgent.value?.id === agent.id ? null : agent
}

function fillStock(code: string, name: string): void {
  stockCode.value = code
  stockName.value = name
}
</script>

<template>
  <div class="analysis-view">
    <!-- 顶部搜索栏 -->
    <header class="search-header">
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input
          v-model="stockCode"
          type="text"
          placeholder="输入股票代码 (如 600519.SH)"
          class="search-input"
          @keyup.enter="startAnalysis"
          :disabled="isAnalyzing"
        />
        <input
          v-model="stockName"
          type="text"
          placeholder="股票名称 (可选)"
          class="search-input name-input"
          @keyup.enter="startAnalysis"
          :disabled="isAnalyzing"
        />
        <button
          class="analyze-btn"
          :class="{ active: isAnalyzing }"
          @click="startAnalysis"
          :disabled="isAnalyzing || !stockCode.trim()"
        >
          <span v-if="isAnalyzing" class="btn-loading">⏳</span>
          <span v-else>🚀</span>
          {{ isAnalyzing ? '分析中...' : '开始分析' }}
        </button>
      </div>

      <div class="popular-stocks">
        <span class="popular-label">热门:</span>
        <button
          v-for="stock in popularStocks"
          :key="stock.code"
          class="popular-tag"
          @click="fillStock(stock.code, stock.name)"
          :disabled="isAnalyzing"
        >
          {{ stock.name }}
        </button>
      </div>
    </header>

    <!-- 总进度条 -->
    <div v-if="isAnalyzing" class="global-progress">
      <div class="progress-info">
        <span class="progress-label">总体进度</span>
        <span class="progress-value">{{ overallProgress }}%</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${overallProgress}%` }"></div>
      </div>
    </div>

    <!-- 3D 场景 -->
    <section class="scene-section" v-if="show3D">
      <AgentScene :agents="store.agents" />
      <button class="toggle-3d-btn" @click="show3D = false">收起3D</button>
    </section>
    <section v-else class="scene-collapsed">
      <button class="toggle-3d-btn" @click="show3D = true">展开3D场景</button>
    </section>

    <!-- 工作流进度 -->
    <section class="workflow-section">
      <WorkflowGraph :agents="store.agents" :current-phase="store.currentPhase" />
    </section>

    <!-- 下方内容区 -->
    <div class="content-grid">
      <div class="left-panel">
        <LogConsole :logs="store.logs" :is-running="isAnalyzing" />
      </div>
      <div class="right-panel">
        <div class="agents-grid">
          <AgentCard
            v-for="agent in store.agents"
            :key="agent.id"
            :agent="agent"
            @click="handleAgentClick"
          />
        </div>
        <Transition name="slide">
          <ResultCard v-if="store.finalResult" :result="store.finalResult" />
        </Transition>
      </div>
    </div>

    <!-- 错误提示 -->
    <Transition name="fade">
      <div v-if="analysisError" class="error-banner">
        <span class="error-icon">❌</span>
        <span class="error-text">{{ analysisError }}</span>
        <button class="error-close" @click="analysisError = null">✕</button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.analysis-view {
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 100vh;
}

.search-header {
  background: #1E293B;
  border-radius: 16px;
  padding: 16px 20px;
  border: 1px solid rgba(255,255,255,0.06);
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #334155;
  border-radius: 12px;
  padding: 4px 4px 4px 16px;
  border: 1px solid rgba(255,255,255,0.1);
  transition: border-color 0.2s;
}

.search-box:focus-within {
  border-color: rgba(59,130,246,0.5);
}

.search-icon { font-size: 14px; color: #64748B; }

.search-input {
  background: none;
  border: none;
  color: #F8FAFC;
  font-size: 14px;
  outline: none;
  width: 180px;
  padding: 8px 0;
}

.search-input::placeholder { color: #64748B; }

.name-input {
  width: 120px;
  border-left: 1px solid rgba(255,255,255,0.1);
  padding-left: 12px;
}

.analyze-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  background: linear-gradient(135deg, #3B82F6, #8B5CF6);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.analyze-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(59,130,246,0.4);
}

.analyze-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.analyze-btn.active { background: linear-gradient(135deg, #F59E0B, #EAB308); }

.btn-loading { animation: spin 1s linear infinite; display: inline-block; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.popular-stocks {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.popular-label { font-size: 12px; color: #64748B; }

.popular-tag {
  padding: 4px 10px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;
  color: #94A3B8;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.popular-tag:hover:not(:disabled) { border-color: #3B82F6; color: #3B82F6; }
.popular-tag:disabled { opacity: 0.5; cursor: not-allowed; }

.global-progress { padding: 8px 0; }
.progress-info { display: flex; justify-content: space-between; margin-bottom: 4px; }
.progress-label { font-size: 12px; color: #94A3B8; }
.progress-value { font-size: 12px; color: #3B82F6; font-weight: 600; }
.progress-bar { height: 3px; background: #334155; border-radius: 2px; overflow: hidden; }
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3B82F6, #8B5CF6, #EC4899, #3B82F6);
  background-size: 300% 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
  animation: gradient-shift 3s ease infinite;
}
@keyframes gradient-shift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }

.scene-section { position: relative; border-radius: 16px; overflow: hidden; border: 1px solid rgba(255,255,255,0.06); }
.scene-collapsed { display: flex; justify-content: center; padding: 8px; }
.toggle-3d-btn {
  position: absolute; top: 12px; right: 12px; z-index: 10;
  padding: 6px 12px; background: rgba(0,0,0,0.5); backdrop-filter: blur(8px);
  border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
  color: #94A3B8; font-size: 12px; cursor: pointer; transition: all 0.2s;
}
.toggle-3d-btn:hover { background: rgba(0,0,0,0.7); color: #F8FAFC; }
.scene-collapsed .toggle-3d-btn { position: static; background: #1E293B; }

.workflow-section { border-radius: 12px; overflow: hidden; }

.content-grid { display: grid; grid-template-columns: 1fr 1.5fr; gap: 16px; flex: 1; }
.left-panel { min-width: 0; }
.right-panel { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.agents-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }

.error-banner {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px; background: rgba(239,68,68,0.1);
  border: 1px solid rgba(239,68,68,0.3); border-radius: 12px;
}
.error-icon { font-size: 16px; flex-shrink: 0; }
.error-text { flex: 1; color: #EF4444; font-size: 13px; }
.error-close { background: none; border: none; color: #64748B; cursor: pointer; font-size: 14px; padding: 4px; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(10px); }
.slide-enter-active, .slide-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateX(20px); }

@media (max-width: 1400px) { .agents-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 1024px) {
  .content-grid { grid-template-columns: 1fr; }
  .agents-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .analysis-view { padding: 12px; }
  .name-input { display: none; }
  .search-input { width: 120px; }
  .agents-grid { grid-template-columns: 1fr; }
}
</style>
