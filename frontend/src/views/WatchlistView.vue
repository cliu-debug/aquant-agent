<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getWatchlist, addToWatchlist, removeFromWatchlist, type WatchlistItem } from '@/services/api'

const items = ref<WatchlistItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const newCode = ref('')
const newName = ref('')

async function loadWatchlist() {
  loading.value = true
  error.value = null
  try {
    const res = await getWatchlist()
    items.value = res.items
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleAdd() {
  if (!newCode.value.trim()) return
  try {
    await addToWatchlist({ stock_code: newCode.value.trim(), stock_name: newName.value.trim() })
    newCode.value = ''
    newName.value = ''
    await loadWatchlist()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '添加失败'
  }
}

async function handleRemove(code: string) {
  try {
    await removeFromWatchlist(code)
    await loadWatchlist()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '删除失败'
  }
}

onMounted(loadWatchlist)
</script>

<template>
  <div class="watchlist-view">
    <div class="page-header">
      <h2>⭐ 自选股</h2>
      <div class="add-form">
        <input v-model="newCode" placeholder="股票代码" class="input" />
        <input v-model="newName" placeholder="股票名称" class="input" />
        <button class="btn-primary" @click="handleAdd">添加</button>
      </div>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="items.length === 0" class="empty">暂无自选股，请添加</div>

    <div v-else class="stock-list">
      <div v-for="item in items" :key="item.stock_code" class="stock-item">
        <div class="stock-info">
          <span class="stock-code">{{ item.stock_code }}</span>
          <span class="stock-name">{{ item.stock_name }}</span>
        </div>
        <button class="btn-remove" @click="handleRemove(item.stock_code)">移除</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.watchlist-view {
  padding: 24px;
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 24px;
  color: #F8FAFC;
  margin-bottom: 16px;
}

.add-form {
  display: flex;
  gap: 8px;
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

.input:focus {
  border-color: #3B82F6;
}

.btn-primary {
  padding: 8px 16px;
  background: linear-gradient(135deg, #3B82F6, #8B5CF6);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.9;
}

.error-msg {
  padding: 12px;
  background: rgba(239,68,68,0.1);
  border: 1px solid rgba(239,68,68,0.3);
  border-radius: 8px;
  color: #EF4444;
  margin-bottom: 16px;
}

.loading, .empty {
  text-align: center;
  color: #64748B;
  padding: 40px;
}

.stock-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stock-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #1E293B;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.06);
}

.stock-info {
  display: flex;
  gap: 12px;
  align-items: center;
}

.stock-code {
  color: #3B82F6;
  font-weight: 600;
  font-size: 14px;
}

.stock-name {
  color: #94A3B8;
  font-size: 14px;
}

.btn-remove {
  padding: 4px 12px;
  background: rgba(239,68,68,0.1);
  border: 1px solid rgba(239,68,68,0.2);
  border-radius: 6px;
  color: #EF4444;
  font-size: 12px;
  cursor: pointer;
}

.btn-remove:hover {
  background: rgba(239,68,68,0.2);
}
</style>
