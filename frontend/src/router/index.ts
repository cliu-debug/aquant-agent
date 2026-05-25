import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'analysis',
      component: () => import('@/views/AnalysisView.vue'),
      meta: { title: '智能体分析', icon: '🤖' },
    },
    {
      path: '/watchlist',
      name: 'watchlist',
      component: () => import('@/views/WatchlistView.vue'),
      meta: { title: '自选股', icon: '⭐' },
    },
    {
      path: '/trading',
      name: 'trading',
      component: () => import('@/views/TradingView.vue'),
      meta: { title: '模拟交易', icon: '💰' },
    },
    {
      path: '/backtest',
      name: 'backtest',
      component: () => import('@/views/BacktestView.vue'),
      meta: { title: '策略回测', icon: '📊' },
    },
  ],
})

router.beforeEach((to) => {
  document.title = `${to.meta.title || 'AStockAgents'} - AStockAgents`
})

export default router
