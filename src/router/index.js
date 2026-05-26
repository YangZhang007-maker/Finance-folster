import { createRouter, createWebHistory } from 'vue-router'
import SearchPage from '../views/SearchPage.vue'
import WatchlistPage from '../views/WatchlistPage.vue'
import MetricsPage from '../views/MetricsPage.vue'

const routes = [
  { path: '/', name: 'search', component: SearchPage },
  { path: '/watchlist', name: 'watchlist', component: WatchlistPage },
  { path: '/metrics', name: 'metrics', component: MetricsPage },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
