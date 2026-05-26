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
      <h2 class="page-title">自选股</h2>
      <div class="add-form">
        <input v-model="newCode" placeholder="股票代码" class="input" />
        <input v-model="newName" placeholder="股票名称" class="input" />
        <button class="btn-primary" @click="handleAdd">添加</button>
      </div>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>

    <div v-if="loading" class="loading-state">加载中...</div>

    <div v-else-if="items.length === 0" class="empty-state">暂无自选股，请添加</div>

    <div v-else class="card">
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>股票代码</th>
              <th>股票名称</th>
              <th>添加时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.stock_code">
              <td class="code-cell">{{ item.stock_code }}</td>
              <td>{{ item.stock_name }}</td>
              <td class="time-cell">{{ item.added_at ? String(item.added_at).substring(0, 10) : '-' }}</td>
              <td>
                <button class="btn-danger" @click="handleRemove(item.stock_code)">移除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.watchlist-view {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 14px;
}

.add-form {
  display: flex;
  gap: 8px;
}

.code-cell {
  color: var(--color-accent);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.time-cell {
  color: var(--color-text-secondary);
  font-size: 12px;
}

@media (max-width: 768px) {
  .add-form { flex-wrap: wrap; }
}
</style>
