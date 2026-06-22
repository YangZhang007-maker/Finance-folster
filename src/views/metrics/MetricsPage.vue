<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">指标统计</h1>
      <div style="display: flex; gap: 8px;">
        <select v-model="sortField" class="btn btn-sm" style="cursor: pointer;">
          <option value="">默认排序</option>
          <option v-for="col in columns" :key="col.key" :value="col.key">{{ col.label }}</option>
        </select>
        <button class="btn btn-sm" @click="toggleSortDir">
          {{ sortDir === 'asc' ? '升序' : '降序' }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading"><div class="spinner"></div></div>

    <div v-else-if="watchlist.length === 0" class="empty-state">
      <h3>暂无自选公司</h3>
      <p>先在自选列表中添加公司，然后在这里查看对比指标</p>
    </div>

    <div v-else-if="sortedData.length === 0" class="empty-state">
      <h3>暂无财务数据</h3>
      <p>数据正在通过GitHub Actions同步中，请稍后再查看</p>
    </div>

    <template v-else>
      <!-- Summary stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">公司数量</div>
          <div class="stat-value">{{ sortedData.length }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">平均 PE</div>
          <div class="stat-value">{{ avgMetric('pe_ratio') }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">平均 ROE</div>
          <div class="stat-value">{{ avgMetric('roe') }}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">平均 PB</div>
          <div class="stat-value">{{ avgMetric('pb_ratio') }}</div>
        </div>
      </div>

      <!-- Metrics table -->
      <div class="card table-wrap">
        <table>
          <thead>
            <tr>
              <th @click="setSort('name')">
                公司 <span class="sort-indicator">{{ sortIcon('name') }}</span>
              </th>
              <th @click="setSort('code')">
                代码 <span class="sort-indicator">{{ sortIcon('code') }}</span>
              </th>
              <th v-for="col in columns" :key="col.key" @click="setSort(col.key)">
                {{ col.label }} <span class="sort-indicator">{{ sortIcon(col.key) }}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sortedData" :key="row.code">
              <td style="font-weight: 600;">{{ row.name }}</td>
              <td style="color: var(--text-secondary);">{{ row.code }}</td>
              <td v-for="col in columns" :key="col.key" :class="cellClass(row[col.key], col)">
                {{ formatCell(row[col.key], col) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div style="margin-top: 16px; color: var(--text-secondary); font-size: 13px; text-align: center;">
        数据更新时间：{{ updateTime }}
      </div>
    </template>

    <div v-if="toast" :class="['toast', toastType]">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getWatchlist, getFinancialIndicators, getCompanyNames } from '../../lib/supabase.js'

const columns = [
  { key: 'pe_ratio', label: 'PE', fmt: 'num2' },
  { key: 'pb_ratio', label: 'PB', fmt: 'num2' },
  { key: 'ps_ratio', label: 'PS', fmt: 'num2' },
  { key: 'peg_ratio', label: 'PEG', fmt: 'num2' },
  { key: 'roe', label: 'ROE %', fmt: 'pct' },
  { key: 'roa', label: 'ROA %', fmt: 'pct' },
  { key: 'gross_margin', label: '毛利率 %', fmt: 'pct' },
  { key: 'net_margin', label: '净利率 %', fmt: 'pct' },
  { key: 'revenue_growth', label: '营收增长 %', fmt: 'pct' },
  { key: 'net_profit_growth', label: '利润增长 %', fmt: 'pct' },
  { key: 'debt_to_assets', label: '资产负债率 %', fmt: 'pct' },
  { key: 'current_ratio', label: '流动比率', fmt: 'num2' },
  { key: 'dividend_yield', label: '股息率 %', fmt: 'pct' },
  { key: 'market_cap', label: '总市值(亿)', fmt: 'marketCap' },
  { key: 'buffett_index', label: '巴菲特指标', fmt: 'num2' },
]

const loading = ref(true)
const watchlist = ref([])
const data = ref([])
const sortField = ref('')
const sortDir = ref('desc')
const toast = ref('')
const toastType = ref('toast-success')

const sortedData = computed(() => {
  const arr = [...data.value]
  if (!sortField.value) return arr
  arr.sort((a, b) => {
    const va = a[sortField.value] != null ? Number(a[sortField.value]) : -Infinity
    const vb = b[sortField.value] != null ? Number(b[sortField.value]) : -Infinity
    return sortDir.value === 'asc' ? va - vb : vb - va
  })
  return arr
})

const updateTime = computed(() => {
  if (data.value.length === 0) return '-'
  const times = data.value.map(d => d.updated_at).filter(Boolean)
  return times.length > 0 ? new Date(times[0]).toLocaleString('zh-CN') : '-'
})

function avgMetric(key) {
  const vals = data.value.map(d => Number(d[key])).filter(v => !isNaN(v))
  if (vals.length === 0) return '-'
  return (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2)
}

function setSort(key) {
  if (sortField.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = key
    sortDir.value = 'desc'
  }
}

function sortIcon(key) {
  if (sortField.value !== key) return ''
  return sortDir.value === 'asc' ? '▲' : '▼'
}

function toggleSortDir() {
  sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
}

function formatCell(val, col) {
  if (val == null) return '-'
  const n = Number(val)
  if (isNaN(n)) return val
  switch (col.fmt) {
    case 'num2': return n.toFixed(2)
    case 'pct': return n.toFixed(2)
    case 'marketCap': return n > 0 ? (n / 1e8).toFixed(1) : n.toFixed(1)
    default: return n.toFixed(2)
  }
}

function cellClass(val, col) {
  if (val == null) return ''
  const n = Number(val)
  if (isNaN(n)) return ''
  // Color code growth and profitability metrics
  const positiveGood = ['roe', 'roa', 'gross_margin', 'net_margin', 'revenue_growth', 'net_profit_growth']
  if (positiveGood.includes(col.key)) {
    return n > 0 ? 'num-positive' : n < 0 ? 'num-negative' : ''
  }
  return ''
}

onMounted(async () => {
  try {
    const wl = await getWatchlist()
    const codes = wl.map(w => w.code)
    if (codes.length === 0) {
      loading.value = false
      return
    }
    const [indicators, nameMap] = await Promise.all([
      getFinancialIndicators(codes),
      getCompanyNames(codes)
    ])
    watchlist.value = codes.map(code => ({
      code,
      name: nameMap[code] || code,
    }))
    data.value = indicators.map(ind => ({
      ...ind,
      name: nameMap[ind.code] || ind.code,
    }))
  } catch (e) {
    console.error(e)
    showToast('数据加载失败', 'toast-error')
  } finally {
    loading.value = false
  }
})

function showToast(msg, type = 'toast-success') {
  toast.value = msg
  toastType.value = type
  setTimeout(() => { toast.value = '' }, 2000)
}
</script>
