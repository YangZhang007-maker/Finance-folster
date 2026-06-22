import { createRouter, createWebHistory } from 'vue-router'
import SearchPage from '../views/watchlist/SearchPage.vue'
import WatchlistPage from '../views/watchlist/WatchlistPage.vue'
import MetricsPage from '../views/metrics/MetricsPage.vue'
import TrendChartPage from '../views/charts/TrendChartPage.vue'
import MoneyMachinePage from '../views/money-machine/MoneyMachinePage.vue'
import BuffettPage from '../views/buffett/BuffettPage.vue'
import SectorInsightPage from '../views/sector-insight/SectorInsightPage.vue'

const routes = [
  { path: '/', name: 'search', component: SearchPage },
  { path: '/watchlist', name: 'watchlist', component: WatchlistPage },
  { path: '/metrics', name: 'metrics', component: MetricsPage },
  { path: '/charts', name: 'charts', component: TrendChartPage },
  { path: '/money-machine', name: 'money-machine', component: MoneyMachinePage },
  { path: '/buffett', name: 'buffett', component: BuffettPage },
  { path: '/sector-insight', name: 'sector-insight', component: SectorInsightPage },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})