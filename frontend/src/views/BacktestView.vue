<script setup lang="ts">
import { ref } from 'vue'
import { runBacktest, type BacktestRequest } from '@/services/api'

const form = ref<BacktestRequest>({
  stock_code: '',
  strategy_name: '自定义策略',
  signals: [],
  position_size_pct: 0.2,
  stop_loss_pct: 0.07,
  take_profit_pct: 0.15,
})

const newSignalDate = ref('')
const newSignalAction = ref('buy')
const result = ref<any>(null)
const loading = ref(false)
const error = ref<string | null>(null)

function addSignal() {
  if (!newSignalDate.value) return
  form.value.signals.push({ date: newSignalDate.value, action: newSignalAction.value })
  newSignalDate.value = ''
}

function removeSignal(index: number) {
  form.value.signals.splice(index, 1)
}

async function handleRun() {
  if (!form.value.stock_code || form.value.signals.length === 0) {
    error.value = '请填写股票代码并添加至少一个交易信号'
    return
  }
  loading.value = true
  error.value = null
  result.value = null
  try {
    result.value = await runBacktest(form.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '回测失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="backtest-view">
    <h2>📊 策略回测</h2>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <div class="form-section">
      <div class="form-row">
        <input v-model="form.stock_code" placeholder="股票代码 (如 600519.SH)" class="input" />
        <input v-model="form.strategy_name" placeholder="策略名称" class="input" />
      </div>

      <div class="signals-section">
        <h3>交易信号</h3>
        <div class="signal-add">
          <input v-model="newSignalDate" type="date" class="input" />
          <select v-model="newSignalAction" class="input">
            <option value="buy">买入</option>
            <option value="sell">卖出</option>
          </select>
          <button class="btn-secondary" @click="addSignal">添加信号</button>
        </div>
        <div class="signal-list">
          <div v-for="(sig, i) in form.signals" :key="i" class="signal-item">
            <span :class="sig.action === 'buy' ? 'buy' : 'sell'">{{ sig.action === 'buy' ? '📈 买入' : '📉 卖出' }}</span>
            <span class="signal-date">{{ sig.date }}</span>
            <button class="btn-remove" @click="removeSignal(i)">✕</button>
          </div>
        </div>
      </div>

      <div class="form-row">
        <label class="label">仓位比例: {{ (form.position_size_pct! * 100).toFixed(0) }}%</label>
        <input v-model.number="form.position_size_pct" type="range" min="0.05" max="1" step="0.05" />
        <label class="label">止损: {{ (form.stop_loss_pct! * 100).toFixed(0) }}%</label>
        <input v-model.number="form.stop_loss_pct" type="range" min="0.01" max="0.2" step="0.01" />
        <label class="label">止盈: {{ (form.take_profit_pct! * 100).toFixed(0) }}%</label>
        <input v-model.number="form.take_profit_pct" type="range" min="0.05" max="0.5" step="0.05" />
      </div>

      <button class="btn-primary" @click="handleRun" :disabled="loading">
        {{ loading ? '回测中...' : '🚀 开始回测' }}
      </button>
    </div>

    <div v-if="result" class="result-section">
      <h3>回测结果</h3>
      <div class="result-grid">
        <div class="result-card">
          <div class="result-label">总收益率</div>
          <div class="result-value" :class="result.total_return_pct >= 0 ? 'positive' : 'negative'">
            {{ result.total_return_pct >= 0 ? '+' : '' }}{{ result.total_return_pct?.toFixed(2) }}%
          </div>
        </div>
        <div class="result-card">
          <div class="result-label">最大回撤</div>
          <div class="result-value negative">{{ result.max_drawdown_pct?.toFixed(2) }}%</div>
        </div>
        <div class="result-card">
          <div class="result-label">胜率</div>
          <div class="result-value">{{ result.win_rate?.toFixed(2) }}%</div>
        </div>
        <div class="result-card">
          <div class="result-label">交易次数</div>
          <div class="result-value">{{ result.total_trades }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.backtest-view { padding: 24px; max-width: 900px; margin: 0 auto; }
h2 { font-size: 24px; color: #F8FAFC; margin-bottom: 24px; }
h3 { font-size: 18px; color: #F8FAFC; margin-bottom: 16px; }

.form-section {
  background: #1E293B;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
  border: 1px solid rgba(255,255,255,0.06);
}

.form-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 16px; }
.input { padding: 8px 12px; background: #334155; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #F8FAFC; font-size: 14px; outline: none; }
.input:focus { border-color: #3B82F6; }
.label { color: #94A3B8; font-size: 13px; min-width: 100px; }

.signals-section { margin-bottom: 16px; }
.signal-add { display: flex; gap: 8px; margin-bottom: 12px; }
.signal-list { display: flex; flex-wrap: wrap; gap: 8px; }
.signal-item { display: flex; align-items: center; gap: 8px; padding: 6px 12px; background: #334155; border-radius: 8px; font-size: 13px; }
.signal-date { color: #94A3B8; }
.buy { color: #22C55E; }
.sell { color: #EF4444; }

.btn-primary { padding: 10px 24px; background: linear-gradient(135deg, #3B82F6, #8B5CF6); color: white; border: none; border-radius: 8px; font-size: 14px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary { padding: 8px 16px; background: #334155; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; color: #F8FAFC; font-size: 14px; cursor: pointer; }
.btn-remove { background: none; border: none; color: #64748B; cursor: pointer; font-size: 14px; }

.error-msg { padding: 12px; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); border-radius: 8px; color: #EF4444; margin-bottom: 16px; }

.result-section { background: #1E293B; border-radius: 12px; padding: 20px; border: 1px solid rgba(255,255,255,0.06); }
.result-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.result-card { text-align: center; }
.result-label { font-size: 12px; color: #64748B; margin-bottom: 8px; }
.result-value { font-size: 24px; font-weight: 700; color: #F8FAFC; }
.result-value.positive { color: #22C55E; }
.result-value.negative { color: #EF4444; }
</style>
