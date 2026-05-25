<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const sidebarCollapsed = ref(false)

const navItems = [
  { path: '/', name: 'analysis', icon: '🤖', label: '智能体分析' },
  { path: '/watchlist', name: 'watchlist', icon: '⭐', label: '自选股' },
  { path: '/trading', name: 'trading', icon: '💰', label: '模拟交易' },
  { path: '/backtest', name: 'backtest', icon: '📊', label: '策略回测' },
]

const currentNav = computed(() => route.name as string)

function navigateTo(path: string) {
  router.push(path)
}
</script>

<template>
  <div class="app-layout">
    <!-- 侧边导航栏 -->
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="logo" v-if="!sidebarCollapsed">
          <span class="logo-icon">🤖</span>
          <span class="logo-text">AStock<span class="logo-accent">Agents</span></span>
        </div>
        <span v-else class="logo-icon-only">🤖</span>
      </div>

      <nav class="sidebar-nav">
        <button
          v-for="item in navItems"
          :key="item.name"
          class="nav-item"
          :class="{ active: currentNav === item.name }"
          @click="navigateTo(item.path)"
          :title="item.label"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label" v-if="!sidebarCollapsed">{{ item.label }}</span>
        </button>
      </nav>

      <button class="sidebar-toggle" @click="sidebarCollapsed = !sidebarCollapsed">
        {{ sidebarCollapsed ? '→' : '←' }}
      </button>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background: #0F172A;
}

.sidebar {
  width: 220px;
  background: #1E293B;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-header {
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 64px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-icon {
  font-size: 24px;
}

.logo-icon-only {
  font-size: 24px;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #F8FAFC;
}

.logo-accent {
  color: #3B82F6;
}

.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: #94A3B8;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
  text-align: left;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #F8FAFC;
}

.nav-item.active {
  background: rgba(59, 130, 246, 0.15);
  color: #3B82F6;
}

.nav-icon {
  font-size: 18px;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}

.nav-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 12px;
}

.sidebar-toggle {
  margin: 12px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.06);
  border: none;
  border-radius: 8px;
  color: #64748B;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.sidebar-toggle:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #F8FAFC;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}

@media (max-width: 768px) {
  .sidebar {
    width: 64px;
  }
  .sidebar .nav-label {
    display: none;
  }
  .sidebar .logo-text {
    display: none;
  }
  .sidebar-toggle {
    display: none;
  }
}
</style>
