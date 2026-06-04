<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">趋势图表</h1>
    </div>

    <!-- Stock search -->
    <div class="search-box" style="margin-bottom: 16px">
      <span class="search-icon">&#128269;</span>
      <input
        v-model="searchQuery"
        class="input"
        placeholder="输入股票代码或名称搜索..."
        @input="onSearchInput"
      />
    </div>

    <!-- Search results dropdown -->
    <div v-if="searchResults.length > 0 && !selectedStock" class="card" style="margin-bottom: 24px; max-height: 300px; overflow-y: auto">
      <div
        v-for="stock in searchResults"
        :key="stock.code"
        style="padding: 10px 14px; cursor: pointer; border-bottom: 1px solid var(--border); transition: background 0.1s"
        @click="selectStock(stock)"
        @mouseenter="e => e.target.style.background = 'var(--bg)'"
        @mouseleave="e => e.target.style.background = 'transparent'"
      >
        <strong>{{ stock.name }}</strong>
        <span style="color:var(--text-secondary);margin-left:8px;font-size:13px">{{ stock.code }}</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading"><div class="spinner"></div></div>

    <!-- Charts -->
    <template v-if="selectedStock && chartData">
      <div class="card" style="margin-bottom: 16px">
        <div style="display:flex;align-items:center;gap:12px">
          <h2 style="margin:0">{{ selectedStock.name }}</h2>
          <span style="color:var(--text-secondary)">{{ selectedStock.code }}</span>
          <button class="btn btn-sm" @click="resetSearch">换股票</button>
        </div>
      </div>

      <!-- Line chart: ROE, 毛利率, 净利率 -->
      <div class="card" style="margin-bottom: 16px">
        <h3 style="margin-bottom: 16px">盈利能力趋势（折线图）</h3>
        <div style="height: 350px">
          <Line v-if="percentageChartData" :data="percentageChartData" :options="lineOptions" />
        </div>
      </div>

      <!-- Bar chart: 毛利润, 净利润, 总市值 -->
      <div class="card" style="margin-bottom: 16px">
        <h3 style="margin-bottom: 16px">利润与市值（条形图，单位：元）</h3>
        <div style="height: 350px">
          <Bar v-if="absoluteChartData" :data="absoluteChartData" :options="barOptions" />
        </div>
      </div>
    </template>

    <!-- Empty state -->
    <div v-if="!selectedStock && !loading && searchResults.length === 0 && !searched" class="empty-state">
      <h3>搜索股票查看 10 年财务趋势</h3>
      <p>输入股票代码或名称</p>
    </div>

    <div v-if="selectedStock && !chartData && !loading" class="empty-state">
      <h3>{{ selectedStock.name }} 暂无历史数据</h3>
      <p>数据正在同步中，请稍后查看</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Line, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement,
  LineElement, BarElement, Title, Tooltip, Legend, Filler
} from 'chart.js'
import { getAnnualFinancials, searchCompanies } from '../lib/supabase.js'

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
    if (!searchQuery.value.trim()) {
      searchResults.value = []
      searched.value = false
      return
    }
    searched.value = true
    try {
      searchResults.value = await searchCompanies(searchQuery.value.trim())
    } catch {
      searchResults.value = []
    }
  }, 300)
}

async function selectStock(stock) {
  selectedStock.value = stock
  searchResults.value = []
  searchQuery.value = ''
  loading.value = true

  try {
    annualData.value = await getAnnualFinancials(stock.code)
  } catch {
    annualData.value = []
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  selectedStock.value = null
  annualData.value = []
}

// Data for percentage charts (ROE, gross margin, net margin) - line chart
const chartData = computed(() => {
  if (!annualData.value || annualData.value.length === 0) return null
  // Use last 10 years
  const data = annualData.value.slice(-10)
  return data
})

// Format large numbers
function fmtAmount(val) {
  if (val == null) return null
  const n = Number(val)
  if (isNaN(n)) return null
  return n
}

// Percentage line chart
const percentageChartData = computed(() => {
  if (!chartData.value) return null
  const labels = chartData.value.map(d => d.report_date?.substring(0, 4) || '')
  return {
    labels,
    datasets: [
      {
        label: 'ROE (%)',
        data: chartData.value.map(d => d.roe != null ? Number(d.roe) : null),
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37,99,235,0.1)',
        fill: false,
        tension: 0.3,
        pointRadius: 4,
      },
      {
        label: '毛利率 (%)',
        data: chartData.value.map(d => d.gross_margin != null ? Number(d.gross_margin) : null),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16,185,129,0.1)',
        fill: false,
        tension: 0.3,
        pointRadius: 4,
      },
      {
        label: '净利率 (%)',
        data: chartData.value.map(d => d.net_margin != null ? Number(d.net_margin) : null),
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245,158,11,0.1)',
        fill: false,
        tension: 0.3,
        pointRadius: 4,
      },
    ],
  }
})

// Absolute value bar chart
const absoluteChartData = computed(() => {
  if (!chartData.value) return null
  const labels = chartData.value.map(d => d.report_date?.substring(0, 4) || '')

  // Convert to 亿 (divide by 1e8)
  const convertToYi = (val) => {
    if (val == null) return null
    const n = Number(val)
    return isNaN(n) ? null : Number((n / 1e8).toFixed(1))
  }

  return {
    labels,
    datasets: [
      {
        label: '毛利润（亿）',
        data: chartData.value.map(d => convertToYi(d.gross_profit)),
        backgroundColor: 'rgba(16,185,129,0.7)',
        borderColor: '#10b981',
        borderWidth: 1,
      },
      {
        label: '净利润（亿）',
        data: chartData.value.map(d => convertToYi(d.net_profit)),
        backgroundColor: 'rgba(37,99,235,0.7)',
        borderColor: '#2563eb',
        borderWidth: 1,
      },
      {
        label: '营业总收入（亿）',
        data: chartData.value.map(d => convertToYi(d.total_revenue)),
        backgroundColor: 'rgba(245,158,11,0.7)',
        borderColor: '#f59e0b',
        borderWidth: 1,
      },
    ],
  }
})

const lineOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y != null ? ctx.parsed.y.toFixed(2) + '%' : '-'}`
      }
    }
  },
  scales: {
    y: {
      ticks: {
        callback: (val) => val + '%'
      }
    }
  }
}

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y != null ? ctx.parsed.y.toFixed(1) + ' 亿' : '-'}`
      }
    }
  },
  scales: {
    y: {
      ticks: {
        callback: (val) => val + ' 亿'
      }
    }
  }
}
</script>