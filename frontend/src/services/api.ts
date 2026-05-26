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
