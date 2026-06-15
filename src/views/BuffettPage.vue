<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">巴菲特指标分析</h1>
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

      <div class="charts-grid-2x5">
        <!-- Chart 1: 毛利润 vs 毛利率 -->
        <div class="chart-card">
          <h3 class="chart-title">毛利润 vs 毛利率</h3>
          <div class="chart-wrap">
            <Bar :data="chart1Data" :options="chart1Options" />
          </div>
        </div>

        <!-- Chart 2: 毛利率趋势 -->
        <div class="chart-card">
          <h3 class="chart-title">毛利率变化趋势</h3>
          <div class="chart-wrap">
            <Line :data="chart2Data" :options="chart2Options" />
          </div>
        </div>

        <!-- Chart 3: 三费占毛利比 -->
        <div class="chart-card">
          <h3 class="chart-title">销售+管理+研发费用占毛利比</h3>
          <div class="chart-wrap">
            <Line :data="chart3Data" :options="chart3Options" />
          </div>
          <div class="chart-legend-row">
            <span class="legend-item"><span class="legend-dot" style="background:#1F77B4"></span>销售费用</span>
            <span class="legend-item"><span class="legend-dot" style="background:#FF7F0E"></span>管理费用</span>
            <span class="legend-item"><span class="legend-dot" style="background:#2CA02C"></span>研发费用</span>
          </div>
        </div>

        <!-- Chart 4: 销管研三费占毛利比趋势 -->
        <div class="chart-card">
          <h3 class="chart-title">销管研三费合计占毛利比趋势</h3>
          <div class="chart-wrap">
            <Line :data="chart4Data" :options="chart4Options" />
          </div>
        </div>

        <!-- Chart 5: 经营利润 vs 归母净利润 -->
        <div class="chart-card">
          <h3 class="chart-title">经营利润 vs 归母净利润</h3>
          <div class="chart-wrap">
            <Bar :data="chart5Data" :options="chart5Options" />
          </div>
        </div>

        <!-- Chart 6: 扣非净利润 -->
        <div class="chart-card">
          <h3 class="chart-title">扣非净利润趋势</h3>
          <div class="chart-wrap">
            <Bar :data="chart6Data" :options="chart6Options" />
          </div>
        </div>

        <!-- Chart 7: 存货 vs 预收款 -->
        <div class="chart-card">
          <h3 class="chart-title">存货 vs 预收款</h3>
          <p class="chart-subtitle">预收款反映下游议价能力</p>
          <div class="chart-wrap">
            <Bar :data="chart7Data" :options="chart7Options" />
          </div>
        </div>

        <!-- Chart 8: 预收款占总营收比 -->
        <div class="chart-card">
          <h3 class="chart-title">预收款占总营收比</h3>
          <p class="chart-subtitle">越高说明对下游话语权越强</p>
          <div class="chart-wrap">
            <Line :data="chart8Data" :options="chart8Options" />
          </div>
        </div>

        <!-- Chart 9: 剔除预收款后的资产负债率 -->
        <div class="chart-card">
          <h3 class="chart-title">剔除预收款后的资产负债率</h3>
          <div class="chart-wrap">
            <Line :data="chart9Data" :options="chart9Options" />
          </div>
        </div>

        <!-- Chart 10: 剔除预收款后的债务股权比 -->
        <div class="chart-card">
          <h3 class="chart-title">剔除预收款后的债务股权比</h3>
          <p class="chart-subtitle">负值表示净现金公司</p>
          <div class="chart-wrap">
            <Line :data="chart10Data" :options="chart10Options" />
          </div>
        </div>
      </div>
    </template>

    <div v-if="!selectedStock && !loading && searchResults.length === 0 && !searched" class="empty-state">
      <h3>搜索股票查看巴菲特指标</h3>
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
    const y = d.year
    return y >= 2016 && y <= 2025
  })
})

const labels = computed(() => {
  if (!chartData.value) return []
  return chartData.value.map(d => String(d.year || ''))
})

// Convert 元 to 万元
function toWan(val) {
  if (val == null) return null
  return Number((Number(val) / 10000).toFixed(0))
}

// Compute advance_contract_liab = advance_receipts_sina + contract_liabilities
function advanceContract(d) {
  const a = d.advance_receipts_sina != null ? Number(d.advance_receipts_sina) : 0
  const c = d.contract_liabilities != null ? Number(d.contract_liabilities) : 0
  return a + c
}

// ---- Chart 1: 毛利润 vs 毛利率 (dual axis) ----
const chart1Data = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      type: 'bar',
      label: '毛利润',
      data: chartData.value.map(d => toWan(d.gross_profit)),
      backgroundColor: '#1F77B4',
      borderRadius: 4,
      barPercentage: 0.6,
      yAxisID: 'y',
      order: 2,
    },
    {
      type: 'line',
      label: '毛利率',
      data: chartData.value.map(d => d.gross_margin != null ? Number(d.gross_margin) : null),
      borderColor: '#FF8C00',
      backgroundColor: '#FF8C00',
      fill: false,
      tension: 0.3,
      pointRadius: 5,
      pointBackgroundColor: '#FF8C00',
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      yAxisID: 'y1',
      order: 1,
    },
  ],
}))

const chart1Options = computed(() => dualAxisOpts('万元', '%', '#FF8C00'))

function dualAxisOpts(leftLabel, rightLabel, rightColor) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: { boxWidth: 12, padding: 8, font: { size: 11 } },
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
        ticks: { color: '#999', font: { size: 11 }, callback: (val) => val + leftLabel },
        border: { display: false },
        beginAtZero: false,
      },
      y1: {
        type: 'linear',
        position: 'right',
        grid: { drawOnChartArea: false },
        ticks: { color: rightColor, font: { size: 11 }, callback: (val) => val + rightLabel },
        border: { display: false },
        beginAtZero: false,
      },
    },
  }
}

// ---- Chart 2: 毛利率趋势 ----
const chart2Data = computed(() => ({
  labels: labels.value,
  datasets: [{
    label: '毛利率',
    data: chartData.value.map(d => d.gross_margin != null ? Number(d.gross_margin) : null),
    borderColor: '#2CA02C',
    backgroundColor: '#2CA02C',
    fill: false,
    tension: 0.3,
    pointRadius: 5,
    pointBackgroundColor: '#2CA02C',
    pointBorderColor: '#fff',
    pointBorderWidth: 2,
  }],
}))

const chart2Options = computed(() => lineOpts('%', 0, 100))

function lineOpts(unit, yMin, yMax) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `${ctx.raw?.toFixed(2)}${unit}` } }
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#666', font: { size: 12 } },
        border: { display: true, color: '#ccc' },
      },
      y: {
        position: 'left',
        min: yMin,
        max: yMax,
        grid: { color: '#e8e8e8', drawTicks: false },
        ticks: { color: '#999', font: { size: 11 }, callback: (val) => val + unit },
        border: { display: false },
        beginAtZero: false,
      },
    },
  }
}

// ---- Chart 3: 三费占毛利比 (stacked area with 3 lines) ----
const chart3Data = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      label: '销售费用',
      data: chartData.value.map(d => d.selling_to_gross != null ? Number(d.selling_to_gross) : null),
      borderColor: '#1F77B4',
      backgroundColor: '#1F77B4',
      fill: true,
      tension: 0.3,
      pointRadius: 3,
    },
    {
      label: '管理费用',
      data: chartData.value.map(d => d.admin_to_gross != null ? Number(d.admin_to_gross) : null),
      borderColor: '#FF7F0E',
      backgroundColor: '#FF7F0E',
      fill: true,
      tension: 0.3,
      pointRadius: 3,
    },
    {
      label: '研发费用',
      data: chartData.value.map(d => d.rd_to_gross != null ? Number(d.rd_to_gross) : null),
      borderColor: '#2CA02C',
      backgroundColor: '#2CA02C',
      fill: true,
      tension: 0.3,
      pointRadius: 3,
    },
  ],
}))

const chart3Options = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ${ctx.raw?.toFixed(2)}%`
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
      stacked: true,
      grid: { color: '#e8e8e8', drawTicks: false },
      ticks: { color: '#999', font: { size: 11 }, callback: (val) => val + '%' },
      border: { display: false },
    },
  },
}))

// ---- Chart 4: 销管研三费占毛利比趋势 ----
const chart4Data = computed(() => ({
  labels: labels.value,
  datasets: [{
    label: '销管研三费占毛利比',
    data: chartData.value.map(d => d.sga_rd_to_gross != null ? Number(d.sga_rd_to_gross) : null),
    borderColor: '#D62728',
    backgroundColor: '#D62728',
    fill: false,
    tension: 0.3,
    pointRadius: 5,
    pointBackgroundColor: '#D62728',
    pointBorderColor: '#fff',
    pointBorderWidth: 2,
  }],
}))

const chart4Options = computed(() => lineOpts('%', 0, 100))

// ---- Chart 5: 经营利润 vs 归母净利润 (grouped bar) ----
const chart5Data = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      label: '经营利润',
      data: chartData.value.map(d => toWan(d.operating_profit)),
      backgroundColor: '#1F77B4',
      borderRadius: 4,
      barPercentage: 0.8,
    },
    {
      label: '归母净利润',
      data: chartData.value.map(d => toWan(d.parent_net_profit)),
      backgroundColor: '#FF7F0E',
      borderRadius: 4,
      barPercentage: 0.8,
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
      grid: { display: false },
      ticks: { color: '#666', font: { size: 12 } },
      border: { display: true, color: '#ccc' },
    },
    y: {
      position: 'left',
      grid: { color: '#e8e8e8', drawTicks: false },
      ticks: { color: '#999', font: { size: 11 }, callback: (val) => val + '万' },
      border: { display: false },
      beginAtZero: false,
    },
  },
}))

// ---- Chart 6: 扣非净利润 ----
const chart6Data = computed(() => ({
  labels: labels.value,
  datasets: [{
    label: '扣非净利润',
    data: chartData.value.map(d => toWan(d.deducted_net_profit)),
    backgroundColor: '#9467BD',
    borderColor: '#9467BD',
    borderRadius: 4,
    barPercentage: 0.6,
  }],
}))

const chart6Options = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `扣非净利润: ${ctx.raw?.toLocaleString()} 万元`
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
      ticks: { color: '#999', font: { size: 11 }, callback: (val) => val + '万' },
      border: { display: false },
      beginAtZero: false,
    },
  },
}))

// ---- Chart 7: 存货 vs 预收款 (grouped bar) ----
const chart7Data = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      label: '存货',
      data: chartData.value.map(d => toWan(d.inventory)),
      backgroundColor: '#1F77B4',
      borderRadius: 4,
      barPercentage: 0.8,
    },
    {
      label: '预收款/合同负债',
      data: chartData.value.map(d => toWan(advanceContract(d))),
      backgroundColor: '#FF7F0E',
      borderRadius: 4,
      barPercentage: 0.8,
    },
  ],
}))

const chart7Options = computed(() => ({
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
      grid: { display: false },
      ticks: { color: '#666', font: { size: 12 } },
      border: { display: true, color: '#ccc' },
    },
    y: {
      position: 'left',
      grid: { color: '#e8e8e8', drawTicks: false },
      ticks: { color: '#999', font: { size: 11 }, callback: (val) => val + '万' },
      border: { display: false },
      beginAtZero: false,
    },
  },
}))

// ---- Chart 8: 预收款占总营收比 ----
const chart8Data = computed(() => ({
  labels: labels.value,
  datasets: [{
    label: '预收款占总营收比',
    data: chartData.value.map(d => d.advance_to_revenue != null ? Number(d.advance_to_revenue) : null),
    borderColor: '#2CA02C',
    backgroundColor: '#2CA02C',
    fill: false,
    tension: 0.3,
    pointRadius: 5,
    pointBackgroundColor: '#2CA02C',
    pointBorderColor: '#fff',
    pointBorderWidth: 2,
  }],
}))

const chart8Options = computed(() => lineOpts('%', 0, undefined))

// ---- Chart 9: 剔除预收款后的资产负债率 (with 50% reference line) ----
const chart9Data = computed(() => ({
  labels: labels.value,
  datasets: [
    {
      label: '资产负债率(剔预收)',
      data: chartData.value.map(d => d.debt_ratio_ex_advance != null ? Number(d.debt_ratio_ex_advance) : null),
      borderColor: '#D62728',
      backgroundColor: '#D62728',
      fill: false,
      tension: 0.3,
      pointRadius: 5,
      pointBackgroundColor: '#D62728',
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
    },
  ],
}))

const chart9Options = computed(() => {
  const opts = lineOpts('%', 0, 100)
  // Add 50% reference line annotation
  opts.plugins.annotation = {
    annotations: {
      line50: {
        type: 'line',
        yMin: 50,
        yMax: 50,
        borderColor: '#999',
        borderWidth: 1,
        borderDash: [6, 4],
        label: {
          display: true,
          content: '50% 警戒线',
          position: 'end',
          backgroundColor: 'transparent',
          color: '#999',
          font: { size: 11 },
        },
      },
    },
  }
  return opts
})

// ---- Chart 10: 剔除预收款后的债务股权比 ----
const chart10Data = computed(() => ({
  labels: labels.value,
  datasets: [{
    label: '债务股权比(剔预收)',
    data: chartData.value.map(d => d.debt_equity_ex_cash != null ? Number(d.debt_equity_ex_cash) : null),
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

const chart10Options = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.raw?.toFixed(2)}x`
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
      ticks: { color: '#999', font: { size: 11 }, callback: (val) => val.toFixed(1) + 'x' },
      border: { display: false },
      beginAtZero: false,
    },
  },
}))
</script>

<style scoped>
.charts-grid-2x5 {
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

.chart-legend-row {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

@media (max-width: 900px) {
  .charts-grid-2x5 {
    grid-template-columns: 1fr;
  }
}
</style>