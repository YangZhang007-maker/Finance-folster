import { createRouter, createWebHistory } from 'vue-router'
import SearchPage from '../views/SearchPage.vue'
import WatchlistPage from '../views/WatchlistPage.vue'
import MetricsPage from '../views/MetricsPage.vue'
import ChartPage from '../views/ChartPage.vue'
import MoneyMachinePage from '../views/MoneyMachinePage.vue'
import BuffettPage from '../views/BuffettPage.vue'

const routes = [
  { path: '/', name: 'search', component: SearchPage },
  { path: '/watchlist', name: 'watchlist', component: WatchlistPage },
  { path: '/metrics', name: 'metrics', component: MetricsPage },
  { path: '/charts', name: 'charts', component: ChartPage },
  { path: '/money-machine', name: 'money-machine', component: MoneyMachinePage },
  { path: '/buffett', name: 'buffett', component: BuffettPage },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
