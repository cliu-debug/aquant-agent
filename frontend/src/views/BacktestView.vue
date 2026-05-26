<script setup lang="ts">
import { ref } from 'vue'
import { runBacktest, type BacktestRequest, type BacktestSignal } from '@/services/api'

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
const result = ref<Record<string, unknown> | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

function addSignal() {
  if (!newSignalDate.value) return
  form.value.signals.push({ date: newSignalDate.value, action: newSignalAction.value } as BacktestSignal)
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
    <h2 class="page-title">策略回测</h2>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <div class="card form-section">
      <div class="form-row">
        <div class="form-field">
          <label class="field-label">股票代码</label>
          <input v-model="form.stock_code" placeholder="600519.SH" class="input" />
        </div>
        <div class="form-field">
          <label class="field-label">策略名称</label>
          <input v-model="form.strategy_name" placeholder="自定义策略" class="input" />
        </div>
      </div>

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
          <div v-for="(sig, i) in form.signals" :key="i" class="signal-item">
            <span :class="sig.action === 'buy' ? 'signal-buy' : 'signal-sell'">
              {{ sig.action === 'buy' ? '买入' : '卖出' }}
            </span>
            <span class="signal-date">{{ sig.date }}</span>
            <button class="btn-remove" @click="removeSignal(i)">&times;</button>
          </div>
        </div>
      </div>

      <div class="params-grid">
        <div class="form-field">
          <label class="field-label">仓位比例 (%)</label>
          <input type="number" class="input" min="5" max="100" step="5"
            :value="(form.position_size_pct! * 100).toFixed(0)"
            @input="form.position_size_pct = ($event.target as HTMLInputElement).valueAsNumber / 100"
          />
        </div>
        <div class="form-field">
          <label class="field-label">止损 (%)</label>
          <input type="number" class="input" min="1" max="20" step="1"
            :value="(form.stop_loss_pct! * 100).toFixed(0)"
            @input="form.stop_loss_pct = ($event.target as HTMLInputElement).valueAsNumber / 100"
          />
        </div>
        <div class="form-field">
          <label class="field-label">止盈 (%)</label>
          <input type="number" class="input" min="5" max="50" step="5"
            :value="(form.take_profit_pct! * 100).toFixed(0)"
            @input="form.take_profit_pct = ($event.target as HTMLInputElement).valueAsNumber / 100"
          />
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
          <div class="result-value" :class="(result.total_return_pct as number) >= 0 ? 'value-positive' : 'value-negative'">
            {{ (result.total_return_pct as number) >= 0 ? '+' : '' }}{{ (result.total_return_pct as number)?.toFixed(2) }}%
          </div>
        </div>
        <div class="result-item">
          <div class="result-label">最大回撤</div>
          <div class="result-value value-negative">{{ (result.max_drawdown_pct as number)?.toFixed(2) }}%</div>
        </div>
        <div class="result-item">
          <div class="result-label">胜率</div>
          <div class="result-value">{{ (result.win_rate as number)?.toFixed(2) }}%</div>
        </div>
        <div class="result-item">
          <div class="result-label">交易次数</div>
          <div class="result-value">{{ result.total_trades }}</div>
        </div>
        <div class="result-item">
          <div class="result-label">夏普比率</div>
          <div class="result-value">{{ (result.sharpe_ratio as number)?.toFixed(2) || '-' }}</div>
        </div>
        <div class="result-item">
          <div class="result-label">盈亏比</div>
          <div class="result-value">{{ (result.profit_loss_ratio as number)?.toFixed(2) || '-' }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.backtest-view { padding: 20px; max-width: 900px; margin: 0 auto; }

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 20px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 12px;
}

.form-section { margin-bottom: 16px; }

.form-row { display: flex; gap: 12px; margin-bottom: 16px; }
.form-field { display: flex; flex-direction: column; gap: 4px; flex: 1; }
.field-label { font-size: 12px; color: var(--color-text-secondary); }

.signals-section { margin-bottom: 16px; }
.signal-add { display: flex; gap: 8px; margin-bottom: 10px; }
.signal-list { display: flex; flex-wrap: wrap; gap: 6px; }
.signal-item {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 10px; background: var(--color-bg-input);
  border: 1px solid var(--color-border); border-radius: 2px; font-size: 13px;
}
.signal-date { color: var(--color-text-secondary); }
.signal-buy { color: var(--color-positive); }
.signal-sell { color: var(--color-negative); }
.btn-remove { background: none; border: none; color: var(--color-text-muted); cursor: pointer; font-size: 14px; padding: 0 4px; }

.params-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }

.result-section { margin-top: 16px; }
.result-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.result-item { text-align: center; padding: 12px 0; }
.result-label { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 6px; }
.result-value { font-size: 22px; font-weight: 700; color: var(--color-text-primary); font-variant-numeric: tabular-nums; }

@media (max-width: 768px) {
  .form-row { flex-direction: column; }
  .params-grid { grid-template-columns: 1fr; }
  .result-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
