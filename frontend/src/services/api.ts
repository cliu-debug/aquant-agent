/**
 * 后端 API 服务模块
 * 封装所有与后端 FastAPI 的 HTTP 通信
 * API 端点与 astock_agents/web/app.py 对齐
 */

/** API 基础地址，从环境变量读取，默认 http://localhost:8000 */
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

/** 通用请求函数 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const token = localStorage.getItem('astock_token')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: { ...headers, ...options.headers },
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({
      detail: response.statusText,
    }))
    throw new Error(errorData.detail || `请求失败 (${response.status})`)
  }

  return response.json() as Promise<T>
}

// ==================== 分析 API ====================

/** 分析请求参数 */
export interface AnalyzeRequest {
  stock_code: string
  stock_name?: string
  days?: number
}

/** 分析响应数据 */
export interface AnalyzeResponse {
  stock_code: string
  stock_name: string
  current_price: number | null
  final_signal: string | null
  final_confidence: number | null
  technical_analysis: Record<string, unknown> | null
  fundamental_analysis: Record<string, unknown> | null
  sentiment_analysis: Record<string, unknown> | null
  news_analysis: Record<string, unknown> | null
  debate: Record<string, unknown> | null
  trade_proposal: Record<string, unknown> | null
  risk_assessment: Record<string, unknown> | null
  price_data:
    | Array<{
        date: string
        open: number
        high: number
        low: number
        close: number
        volume: number
      }>
    | null
  full_report: string | null
  timestamp: string
}

/** 分析股票 - POST /api/analyze */
export async function analyzeStock(
  data: AnalyzeRequest
): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>('/api/analyze', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ==================== 热门股票 API ====================

/** 热门股票数据 */
export interface PopularStock {
  code: string
  name: string
  industry: string
}

/** 获取热门股票列表 - GET /api/stocks/popular */
export async function getPopularStocks(): Promise<{
  stocks: PopularStock[]
}> {
  return request('/api/stocks/popular')
}

// ==================== 选股器 API ====================

/** 选股预设 */
export interface ScreenerPreset {
  name: string
  description: string
  conditions: Array<Record<string, unknown>>
}

/** 获取选股预设 - GET /api/screener/presets */
export async function getScreenerPresets(): Promise<{
  presets: ScreenerPreset[]
}> {
  return request('/api/screener/presets')
}

/** 选股扫描请求 */
export interface ScreenerScanRequest {
  preset_name?: string
  conditions?: Array<Record<string, unknown>>
}

/** 选股扫描 - POST /api/screener/scan */
export async function screenerScan(
  data: ScreenerScanRequest
): Promise<Record<string, unknown>> {
  return request('/api/screener/scan', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ==================== 自选股 API ====================

/** 自选股条目 */
export interface WatchlistItem {
  stock_code: string
  stock_name: string
  group?: string
  added_at?: string
  notes?: string
}

/** 获取自选股列表 - GET /api/watchlist */
export async function getWatchlist(
  group?: string
): Promise<{ items: WatchlistItem[]; total: number }> {
  const params = group ? `?group=${encodeURIComponent(group)}` : ''
  return request(`/api/watchlist${params}`)
}

/** 添加自选股 - POST /api/watchlist/add */
export async function addToWatchlist(
  item: WatchlistItem
): Promise<{ success: boolean; message: string }> {
  return request('/api/watchlist/add', {
    method: 'POST',
    body: JSON.stringify(item),
  })
}

/** 删除自选股 - DELETE /api/watchlist/{stock_code} */
export async function removeFromWatchlist(
  stockCode: string
): Promise<{ success: boolean }> {
  return request(
    `/api/watchlist/${encodeURIComponent(stockCode)}`,
    { method: 'DELETE' }
  )
}

/** 获取自选股分组 - GET /api/watchlist/groups */
export async function getWatchlistGroups(): Promise<{
  groups: Array<{ name: string; count: number }>
}> {
  return request('/api/watchlist/groups')
}

// ==================== 模拟交易 API ====================

/** 投资组合数据 */
export interface Portfolio {
  cash: number
  total_value: number
  total_return_pct: number
  positions: Array<{
    stock_code: string
    stock_name: string
    quantity: number
    avg_cost: number
    current_price: number
    market_value: number
    return_pct: number
  }>
}

/** 下单请求参数 */
export interface OrderRequest {
  stock_code: string
  stock_name?: string
  direction: string
  quantity: number
  order_type?: string
  price?: number
  reason?: string
  signal_source?: string
}

/** 获取投资组合 - GET /api/trading/portfolio */
export async function getPortfolio(): Promise<Portfolio> {
  return request('/api/trading/portfolio')
}

/** 下单 - POST /api/trading/order */
export async function placeOrder(
  order: OrderRequest
): Promise<Record<string, unknown>> {
  return request('/api/trading/order', {
    method: 'POST',
    body: JSON.stringify(order),
  })
}

/** 获取订单列表 - GET /api/trading/orders */
export async function getOrders(
  limit: number = 50
): Promise<{ orders: Array<Record<string, unknown>> }> {
  return request(`/api/trading/orders?limit=${limit}`)
}

/** 获取交易历史 - GET /api/trading/history */
export async function getTradeHistory(): Promise<{
  history: Record<string, unknown>
}> {
  return request('/api/trading/history')
}

// ==================== 回测 API ====================

/** 回测交易信号 */
export interface BacktestSignal {
  date: string
  action: string
}

/** 回测请求参数 */
export interface BacktestRequest {
  stock_code: string
  strategy_name?: string
  signals: BacktestSignal[]
  position_size_pct?: number
  stop_loss_pct?: number
  take_profit_pct?: number
}

/** 运行回测 - POST /api/backtest/run */
export async function runBacktest(
  data: BacktestRequest
): Promise<Record<string, unknown>> {
  return request('/api/backtest/run', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 策略信息 */
export interface StrategyInfo {
  id: string
  name: string
  description: string
  params: StrategyParam[]
}

/** 策略参数定义 */
export interface StrategyParam {
  key: string
  label: string
  type: 'int' | 'float'
  default: number
  min: number
  max: number
}

/** 策略回测请求 */
export interface StrategyBacktestRequest {
  stock_code: string
  strategy_id: string
  strategy_params?: Record<string, number>
  position_size_pct?: number
  stop_loss_pct?: number
  take_profit_pct?: number
}

/** 获取可用策略列表 - GET /api/backtest/strategies */
export async function getBacktestStrategies(): Promise<StrategyInfo[]> {
  const res = await request<{ success: boolean; data: StrategyInfo[] }>('/api/backtest/strategies')
  return res.data
}

/** 策略自动回测 - POST /api/backtest/strategy-run */
export async function runStrategyBacktest(
  data: StrategyBacktestRequest
): Promise<Record<string, unknown>> {
  const res = await request<{ success: boolean; data: Record<string, unknown> }>('/api/backtest/strategy-run', {
    method: 'POST',
    body: JSON.stringify(data),
  })
  return res.data
}

// ==================== 复盘 API ====================

/** 获取复盘报告 - GET /api/review/report */
export async function getReviewReport(
  period?: string
): Promise<Record<string, unknown>> {
  const params = period ? `?period=${encodeURIComponent(period)}` : ''
  return request(`/api/review/report${params}`)
}

/** 获取交易记录 - GET /api/review/records */
export async function getReviewRecords(
  status?: string
): Promise<{ records: Array<Record<string, unknown>> }> {
  const params = status ? `?status=${encodeURIComponent(status)}` : ''
  return request(`/api/review/records${params}`)
}

// ==================== 追踪中心 API ====================

/** 投资逻辑 */
export interface InvestmentThesis {
  reasons?: string[]
  watch_indicators?: string[]
  exit_conditions?: string[]
  stop_loss_price?: number
  profit_target_price?: number
}

/** 创建追踪请求参数 */
export interface CreateTrackerRequest {
  stock_code: string
  stock_name: string
  thesis?: InvestmentThesis
}

/** 追踪条目 */
export interface TrackerItem {
  id: string
  stock_code: string
  stock_name: string
  active: boolean
  created_at: string
  thesis?: InvestmentThesis
  [key: string]: unknown
}

/** 信号变化记录 */
export interface SignalChange {
  id: string
  timestamp: string
  signal: string
  confidence: number
  price: number
  [key: string]: unknown
}

/** 获取追踪列表 - GET /api/trackers */
export async function getTrackers(
  activeOnly: boolean = true
): Promise<{ success: boolean; data: TrackerItem[] }> {
  const params = activeOnly ? '?active_only=true' : ''
  return request(`/api/trackers${params}`)
}

/** 创建追踪 - POST /api/trackers */
export async function createTracker(
  data: CreateTrackerRequest
): Promise<{ success: boolean; data: TrackerItem }> {
  return request('/api/trackers', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

/** 获取追踪详情 - GET /api/trackers/{id} */
export async function getTracker(
  trackerId: string
): Promise<{ success: boolean; data: TrackerItem }> {
  return request(`/api/trackers/${encodeURIComponent(trackerId)}`)
}

/** 更新投资逻辑 - PUT /api/trackers/{id}/thesis */
export async function updateThesis(
  trackerId: string,
  thesis: InvestmentThesis
): Promise<{ success: boolean }> {
  return request(
    `/api/trackers/${encodeURIComponent(trackerId)}/thesis`,
    {
      method: 'PUT',
      body: JSON.stringify(thesis),
    }
  )
}

/** 获取信号时间线 - GET /api/trackers/{id}/timeline */
export async function getSignalTimeline(
  trackerId: string,
  days: number = 30
): Promise<{ success: boolean; data: SignalChange[] }> {
  return request(
    `/api/trackers/${encodeURIComponent(trackerId)}/timeline?days=${days}`
  )
}

/** 停止追踪 - POST /api/trackers/{id}/deactivate */
export async function deactivateTracker(
  trackerId: string
): Promise<{ success: boolean }> {
  return request(
    `/api/trackers/${encodeURIComponent(trackerId)}/deactivate`,
    { method: 'POST' }
  )
}

/** 删除追踪 - DELETE /api/trackers/{id} */
export async function deleteTracker(
  trackerId: string
): Promise<{ success: boolean }> {
  return request(
    `/api/trackers/${encodeURIComponent(trackerId)}`,
    { method: 'DELETE' }
  )
}

// ==================== 历史分析 API ====================

/** 获取分析历史 - GET /api/analysis/history/{stock_code} */
export async function getAnalysisHistory(
  stockCode: string,
  limit: number = 20
): Promise<{ success: boolean; data: unknown }> {
  return request(
    `/api/analysis/history/${encodeURIComponent(stockCode)}?limit=${limit}`
  )
}

/** 对比分析 - GET /api/analysis/compare?id1=1&id2=2 */
export async function compareAnalyses(
  id1: number,
  id2: number
): Promise<{ success: boolean; data: unknown }> {
  return request(`/api/analysis/compare?id1=${id1}&id2=${id2}`)
}

/** 获取信号统计 - GET /api/analysis/statistics/{stock_code} */
export async function getSignalStatistics(
  stockCode: string,
  days: number = 30
): Promise<{ success: boolean; data: unknown }> {
  return request(
    `/api/analysis/statistics/${encodeURIComponent(stockCode)}?days=${days}`
  )
}

/** 获取评分趋势 - GET /api/analysis/trend/{stock_code} */
export async function getScoreTrend(
  stockCode: string,
  days: number = 90
): Promise<{ success: boolean; data: unknown }> {
  return request(
    `/api/analysis/trend/${encodeURIComponent(stockCode)}?days=${days}`
  )
}

/** 搜索分析 - GET /api/analysis/search?q=xxx */
export async function searchAnalyses(
  query: string,
  limit: number = 50
): Promise<{ success: boolean; data: unknown }> {
  return request(
    `/api/analysis/search?q=${encodeURIComponent(query)}&limit=${limit}`
  )
}

// ==================== 组合风险 API ====================

/** 获取组合风险 - GET /api/portfolio/risk */
export async function getPortfolioRisk(): Promise<{
  success: boolean
  data: unknown
}> {
  return request('/api/portfolio/risk')
}

// ==================== 宏观分析 API ====================

/** 宏观分析请求参数 */
export interface MacroAnalysisRequest {
  stock_code: string
  stock_name?: string
  industry?: string
  pe_ttm?: number
}

/** 宏观分析 - POST /api/macro/analyze */
export async function macroAnalyze(
  data: MacroAnalysisRequest
): Promise<{ success: boolean; data: unknown }> {
  return request('/api/macro/analyze', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ==================== 健康检查 ====================

/** 健康检查 - GET /api/health */
export async function healthCheck(): Promise<{
  status: string
  timestamp: string
  workflow_ready: boolean
}> {
  return request('/api/health')
}

// ==================== 行业轮动 API ====================

/** 行业热力图条目 */
export interface SectorHeatmapItem {
  sector_name: string
  change_pct: number
  volume_ratio: number
  capital_flow: number
  heat_score: number
}

/** 行业推荐条目 */
export interface SectorRecommendation {
  sector_name: string
  rank: number
  reason: string
  matching_stocks: string[]
  weight: number
}

/** 行业轮动分析结果 */
export interface SectorRotationResult {
  current_cycle: string
  cycle_description: string
  heatmap: SectorHeatmapItem[]
  recommendations: SectorRecommendation[]
  rotation_signal: string
  summary: string
}

/** 行业轮动分析 - GET /api/sector/rotation */
export async function getSectorRotation(): Promise<{
  success: boolean
  data: SectorRotationResult
}> {
  return request('/api/sector/rotation')
}

/** 行业热力图 - GET /api/sector/heatmap */
export async function getSectorHeatmap(): Promise<{
  success: boolean
  data: SectorHeatmapItem[]
}> {
  return request('/api/sector/heatmap')
}

// ==================== 决策系统 API ====================

/** 获取待执行决策列表 - GET /api/decisions/pending */
export async function getPendingDecisions(): Promise<any> {
  return request('/api/decisions/pending')
}

/** 获取决策历史 - GET /api/decisions/history */
export async function getDecisionHistory(stockCode?: string, limit: number = 50): Promise<any> {
  const params = new URLSearchParams()
  if (stockCode) params.set('stock_code', stockCode)
  params.set('limit', String(limit))
  return request(`/api/decisions/history?${params.toString()}`)
}

/** 执行决策 - POST /api/decisions/{decisionId}/execute */
export async function executeDecision(decisionId: string): Promise<any> {
  return request(`/api/decisions/${decisionId}/execute`, { method: 'POST' })
}

/** 取消决策 - POST /api/decisions/{decisionId}/cancel */
export async function cancelDecision(decisionId: string, reason: string = ''): Promise<any> {
  return request(`/api/decisions/${decisionId}/cancel`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

/** 复盘决策 - POST /api/decisions/{decisionId}/review */
export async function reviewDecision(decisionId: string, outcome: string, actualPnl: number): Promise<any> {
  return request(`/api/decisions/${decisionId}/review`, {
    method: 'POST',
    body: JSON.stringify({ outcome, actual_pnl: actualPnl }),
  })
}

// ==================== 调度器 API ====================

/** 获取调度器状态 - GET /api/scheduler/status */
export async function getSchedulerStatus(): Promise<any> {
  return request('/api/scheduler/status')
}

/** 启动调度器 - POST /api/scheduler/start */
export async function startScheduler(): Promise<any> {
  return request('/api/scheduler/start', { method: 'POST' })
}

/** 停止调度器 - POST /api/scheduler/stop */
export async function stopScheduler(): Promise<any> {
  return request('/api/scheduler/stop', { method: 'POST' })
}

// ==================== 通知 API ====================

/** 获取通知历史 - GET /api/notifications/history */
export async function getNotificationHistory(limit: number = 20): Promise<any> {
  return request(`/api/notifications/history?limit=${limit}`)
}

/** 获取通知渠道 - GET /api/notifications/channels */
export async function getNotificationChannels(): Promise<any> {
  return request('/api/notifications/channels')
}

/** 测试通知 - POST /api/notifications/test */
export async function testNotification(): Promise<any> {
  return request('/api/notifications/test', { method: 'POST' })
}

// ==================== 资金流向 API ====================

/** 分析资金流向 - POST /api/capital-flow/analyze */
export async function analyzeCapitalFlow(stockCode: string, stockName: string = ''): Promise<any> {
  return request('/api/capital-flow/analyze', {
    method: 'POST',
    body: JSON.stringify({ stock_code: stockCode, stock_name: stockName }),
  })
}

// ==================== 市场情绪 API ====================

/** 获取市场情绪 - GET /api/market/sentiment */
export async function getMarketSentiment(): Promise<any> {
  return request('/api/market/sentiment')
}

// ==================== 仓位计算 API ====================

/** 仓位计算请求参数 */
export interface PositionSizingParams {
  signal: string
  confidence: number
  risk_level: string
  portfolio_value: number
  stop_loss_pct: number
  stock_code?: string
}

/** 计算仓位 - POST /api/position-sizing */
export async function calculatePositionSizing(params: PositionSizingParams): Promise<any> {
  return request('/api/position-sizing', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

// ==================== WebSocket 状态 API ====================

/** 获取 WebSocket 状态 - GET /api/ws/status */
export async function getWebSocketStatus(): Promise<any> {
  return request('/api/ws/status')
}

// ==================== LLM 配置 API ====================

/** LLM 提供商配置 */
export interface LLMProviderConfig {
  provider: string
  model: string
  api_key_set: boolean
  api_key_masked: string
  status: 'connected' | 'disconnected' | 'unknown'
  [key: string]: unknown
}

/** LLM 配置响应 */
export interface LLMConfigResponse {
  providers: LLMProviderConfig[]
  [key: string]: unknown
}

/** 获取 LLM 配置 - GET /api/llm/config */
export async function getLLMConfig(): Promise<LLMConfigResponse> {
  return request('/api/llm/config')
}

/** LLM 连接测试响应 */
export interface LLMTestResponse {
  success: boolean
  message: string
  latency_ms?: number
  [key: string]: unknown
}

/** 测试 LLM 连接 - POST /api/llm/test */
export async function testLLMConnection(provider: string): Promise<LLMTestResponse> {
  return request('/api/llm/test', {
    method: 'POST',
    body: JSON.stringify({ provider }),
  })
}

// ==================== 记忆系统 API ====================

/** 用户投资画像 */
export interface MemoryProfile {
  preferred_industries: string[]
  risk_preference: string
  holding_period: string
  analysis_count: number
  [key: string]: unknown
}

/** 获取用户投资画像 - GET /api/memory/profile */
export async function getMemoryProfile(): Promise<{ success: boolean; data: MemoryProfile }> {
  return request('/api/memory/profile')
}

/** 股票历史记忆 */
export interface StockMemory {
  stock_code: string
  stock_name: string
  memories: Array<{
    date: string
    signal: string
    confidence: number
    summary: string
    [key: string]: unknown
  }>
  [key: string]: unknown
}

/** 获取股票历史记忆 - GET /api/memory/stock/{stock_code} */
export async function getStockMemory(stockCode: string): Promise<{ success: boolean; data: StockMemory }> {
  return request(`/api/memory/stock/${encodeURIComponent(stockCode)}`)
}

// ==================== MCP 工具 API ====================

/** MCP 工具参数定义 */
export interface MCPToolParameter {
  name: string
  type: string
  description: string
  required: boolean
  default?: unknown
  [key: string]: unknown
}

/** MCP 工具信息 */
export interface MCPToolInfo {
  name: string
  description: string
  parameters: MCPToolParameter[]
  [key: string]: unknown
}

/** 获取 MCP 工具列表 - GET /api/mcp/tools */
export async function getMCPTools(): Promise<{ success: boolean; tools: MCPToolInfo[] }> {
  return request('/api/mcp/tools')
}

/** MCP 工具调用请求 */
export interface MCPCallRequest {
  tool_name: string
  arguments: Record<string, unknown>
}

/** 调用 MCP 工具 - POST /api/mcp/call */
export async function callMCPTool(data: MCPCallRequest): Promise<{ success: boolean; result: unknown }> {
  return request('/api/mcp/call', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ==================== 博弈论配置 API ====================

/** 辩论配置参数 */
export interface DebateConfigParams {
  rounds: number
  enable_prisoners_dilemma: boolean
  enable_voting: boolean
  [key: string]: unknown
}

/** 配置辩论参数 - POST /api/debate/config */
export async function configureDebate(config: DebateConfigParams): Promise<{ success: boolean; message: string }> {
  return request('/api/debate/config', {
    method: 'POST',
    body: JSON.stringify(config),
  })
}

/** 辩论历史记录 */
export interface DebateHistory {
  stock_code: string
  rounds: Array<{
    round: number
    bull_argument: string
    bear_argument: string
    [key: string]: unknown
  }>
  vote_result: Record<string, unknown>
  cooperation_score: number
  nash_equilibrium: Record<string, unknown>
  [key: string]: unknown
}

/** 获取辩论历史 - GET /api/debate/history/{stock_code} */
export async function getDebateHistory(stockCode: string): Promise<{ success: boolean; data: DebateHistory }> {
  return request(`/api/debate/history/${encodeURIComponent(stockCode)}`)
}
