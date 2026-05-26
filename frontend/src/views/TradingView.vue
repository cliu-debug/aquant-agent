<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getPortfolio, placeOrder, getOrders, type OrderRequest, type Portfolio } from '@/services/api'

const portfolio = ref<Portfolio | null>(null)
const orders = ref<Array<Record<string, unknown>>>([])
const loading = ref(false)
const error = ref<string | null>(null)

const orderForm = ref<OrderRequest>({
  stock_code: '',
  stock_name: '',
  direction: '买入',
  quantity: 100,
  order_type: '市价单',
})

async function loadPortfolio() {
  loading.value = true
  try {
    portfolio.value = await getPortfolio()
    const ordersRes = await getOrders(20)
    orders.value = ordersRes.orders
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleOrder() {
  try {
    await placeOrder(orderForm.value)
    orderForm.value.stock_code = ''
    orderForm.value.stock_name = ''
    orderForm.value.quantity = 100
    await loadPortfolio()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '下单失败'
  }
}

onMounted(loadPortfolio)
</script>

<template>
  <div class="trading-view">
    <h2 class="page-title">模拟交易</h2>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <!-- 账户概览 -->
    <div v-if="portfolio" class="portfolio-summary">
      <div class="stat-item">
        <div class="stat-label">总资产</div>
        <div class="stat-value">{{ portfolio.total_value?.toLocaleString() }}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">可用资金</div>
        <div class="stat-value">{{ portfolio.cash?.toLocaleString() }}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">总收益率</div>
        <div class="stat-value" :class="portfolio.total_return_pct >= 0 ? 'value-positive' : 'value-negative'">
          {{ portfolio.total_return_pct >= 0 ? '+' : '' }}{{ portfolio.total_return_pct?.toFixed(2) }}%
        </div>
      </div>
    </div>

    <!-- 下单面板 -->
    <div class="order-panel card">
      <h3 class="section-title">下单</h3>
      <div class="form-grid">
        <div class="form-field">
          <label class="field-label">股票代码</label>
          <input v-model="orderForm.stock_code" placeholder="600519.SH" class="input" />
        </div>
        <div class="form-field">
          <label class="field-label">股票名称</label>
          <input v-model="orderForm.stock_name" placeholder="贵州茅台" class="input" />
        </div>
        <div class="form-field">
          <label class="field-label">方向</label>
          <select v-model="orderForm.direction" class="input">
            <option value="买入">买入</option>
            <option value="卖出">卖出</option>
          </select>
        </div>
        <div class="form-field">
          <label class="field-label">数量</label>
          <input v-model.number="orderForm.quantity" type="number" placeholder="100" class="input" min="100" step="100" />
        </div>
        <div class="form-field">
          <label class="field-label">订单类型</label>
          <select v-model="orderForm.order_type" class="input">
            <option value="市价单">市价单</option>
            <option value="限价单">限价单</option>
          </select>
        </div>
        <div class="form-field form-action">
          <button class="btn-primary" @click="handleOrder">确认下单</button>
        </div>
      </div>
    </div>

    <!-- 持仓列表 -->
    <div v-if="portfolio?.positions?.length" class="positions card">
      <h3 class="section-title">当前持仓</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>股票</th><th>数量</th><th>成本</th><th>现价</th><th>市值</th><th>盈亏</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="pos in portfolio.positions" :key="pos.stock_code">
              <td>{{ pos.stock_name || pos.stock_code }}</td>
              <td>{{ pos.quantity }}</td>
              <td>{{ pos.avg_cost?.toFixed(2) }}</td>
              <td>{{ pos.current_price?.toFixed(2) }}</td>
              <td>{{ pos.market_value?.toLocaleString() }}</td>
              <td :class="pos.return_pct >= 0 ? 'positive' : 'negative'">
                {{ pos.return_pct >= 0 ? '+' : '' }}{{ pos.return_pct?.toFixed(2) }}%
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 订单记录 -->
    <div v-if="orders.length" class="orders card">
      <h3 class="section-title">订单记录</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>时间</th><th>股票</th><th>方向</th><th>数量</th><th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in orders" :key="String(order.id)">
              <td>{{ String(order.created_at || '').substring(0, 16) }}</td>
              <td>{{ String(order.stock_name || order.stock_code) }}</td>
              <td :class="String(order.direction) === '买入' ? 'positive' : 'negative'">{{ String(order.direction) }}</td>
              <td>{{ String(order.quantity) }}</td>
              <td>{{ String(order.status) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
  </div>
</template>

<style scoped>
.trading-view {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}

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
  margin-bottom: 14px;
}

.portfolio-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-item {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 14px 16px;
}

.stat-label { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 6px; }
.stat-value { font-size: 22px; font-weight: 700; color: var(--color-text-primary); font-variant-numeric: tabular-nums; }

.order-panel {
  margin-bottom: 16px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  align-items: end;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.form-action {
  display: flex;
  align-items: flex-end;
}

.positions, .orders {
  margin-bottom: 16px;
}

@media (max-width: 768px) {
  .form-grid { grid-template-columns: 1fr 1fr; }
  .portfolio-summary { grid-template-columns: 1fr; }
}
</style>
