/**
 * 后端 API 服务模块
 * 封装所有与后端 FastAPI 的 HTTP 通信
 */

const API_BASE = '/api'

/** 通用请求函数 */
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
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
    const errorData = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(errorData.detail || `请求失败 (${response.status})`)
  }

  return response.json() as Promise<T>
}

// ==================== 分析 API ====================

export interface AnalyzeRequest {
  stock_code: string
  stock_name?: string
  days?: number
}

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
  price_data: Array<{ date: string; open: number; high: number; low: number; close: number; volume: number }> | null
  full_report: string | null
  timestamp: string
}

export async function analyzeStock(data: AnalyzeRequest): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>('/analyze', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ==================== 热门股票 API ====================

export interface PopularStock {
  code: string
  name: string
  industry: string
}

export async function getPopularStocks(): Promise<{ stocks: PopularStock[] }> {
  return request('/stocks/popular')
}

// ==================== 自选股 API ====================

export interface WatchlistItem {
  stock_code: string
  stock_name: string
  group?: string
  added_at?: string
  notes?: string
}

export async function getWatchlist(group?: string): Promise<{ items: WatchlistItem[]; total: number }> {
  const params = group ? `?group=${encodeURIComponent(group)}` : ''
  return request(`/watchlist${params}`)
}

export async function addToWatchlist(item: WatchlistItem): Promise<{ success: boolean; message: string }> {
  return request('/watchlist/add', {
    method: 'POST',
    body: JSON.stringify(item),
  })
}

export async function removeFromWatchlist(stockCode: string): Promise<{ success: boolean }> {
  return request(`/watchlist/${encodeURIComponent(stockCode)}`, {
    method: 'DELETE',
  })
}

export async function getWatchlistGroups(): Promise<{ groups: Array<{ name: string; count: number }> }> {
  return request('/watchlist/groups')
}

// ==================== 模拟交易 API ====================

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

export async function getPortfolio(): Promise<Portfolio> {
  return request('/trading/portfolio')
}

export async function placeOrder(order: OrderRequest): Promise<Record<string, unknown>> {
  return request('/trading/order', {
    method: 'POST',
    body: JSON.stringify(order),
  })
}

export async function getOrders(limit: number = 50): Promise<{ orders: Array<Record<string, unknown>> }> {
  return request(`/trading/orders?limit=${limit}`)
}

export async function getTradeHistory(): Promise<{ history: Record<string, unknown> }> {
  return request('/trading/history')
}

// ==================== 回测 API ====================

export interface BacktestRequest {
  stock_code: string
  strategy_name?: string
  signals: Array<{ date: string; action: string }>
  position_size_pct?: number
  stop_loss_pct?: number
  take_profit_pct?: number
}

export async function runBacktest(data: BacktestRequest): Promise<Record<string, unknown>> {
  return request('/backtest/run', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// ==================== 健康检查 ====================

export async function healthCheck(): Promise<{ status: string; timestamp: string }> {
  return request('/health')
}
