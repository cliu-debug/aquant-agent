<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getPortfolio, placeOrder, getOrders, type OrderRequest } from '@/services/api'

const portfolio = ref<any>(null)
const orders = ref<any[]>([])
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
    <h2>💰 模拟交易</h2>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <!-- 账户概览 -->
    <div v-if="portfolio" class="portfolio-summary">
      <div class="stat-card">
        <div class="stat-label">总资产</div>
        <div class="stat-value">¥{{ portfolio.total_value?.toLocaleString() }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">可用资金</div>
        <div class="stat-value">¥{{ portfolio.cash?.toLocaleString() }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">总收益率</div>
        <div class="stat-value" :class="portfolio.total_return_pct >= 0 ? 'positive' : 'negative'">
          {{ portfolio.total_return_pct >= 0 ? '+' : '' }}{{ portfolio.total_return_pct?.toFixed(2) }}%
        </div>
      </div>
    </div>

    <!-- 下单表单 -->
    <div class="order-form">
      <h3>下单</h3>
      <div class="form-row">
        <input v-model="orderForm.stock_code" placeholder="股票代码" class="input" />
        <input v-model="orderForm.stock_name" placeholder="股票名称" class="input" />
        <select v-model="orderForm.direction" class="input">
          <option value="买入">买入</option>
          <option value="卖出">卖出</option>
        </select>
        <input v-model.number="orderForm.quantity" type="number" placeholder="数量" class="input" min="100" step="100" />
        <button class="btn-primary" @click="handleOrder">确认下单</button>
      </div>
    </div>

    <!-- 持仓列表 -->
    <div v-if="portfolio?.positions?.length" class="positions">
      <h3>当前持仓</h3>
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
              <td>¥{{ pos.market_value?.toLocaleString() }}</td>
              <td :class="pos.return_pct >= 0 ? 'positive' : 'negative'">
                {{ pos.return_pct >= 0 ? '+' : '' }}{{ pos.return_pct?.toFixed(2) }}%
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
  </div>
</template>

<style scoped>
.trading-view {
  padding: 24px;
  max-width: 1000px;
  margin: 0 auto;
}

h2 { font-size: 24px; color: #F8FAFC; margin-bottom: 24px; }
h3 { font-size: 18px; color: #F8FAFC; margin-bottom: 16px; }

.portfolio-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #1E293B;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid rgba(255,255,255,0.06);
}

.stat-label { font-size: 12px; color: #64748B; margin-bottom: 8px; }
.stat-value { font-size: 24px; font-weight: 700; color: #F8FAFC; }
.stat-value.positive { color: #22C55E; }
.stat-value.negative { color: #EF4444; }

.order-form {
  background: #1E293B;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
  border: 1px solid rgba(255,255,255,0.06);
}

.form-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.input {
  padding: 8px 12px;
  background: #334155;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: #F8FAFC;
  font-size: 14px;
  outline: none;
}

.input:focus { border-color: #3B82F6; }

.btn-primary {
  padding: 8px 16px;
  background: linear-gradient(135deg, #3B82F6, #8B5CF6);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.error-msg {
  padding: 12px;
  background: rgba(239,68,68,0.1);
  border: 1px solid rgba(239,68,68,0.3);
  border-radius: 8px;
  color: #EF4444;
  margin-bottom: 16px;
}

.loading, .empty { text-align: center; color: #64748B; padding: 40px; }

.table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 10px 12px;
  text-align: left;
  font-size: 13px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

th { color: #64748B; font-weight: 600; }
td { color: #CBD5E1; }
td.positive { color: #22C55E; }
td.negative { color: #EF4444; }
</style>
