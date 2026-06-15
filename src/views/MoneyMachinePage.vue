<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">赚钱机器指标分析</h1>
    </div>

    <!-- Stock search -->
    <div class="search-box" style="margin-bottom: 16px">
      <span class="search-icon">&#128269;</span>
      <input v-model="searchQuery" class="input" placeholder="输入股票代码或名称搜索..." @input="onSearchInput" />
    </div>

    <!-- Search results dropdown -->
    <div v-if="searchResults.length > 0 && !selectedStock" class="card" style="margin-bottom: 24px; max-height: 300px; overflow-y: auto">
      <div v-for="stock in searchResults" :key="stock.code" style="padding: 10px 14px; cursor: pointer; border-bottom: 1px solid var(--border); transition: background 0.1s"
        @click="selectStock(stock)" @mouseenter="e => e.target.style.background = 'var(--bg)'" @mouseleave="e => e.target.style.background = 'transparent'">
        <strong>{{ stock.name }}</strong>
        <span style="color:var(--text-secondary);margin-left:8px;font-size:13px">{{ stock.code }}</span>
      </div>
    </div>

    <div v-if="loading" class="loading"><div class="spinner"></div></div>

    <!-- Charts -->
    <template v-if="selectedStock && chartData && chartData.length > 0">
      <div class="card" style="margin-bottom: 24px">
        <div style="display:flex;align-items:center;gap:12px">
          <h2 style="margin:0">{{ selectedStock.name }}</h2>
          <span style="color:var(--text-secondary)">{{ selectedStock.code }}</span>
          <button class="btn btn-sm" @click="resetSearch">换股票</button>
        </div>
      </div>

      <div class="charts-grid-2x3">
        <!-- Chart 1: 资本开支 -->
        <div class="chart-card">
          <h3 class="chart-title">资本开支趋势</h3>
          <div class="chart-wrap">
            <Bar :data="chart1Data" :options="chart1Options" />
          </div>
        </div>

        <!-- Chart 2: 净利润 vs 同比增速 -->
        <div class="chart-card">
          <h3 class="chart-title">净利润 vs 同比增速</h3>
          <div class="chart-wrap">
            <Bar :data="chart2Data" :options="chart2Options" />
          </div>
        </div>

        <!-- Chart 3: 有效资产收益率 -->
        <div class="chart-card">
          <h3 class="chart-title">有效资产收益率</h3>
          <p class="chart-subtitle">= 归母净利润 / (总资产 − 货币资金 − 商誉) × 100</p>
          <div class="chart-wrap">
            <Line :data="chart3Data" :options="chart3Options" />
          </div>
        </div>

        <!-- Chart 4: 硬朗度利润 -->
        <div class="chart-card">
          <h3 class="chart-title">硬朗度利润（自由现金流）</h3>
          <div class="chart-wrap">
            <Bar :data="chart4Data" :options="chart4Options" />
          </div>
        </div>

        <!-- Chart 5: 锚定资产构成 -->
        <div class="chart-card">
          <h3 class="chart-title">锚定资产构成</h3>
          <div class="chart-wrap">
            <Bar :data="chart5Data" :options="chart5Options" />
          </div>
        </div>

        <!-- Chart 6: 锚定资产占比 -->
        <div class="chart-card">
          <h3 class="chart-title">锚定资产占总资产比</h3>
          <div class="chart-wrap">
            <Line :data="chart6Data" :options="chart6Options" />
          </div>
        </div>
      </div>
    </template>

    <div v-if="!selectedStock && !loading && searchResults.length === 0 && !searched" class="empty-state">
      <h3>搜索股票查看赚钱机器指标</h3>
      <p>输入股票代码或名称</p>
    </div>

    <div v-if="selectedStock && (!chartData || chartData.length === 0) && !loading" class="empty-state">
      <h3>{{ selectedStock.name }} 暂无历史数据</h3>
      <p>数据正在同步中，请稍后查看</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Bar, Line } from 'vue-chartjs'
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, BarElement, Title, Tooltip, Legend, Filler
} from 'chart.js'
import { getAnnualFinancialsV2, searchCompanies } from '../lib/supabase.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, Filler)

const searchQuery = ref('')
const searchResults = ref([])
const searched = ref(false)
const selectedStock = ref(null)
const loading = ref(false)
const annualData = ref([])
let searchTimer = null

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    if (!searchQuery.value.trim()) { searchResults.value = []; searched.value = false; return }
    searched.value = true
    try { searchResults.value = await searchCompanies(searchQuery.value.trim()) } catch { searchResults.value = [] }
  }, 300)
}

async function selectStock(stock) {
  selectedStock.value = stock; searchResults.value = []; searchQuery.value = ''; loading.value = true
  try { annualData.value = await getAnnualFinancialsV2(stock.code) } catch { annualData.value = [] }
  finally { loading.value = false }
}

function resetSearch() { selectedStock.value = null; annualData.value = [] }

const chartData = computed(() => {
  if (!annualData.value || annualData.value.length === 0) return null
  return annualData.value.filter(d => {
    const year = d.report_date?.substring(0, 4)
    return year >= '2016' && year <= '2025'
  })
})

const labels = computed(() => {
  if (!chartData.value) return []
  return chartData.value.map(d => d.report_date?.substring(0, 4) || '')
})

// ---- Common options ----
const baseOptions = (unit, extra = {}) => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          const val = ctx.raw
          if (val == null) return ''
          return ctx.dataset.label ? `${ctx.dataset.label}: ${val.toFixed(2)}${unit}` : `${val.toFixed(2)}${unit}`
        }
      }
    },
    ...extra.plugins,
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: '#666', font: { size: 12 } },
      border: { display: true, color: '#ccc' },
    },
    y: {
      position: 'left',
      grid: { color: '#e8e8e8', drawTicks: false },
      ticks: { color: '#999', font: { size: 11 },
        callback: (val) => val + unit
      },
      border: { display: false },
      beginAtZero: false,
    },
  },
})

// Convert 元 to 万元
function toWan(val) {
  if (val == null) return null
  return Number((Number(val) / 10000).toFixed(0))
}

// ---- Chart 1: 资本开支 ----
const chart1Data = computed(() => ({
  labels: labels.value,
  datasets: [{
    label: '资本开支',
    data: chartData.value.map(d => toWan(d.capex)),
    backgroundColor: '#2E86AB',
    borderColor: '#2E86AB',
    borderRadius: 4,
    barPercentage: 0.6,
  }],
}))

const chart1Options = computed(() => ({
  ...baseOptions('万'),
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `资本开支: ${ctx.raw?.toLocaleString()} 万元`
      }
    }
  },
}))

// ---- Chart 2: 净利润 vs 同比增速 (dual axis) ----
const chart2Data = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      type: 'bar',
      label: '归母净利润',
      data: chartData.value.map(d => toWan(d.parent_net_profit)),
      backgroundColor: '#2CA02C',
      borderRadius: 4,
      barPercentage: 0.6,
      yAxisID: 'y',
      order: 2,
    },
    {
      type: 'line',
      label: '同比增速',
      data: chartData.value.map(d => d.net_profit_yoy != null ? Number(d.net_profit_yoy) : null),
      borderColor: '#D62728',
      backgroundColor: '#D62728',
      fill: false,
      tension: 0.3,
      pointRadius: 5,
      pointBackgroundColor: '#D62728',
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      yAxisID: 'y1',
      order: 1,
    },
  ],
}))

const chart2Options = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: { boxWidth: 12, padding: 8, font: { size: 11 } },
    },
    tooltip: {
      callbacks: {
        label: (ctx) => {
          if (ctx.dataset.yAxisID === 'y1') return `同比增速: ${ctx.raw?.toFixed(2)}%`
          return `归母净利润: ${ctx.raw?.toLocaleString()} 万元`
        }
      }
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: '#666', font: { size: 12 } },
      border: { display: true, color: '#ccc' },
    },
    y: {
      type: 'linear',
      position: 'left',
      grid: { color: '#e8e8e8', drawTicks: false },
      ticks: { color: '#999', font: { size: 11 }, callback: (val) => val + '万' },
      border: { display: false },
      beginAtZero: false,
      title: { display: true, text: '万元', color: '#999', font: { size: 11 } },
    },
    y1: {
      type: 'linear',
      position: 'right',
      grid: { drawOnChartArea: false },
      ticks: { color: '#D62728', font: { size: 11 }, callback: (val) => val + '%' },
      border: { display: false },
      beginAtZero: false,
      title: { display: true, text: '%', color: '#D62728', font: { size: 11 } },
    },
  },
}))

// ---- Chart 3: 有效资产收益率 ----
const chart3Data = computed(() => ({
  labels: labels.value,
  datasets: [{
    label: '有效资产收益率',
    data: chartData.value.map(d => d.effective_asset_return != null ? Number(d.effective_asset_return) : null),
    borderColor: '#FF8C00',
    backgroundColor: '#FF8C00',
    fill: false,
    tension: 0.3,
    pointRadius: 5,
    pointBackgroundColor: '#FF8C00',
    pointBorderColor: '#fff',
    pointBorderWidth: 2,
  }],
}))

const chart3Options = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `有效资产收益率: ${ctx.raw?.toFixed(2)}%`
      }
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: '#666', font: { size: 12 } },
      border: { display: true, color: '#ccc' },
    },
    y: {
      position: 'left',
      grid: { color: '#e8e8e8', drawTicks: false },
      ticks: { color: '#999', font: { size: 11 }, callback: (val) => val + '%' },
      border: { display: false },
      beginAtZero: false,
    },
  },
}))

// ---- Chart 4: 硬朗度利润 (positive/negative colored bars) ----
const chart4Data = computed(() => ({
  labels: labels.value,
  datasets: [{
    label: '硬朗度利润',
    data: chartData.value.map(d => toWan(d.hard_profit)),
    backgroundColor: chartData.value.map(d => {
      const val = toWan(d.hard_profit)
      return val >= 0 ? '#2CA02C' : '#D62728'
    }),
    borderColor: chartData.value.map(d => {
      const val = toWan(d.hard_profit)
      return val >= 0 ? '#2CA02C' : '#D62728'
    }),
    borderRadius: 4,
    barPercentage: 0.6,
  }],
}))

const chart4Options = computed(() => ({
  ...baseOptions('万'),
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `硬朗度利润: ${ctx.raw?.toLocaleString()} 万元`
      }
    },
  },
}))

// ---- Chart 5: 锚定资产构成 (stacked bar) ----
const chart5Data = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      label: '固定资产',
      data: chartData.value.map(d => toWan(d.fixed_asset)),
      backgroundColor: '#1F77B4',
      borderRadius: 0,
      barPercentage: 0.6,
    },
    {
      label: '在建工程',
      data: chartData.value.map(d => toWan(d.construction_in_progress)),
      backgroundColor: '#FF7F0E',
      borderRadius: 0,
      barPercentage: 0.6,
    },
    {
      label: '存货',
      data: chartData.value.map(d => toWan(d.inventory)),
      backgroundColor: '#2CA02C',
      borderRadius: { topLeft: 4, topRight: 4 },
      barPercentage: 0.6,
    },
  ],
}))

const chart5Options = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: { boxWidth: 12, padding: 8, font: { size: 11 } },
    },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ${ctx.raw?.toLocaleString()} 万元`
      }
    },
  },
  scales: {
    x: {
      stacked: true,
      grid: { display: false },
      ticks: { color: '#666', font: { size: 12 } },
      border: { display: true, color: '#ccc' },
    },
    y: {
      stacked: true,
      position: 'left',
      grid: { color: '#e8e8e8', drawTicks: false },
      ticks: { color: '#999', font: { size: 11 }, callback: (val) => val + '万' },
      border: { display: false },
      beginAtZero: false,
    },
  },
}))

// ---- Chart 6: 锚定资产占比 ----
const chart6Data = computed(() => ({
  labels: labels.value,
  datasets: [{
    label: '锚定资产占比',
    data: chartData.value.map(d => d.anchor_asset_ratio != null ? Number(d.anchor_asset_ratio) : null),
    borderColor: '#9467BD',
    backgroundColor: '#9467BD',
    fill: false,
    tension: 0.3,
    pointRadius: 5,
    pointBackgroundColor: '#9467BD',
    pointBorderColor: '#fff',
    pointBorderWidth: 2,
  }],
}))

const chart6Options = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `锚定资产占比: ${ctx.raw?.toFixed(2)}%`
      }
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: '#666', font: { size: 12 } },
      border: { display: true, color: '#ccc' },
    },
    y: {
      position: 'left',
      min: 0,
      max: 100,
      grid: { color: '#e8e8e8', drawTicks: false },
      ticks: { color: '#999', font: { size: 11 }, callback: (val) => val + '%' },
      border: { display: false },
    },
  },
}))
</script>

<style scoped>
.charts-grid-2x3 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.chart-card {
  background: var(--bg-white);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow);
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 4px 0;
  color: #111;
}

.chart-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0 0 12px 0;
}

.chart-wrap {
  height: 350px;
}

@media (max-width: 900px) {
  .charts-grid-2x3 {
    grid-template-columns: 1fr;
  }
}
</style>