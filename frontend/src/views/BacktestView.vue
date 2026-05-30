<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  runBacktest,
  runStrategyBacktest,
  getBacktestStrategies,
  type BacktestRequest,
  type BacktestSignal,
  type StrategyInfo,
  type StrategyBacktestRequest,
} from '@/services/api'

type TabMode = 'strategy' | 'custom'

const mode = ref<TabMode>('strategy')
const strategies = ref<StrategyInfo[]>([])
const selectedStrategyId = ref('ma')
const strategyParams = ref<Record<string, number>>({})

const stockCode = ref('')
const positionSizePct = ref(20)
const stopLossPct = ref(7)
const takeProfitPct = ref(15)

const customSignals = ref<BacktestSignal[]>([])
const newSignalDate = ref('')
const newSignalAction = ref('buy')

const result = ref<Record<string, unknown> | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const selectedStrategy = computed(() =>
  strategies.value.find(s => s.id === selectedStrategyId.value)
)

onMounted(async () => {
  try {
    strategies.value = await getBacktestStrategies()
    if (strategies.value.length > 0) {
      selectedStrategyId.value = strategies.value[0].id
      resetStrategyParams()
    }
  } catch {
    strategies.value = [
      { id: 'ma', name: 'MA金叉死叉', description: '短期均线上穿长期均线买入', params: [] },
      { id: 'macd', name: 'MACD策略', description: 'DIF与DEA金叉买入', params: [] },
      { id: 'rsi', name: 'RSI超买超卖', description: 'RSI低于超卖线买入', params: [] },
      { id: 'boll', name: '布林带策略', description: '触及下轨买入', params: [] },
      { id: 'kdj', name: 'KDJ策略', description: 'K线上穿D线买入', params: [] },
      { id: 'combo', name: '组合策略', description: '多策略投票', params: [] },
    ]
    resetStrategyParams()
  }
})

function resetStrategyParams() {
  const s = selectedStrategy.value
  if (s) {
    const params: Record<string, number> = {}
    for (const p of s.params) {
      params[p.key] = p.default
    }
    strategyParams.value = params
  }
}

function onStrategyChange() {
  resetStrategyParams()
  result.value = null
  error.value = null
}

function addSignal() {
  if (!newSignalDate.value) return
  customSignals.value.push({ date: newSignalDate.value, action: newSignalAction.value })
  newSignalDate.value = ''
}

function removeSignal(index: number) {
  customSignals.value.splice(index, 1)
}

async function handleRun() {
  if (!stockCode.value) {
    error.value = '请填写股票代码'
    return
  }

  loading.value = true
  error.value = null
  result.value = null

  try {
    if (mode.value === 'strategy') {
      const req: StrategyBacktestRequest = {
        stock_code: stockCode.value,
        strategy_id: selectedStrategyId.value,
        strategy_params: Object.keys(strategyParams.value).length > 0 ? strategyParams.value : undefined,
        position_size_pct: positionSizePct.value / 100,
        stop_loss_pct: stopLossPct.value / 100,
        take_profit_pct: takeProfitPct.value / 100,
      }
      result.value = await runStrategyBacktest(req)
    } else {
      if (customSignals.value.length === 0) {
        error.value = '请添加至少一个交易信号'
        loading.value = false
        return
      }
      const req: BacktestRequest = {
        stock_code: stockCode.value,
        strategy_name: '自定义策略',
        signals: customSignals.value,
        position_size_pct: positionSizePct.value / 100,
        stop_loss_pct: stopLossPct.value / 100,
        take_profit_pct: takeProfitPct.value / 100,
      }
      result.value = await runBacktest(req)
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '回测失败'
  } finally {
    loading.value = false
  }
}

function fmtPct(val: unknown): string {
  const n = Number(val)
  if (isNaN(n)) return '-'
  return (n >= 0 ? '+' : '') + n.toFixed(2) + '%'
}

function fmtNum(val: unknown, decimals = 2): string {
  const n = Number(val)
  if (isNaN(n)) return '-'
  return n.toFixed(decimals)
}
</script>

<template>
  <div class="backtest-view">
    <h2 class="page-title">策略回测</h2>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <div class="card form-section">
      <div class="tab-bar">
        <button :class="['tab-btn', mode === 'strategy' ? 'active' : '']" @click="mode = 'strategy'; result = null; error = null">
          预设策略回测
        </button>
        <button :class="['tab-btn', mode === 'custom' ? 'active' : '']" @click="mode = 'custom'; result = null; error = null">
          自定义信号回测
        </button>
      </div>

      <div class="form-row">
        <div class="form-field">
          <label class="field-label">股票代码</label>
          <input v-model="stockCode" placeholder="600519.SH" class="input" />
        </div>
      </div>

      <template v-if="mode === 'strategy'">
        <div class="strategy-section">
          <label class="field-label">选择策略</label>
          <div class="strategy-grid">
            <button
              v-for="s in strategies"
              :key="s.id"
              :class="['strategy-card', selectedStrategyId === s.id ? 'selected' : '']"
              @click="selectedStrategyId = s.id; onStrategyChange()"
            >
              <div class="strategy-name">{{ s.name }}</div>
              <div class="strategy-desc">{{ s.description }}</div>
            </button>
          </div>
        </div>

        <div v-if="selectedStrategy && selectedStrategy.params.length > 0" class="params-section">
          <label class="field-label">策略参数</label>
          <div class="params-grid">
            <div v-for="p in selectedStrategy.params" :key="p.key" class="form-field">
              <label class="param-label">{{ p.label }}</label>
              <input
                type="number"
                class="input"
                :min="p.min"
                :max="p.max"
                :step="p.type === 'int' ? 1 : 0.1"
                v-model.number="strategyParams[p.key]"
              />
              <span class="param-range">{{ p.min }} ~ {{ p.max }}</span>
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <div class="signals-section">
          <h3 class="section-title">交易信号</h3>
          <div class="signal-add">
            <input v-model="newSignalDate" type="date" class="input" />
            <select v-model="newSignalAction" class="input">
              <option value="buy">买入</option>
              <option value="sell">卖出</option>
            </select>
            <button class="btn-secondary" @click="addSignal">添加信号</button>
          </div>
          <div class="signal-list">
            <div v-for="(sig, i) in customSignals" :key="i" class="signal-item">
              <span :class="sig.action === 'buy' ? 'signal-buy' : 'signal-sell'">
                {{ sig.action === 'buy' ? '买入' : '卖出' }}
              </span>
              <span class="signal-date">{{ sig.date }}</span>
              <button class="btn-remove" @click="removeSignal(i)">&times;</button>
            </div>
          </div>
        </div>
      </template>

      <div class="risk-params">
        <label class="field-label">风控参数</label>
        <div class="params-grid">
          <div class="form-field">
            <label class="param-label">仓位比例 (%)</label>
            <input type="number" class="input" min="5" max="100" step="5" v-model.number="positionSizePct" />
          </div>
          <div class="form-field">
            <label class="param-label">止损 (%)</label>
            <input type="number" class="input" min="1" max="20" step="1" v-model.number="stopLossPct" />
          </div>
          <div class="form-field">
            <label class="param-label">止盈 (%)</label>
            <input type="number" class="input" min="5" max="50" step="5" v-model.number="takeProfitPct" />
          </div>
        </div>
      </div>

      <button class="btn-primary" @click="handleRun" :disabled="loading">
        {{ loading ? '回测中...' : '开始回测' }}
      </button>
    </div>

    <div v-if="result" class="card result-section">
      <h3 class="section-title">回测结果</h3>
      <div class="result-grid">
        <div class="result-item">
          <div class="result-label">总收益率</div>
          <div class="result-value" :class="Number(result.total_return_pct) >= 0 ? 'value-positive' : 'value-negative'">
            {{ fmtPct(result.total_return_pct) }}
          </div>
        </div>
        <div class="result-item">
          <div class="result-label">年化收益</div>
          <div class="result-value" :class="Number(result.annual_return_pct) >= 0 ? 'value-positive' : 'value-negative'">
            {{ fmtPct(result.annual_return_pct) }}
          </div>
        </div>
        <div class="result-item">
          <div class="result-label">最大回撤</div>
          <div class="result-value value-negative">{{ fmtPct(result.max_drawdown_pct) }}</div>
        </div>
        <div class="result-item">
          <div class="result-label">夏普比率</div>
          <div class="result-value">{{ fmtNum(result.sharpe_ratio) }}</div>
        </div>
        <div class="result-item">
          <div class="result-label">胜率</div>
          <div class="result-value">{{ fmtNum(result.win_rate, 1) }}%</div>
        </div>
        <div class="result-item">
          <div class="result-label">盈亏比</div>
          <div class="result-value">{{ fmtNum(result.profit_factor) }}</div>
        </div>
        <div class="result-item">
          <div class="result-label">交易次数</div>
          <div class="result-value">{{ result.total_trades }}</div>
        </div>
        <div class="result-item">
          <div class="result-label">盈利/亏损</div>
          <div class="result-value">
            <span class="value-positive">{{ result.win_trades }}</span> /
            <span class="value-negative">{{ result.loss_trades }}</span>
          </div>
        </div>
        <div class="result-item">
          <div class="result-label">基准收益</div>
          <div class="result-value" :class="Number(result.benchmark_return_pct) >= 0 ? 'value-positive' : 'value-negative'">
            {{ fmtPct(result.benchmark_return_pct) }}
          </div>
        </div>
      </div>

      <div v-if="result.signal_count" class="signal-summary">
        <span>信号: {{ result.signal_count }}个 (买入{{ result.buy_signals }}, 卖出{{ result.sell_signals }})</span>
        <span v-if="result.strategy_id" class="strategy-tag">策略: {{ result.strategy_id }}</span>
      </div>

      <div class="disclaimer">
        本回测结果基于历史数据，过往表现不代表未来收益，不构成投资建议。
      </div>
    </div>
  </div>
</template>

<style scoped>
.backtest-view { padding: 20px; max-width: 960px; margin: 0 auto; }

.page-title { font-size: 20px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 20px; }
.section-title { font-size: 14px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 12px; }

.tab-bar { display: flex; gap: 0; margin-bottom: 20px; border-bottom: 2px solid var(--color-border); }
.tab-btn {
  padding: 8px 20px; background: none; border: none; cursor: pointer;
  font-size: 14px; color: var(--color-text-secondary); border-bottom: 2px solid transparent;
  margin-bottom: -2px; transition: all 0.2s;
}
.tab-btn.active { color: var(--color-accent); border-bottom-color: var(--color-accent); font-weight: 600; }
.tab-btn:hover { color: var(--color-text-primary); }

.form-section { margin-bottom: 16px; }
.form-row { display: flex; gap: 12px; margin-bottom: 16px; }
.form-field { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.field-label { font-size: 12px; color: var(--color-text-secondary); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }

.strategy-section { margin-bottom: 16px; }
.strategy-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 8px; }
.strategy-card {
  padding: 10px 12px; border: 1px solid var(--color-border); border-radius: 4px;
  cursor: pointer; background: var(--color-bg-input); transition: all 0.2s; text-align: left;
}
.strategy-card:hover { border-color: var(--color-accent); }
.strategy-card.selected { border-color: var(--color-accent); background: rgba(var(--color-accent-rgb, 59,130,246), 0.1); }
.strategy-name { font-size: 13px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 2px; }
.strategy-desc { font-size: 11px; color: var(--color-text-secondary); }

.params-section { margin-bottom: 16px; }
.params-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 8px; }
.param-label { font-size: 11px; color: var(--color-text-secondary); }
.param-range { font-size: 10px; color: var(--color-text-muted); }

.risk-params { margin-bottom: 16px; }

.signals-section { margin-bottom: 16px; }
.signal-add { display: flex; gap: 8px; margin-bottom: 10px; }
.signal-list { display: flex; flex-wrap: wrap; gap: 6px; }
.signal-item {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 10px; background: var(--color-bg-input);
  border: 1px solid var(--color-border); border-radius: 2px; font-size: 13px;
}
.signal-date { color: var(--color-text-secondary); }
.signal-buy { color: var(--color-positive); font-weight: 600; }
.signal-sell { color: var(--color-negative); font-weight: 600; }
.btn-remove { background: none; border: none; color: var(--color-text-muted); cursor: pointer; font-size: 14px; padding: 0 4px; }

.result-section { margin-top: 16px; }
.result-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.result-item { text-align: center; padding: 12px 0; border-bottom: 1px solid var(--color-border); }
.result-label { font-size: 11px; color: var(--color-text-secondary); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
.result-value { font-size: 22px; font-weight: 700; color: var(--color-text-primary); font-variant-numeric: tabular-nums; }

.value-positive { color: var(--color-positive, #22c55e); }
.value-negative { color: var(--color-negative, #ef4444); }

.signal-summary {
  margin-top: 12px; padding: 8px 12px; background: var(--color-bg-input);
  border-radius: 4px; font-size: 12px; color: var(--color-text-secondary);
  display: flex; justify-content: space-between;
}
.strategy-tag {
  padding: 2px 8px; background: rgba(var(--color-accent-rgb, 59,130,246), 0.15);
  border-radius: 2px; color: var(--color-accent); font-weight: 600;
}

.disclaimer {
  margin-top: 12px; padding: 8px 12px; font-size: 11px;
  color: var(--color-text-muted); border-top: 1px solid var(--color-border);
  font-style: italic;
}

@media (max-width: 768px) {
  .form-row { flex-direction: column; }
  .strategy-grid { grid-template-columns: repeat(2, 1fr); }
  .params-grid { grid-template-columns: 1fr; }
  .result-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
