import { createRouter, createWebHistory } from 'vue-router'
import SearchPage from '../views/SearchPage.vue'
import WatchlistPage from '../views/WatchlistPage.vue'
import MetricsPage from '../views/MetricsPage.vue'
import ChartPage from '../views/ChartPage.vue'

const routes = [
  { path: '/', name: 'search', component: SearchPage },
  { path: '/watchlist', name: 'watchlist', component: WatchlistPage },
  { path: '/metrics', name: 'metrics', component: MetricsPage },
  { path: '/charts', name: 'charts', component: ChartPage },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
