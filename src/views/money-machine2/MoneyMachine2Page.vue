<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">赚钱机器指标2</h1>
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

      <!-- 9 individual charts, each in its own card -->
      <div v-for="cfg in chartConfigs" :key="cfg.key" class="card" style="margin-bottom: 24px; background: #fff; border-radius: 12px; padding: 24px;">
        <h3 style="margin: 0 0 4px 0; font-size: 20px; font-weight: 700; color: #111;">
          {{ cfg.title }}<span v-if="cfg.unit === '%'" style="color: #888; font-weight: 400;"> (%)</span>
        </h3>
        <div style="height: 400px;">
          <component :is="cfg.chartType" :data="cfg.chartData" :options="cfg.options" />
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
import { getAnnualFinancialsV2, searchCompanies } from '../../lib/supabase.js'

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
    const y = d.year
    return y >= 2016 && y <= 2025
  })
})

// -- Shared style helpers (from TrendChartPage) --
const BLUE = '#5A75C7'
const GRAY = '#999'
const LIGHT_GRAY = '#e8e8e8'

const baseOptions = (unit) => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { enabled: false },
    datalabels: { display: false },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: '#666', font: { size: 12 }, maxRotation: 45, minRotation: 45 },
      border: { display: true, color: '#ccc', dash: [] },
    },
    y: {
      position: 'left',
      grid: { color: LIGHT_GRAY, drawTicks: false, drawBorder: false, lineWidth: 1 },
      ticks: { color: GRAY, font: { size: 11 }, padding: 8,
        callback: (val) => val + unit
      },
      border: { display: false },
      beginAtZero: false,
    },
  },
})

function fmtVal(val, unit) {
  if (val == null) return ''
  const n = Number(val)
  if (isNaN(n)) return ''
  return n.toFixed(1) + unit
}

function fmtPct(val) {
  if (val == null) return ''
  const n = Number(val)
  if (isNaN(n)) return ''
  return n.toFixed(2) + '%'
}

// -- Annotation plugin to draw labels on top of bars/points --
const annotationPlugin = {
  id: 'dataLabels',
  afterDatasetsDraw(chart, args, options) {
    const { ctx } = chart
    const meta = chart.getDatasetMeta(0)
    ctx.save()
    ctx.font = 'bold 12px -apple-system, BlinkMacSystemFont, sans-serif'
    ctx.fillStyle = '#333'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'bottom'
    for (let i = 0; i < meta.data.length; i++) {
      const bar = meta.data[i]
      const val = chart.data.datasets[0].data[i]
      const label = options.labels[i]
      if (val != null && bar.y !== undefined) {
        ctx.fillText(label, bar.x, bar.y - 6)
      }
    }
    ctx.restore()
  }
}

ChartJS.register(annotationPlugin)

// ---- Chart configs (9 charts, MoneyMachine fields + TrendChart style) ----
const chartConfigs = computed(() => {
  if (!chartData.value) return []
  const labels = chartData.value.map(d => String(d.year || ''))

  return [
    // 1. 资本开支 — bar chart, unit 亿
    {
      key: 'capex', title: '资本开支', unit: '亿', chartType: Bar,
      chartData: {
        labels,
        datasets: [{
          data: chartData.value.map(d => d.capex != null ? Number((Number(d.capex) / 1e8).toFixed(1)) : null),
          backgroundColor: BLUE, borderColor: BLUE, borderWidth: 0, borderRadius: 4, barPercentage: 0.6,
        }],
      },
      options: {
        ...baseOptions('亿'),
        plugins: { legend: { display: false }, tooltip: { enabled: false },
          dataLabels: { labels: chartData.value.map(d => fmtVal(d.capex != null ? Number(d.capex) / 1e8 : null, '亿')) }
        },
      },
    },
    // 2. 归母净利润 — bar chart, unit 亿
    {
      key: 'parent_net_profit', title: '归母净利润', unit: '亿', chartType: Bar,
      chartData: {
        labels,
        datasets: [{
          data: chartData.value.map(d => d.parent_net_profit != null ? Number((Number(d.parent_net_profit) / 1e8).toFixed(1)) : null),
          backgroundColor: BLUE, borderColor: BLUE, borderWidth: 0, borderRadius: 4, barPercentage: 0.6,
        }],
      },
      options: {
        ...baseOptions('亿'),
        plugins: { legend: { display: false }, tooltip: { enabled: false },
          dataLabels: { labels: chartData.value.map(d => fmtVal(d.parent_net_profit != null ? Number(d.parent_net_profit) / 1e8 : null, '亿')) }
        },
      },
    },
    // 3. 净利润同比增速 — line chart, unit %
    {
      key: 'net_profit_yoy', title: '净利润同比增速', unit: '%', chartType: Line,
      chartData: {
        labels,
        datasets: [{
          data: chartData.value.map(d => d.net_profit_yoy != null ? Number(d.net_profit_yoy) : null),
          borderColor: BLUE, backgroundColor: BLUE, fill: false, tension: 0.3,
          pointRadius: 5, pointBackgroundColor: BLUE, pointBorderColor: '#fff', pointBorderWidth: 2,
        }],
      },
      options: {
        ...baseOptions('%'),
        plugins: { legend: { display: false }, tooltip: { enabled: false },
          dataLabels: { labels: chartData.value.map(d => fmtPct(d.net_profit_yoy)) }
        },
      },
    },
    // 4. 有效资产收益率 — line chart, unit %
    {
      key: 'effective_asset_return', title: '有效资产收益率', unit: '%', chartType: Line,
      chartData: {
        labels,
        datasets: [{
          data: chartData.value.map(d => d.effective_asset_return != null ? Number(d.effective_asset_return) : null),
          borderColor: BLUE, backgroundColor: BLUE, fill: false, tension: 0.3,
          pointRadius: 5, pointBackgroundColor: BLUE, pointBorderColor: '#fff', pointBorderWidth: 2,
        }],
      },
      options: {
        ...baseOptions('%'),
        plugins: { legend: { display: false }, tooltip: { enabled: false },
          dataLabels: { labels: chartData.value.map(d => fmtPct(d.effective_asset_return)) }
        },
      },
    },
    // 5. 硬朗度利润 — bar chart, unit 亿
    {
      key: 'hard_profit', title: '硬朗度利润（自由现金流）', unit: '亿', chartType: Bar,
      chartData: {
        labels,
        datasets: [{
          data: chartData.value.map(d => d.hard_profit != null ? Number((Number(d.hard_profit) / 1e8).toFixed(1)) : null),
          backgroundColor: BLUE, borderColor: BLUE, borderWidth: 0, borderRadius: 4, barPercentage: 0.6,
        }],
      },
      options: {
        ...baseOptions('亿'),
        plugins: { legend: { display: false }, tooltip: { enabled: false },
          dataLabels: { labels: chartData.value.map(d => fmtVal(d.hard_profit != null ? Number(d.hard_profit) / 1e8 : null, '亿')) }
        },
      },
    },
    // 6. 固定资产 — bar chart, unit 亿
    {
      key: 'fixed_asset', title: '固定资产', unit: '亿', chartType: Bar,
      chartData: {
        labels,
        datasets: [{
          data: chartData.value.map(d => d.fixed_asset != null ? Number((Number(d.fixed_asset) / 1e8).toFixed(1)) : null),
          backgroundColor: BLUE, borderColor: BLUE, borderWidth: 0, borderRadius: 4, barPercentage: 0.6,
        }],
      },
      options: {
        ...baseOptions('亿'),
        plugins: { legend: { display: false }, tooltip: { enabled: false },
          dataLabels: { labels: chartData.value.map(d => fmtVal(d.fixed_asset != null ? Number(d.fixed_asset) / 1e8 : null, '亿')) }
        },
      },
    },
    // 7. 在建工程 — bar chart, unit 亿
    {
      key: 'construction_in_progress', title: '在建工程', unit: '亿', chartType: Bar,
      chartData: {
        labels,
        datasets: [{
          data: chartData.value.map(d => d.construction_in_progress != null ? Number((Number(d.construction_in_progress) / 1e8).toFixed(1)) : null),
          backgroundColor: BLUE, borderColor: BLUE, borderWidth: 0, borderRadius: 4, barPercentage: 0.6,
        }],
      },
      options: {
        ...baseOptions('亿'),
        plugins: { legend: { display: false }, tooltip: { enabled: false },
          dataLabels: { labels: chartData.value.map(d => fmtVal(d.construction_in_progress != null ? Number(d.construction_in_progress) / 1e8 : null, '亿')) }
        },
      },
    },
    // 8. 存货 — bar chart, unit 亿
    {
      key: 'inventory', title: '存货', unit: '亿', chartType: Bar,
      chartData: {
        labels,
        datasets: [{
          data: chartData.value.map(d => d.inventory != null ? Number((Number(d.inventory) / 1e8).toFixed(1)) : null),
          backgroundColor: BLUE, borderColor: BLUE, borderWidth: 0, borderRadius: 4, barPercentage: 0.6,
        }],
      },
      options: {
        ...baseOptions('亿'),
        plugins: { legend: { display: false }, tooltip: { enabled: false },
          dataLabels: { labels: chartData.value.map(d => fmtVal(d.inventory != null ? Number(d.inventory) / 1e8 : null, '亿')) }
        },
      },
    },
    // 9. 锚定资产占比 — line chart, unit %
    {
      key: 'anchor_asset_ratio', title: '锚定资产占总资产比', unit: '%', chartType: Line,
      chartData: {
        labels,
        datasets: [{
          data: chartData.value.map(d => d.anchor_asset_ratio != null ? Number(d.anchor_asset_ratio) : null),
          borderColor: BLUE, backgroundColor: BLUE, fill: false, tension: 0.3,
          pointRadius: 5, pointBackgroundColor: BLUE, pointBorderColor: '#fff', pointBorderWidth: 2,
        }],
      },
      options: {
        ...baseOptions('%'),
        scales: {
          ...baseOptions('%').scales,
          y: { ...baseOptions('%').scales.y, min: 0, max: 100 },
        },
        plugins: { legend: { display: false }, tooltip: { enabled: false },
          dataLabels: { labels: chartData.value.map(d => fmtPct(d.anchor_asset_ratio)) }
        },
      },
    },
  ]
})
</script>