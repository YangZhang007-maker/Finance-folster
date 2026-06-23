<template>
  <div class="sector-insight">
    <!-- ===== 头部筛选区域 ===== -->
    <div class="filter-bar">
      <div class="filter-left">
        <div class="filter-group">
          <label>选择行业</label>
          <select v-model="filters.industry">
            <option v-for="ind in industryOptions" :key="ind" :value="ind">{{ ind }}</option>
          </select>
        </div>
        <div class="filter-group">
          <label>选择会计年度</label>
          <select v-model="filters.year">
            <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
          </select>
        </div>
        <div class="filter-group">
          <label>选择指标</label>
          <select v-model="filters.indicator">
            <option v-for="ind in indicatorOptions" :key="ind.value" :value="ind.value">{{ ind.label }}</option>
          </select>
        </div>
      </div>
      <div class="filter-right">
        <div class="current-badge">
          <span class="badge-label">当前查看：</span>
          <span class="badge-value">{{ filters.industry }}</span>
          <span class="badge-sep">·</span>
          <span class="badge-value">{{ currentIndicatorLabel }}</span>
          <span class="badge-sep">·</span>
          <span class="badge-value">{{ filters.year }}年</span>
        </div>
      </div>
    </div>

    <!-- ===== 加载状态 ===== -->
    <div v-if="loading" class="loading"><div class="spinner"></div><p>加载中...</p></div>

    <!-- ===== 内容区 ===== -->
    <template v-else-if="hasData">
      <!-- 统计指标卡片（4个并排） -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-label">公司数量</div>
          <div class="stat-value blue">{{ filteredCompanyData.length }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">平均值</div>
          <div class="stat-value green">{{ avgValue }}<span class="stat-unit">{{ indicatorUnit }}</span></div>
        </div>
        <div class="stat-card">
          <div class="stat-label">最大值</div>
          <div class="stat-value red">{{ maxValue }}<span class="stat-unit">{{ indicatorUnit }}</span></div>
        </div>
        <div class="stat-card">
          <div class="stat-label">最小值</div>
          <div class="stat-value orange">{{ minValue }}<span class="stat-unit">{{ indicatorUnit }}</span></div>
        </div>
      </div>

      <!-- 图表区域 -->
      <div class="chart-card">
        <h3 class="chart-card-title">{{ filters.industry }} - {{ currentIndicatorLabel }}<span class="chart-card-subtitle">（注：{{ indicatorNote }}）</span></h3>
        <div class="chart-wrap">
          <v-chart v-if="treemapOption" :option="treemapOption" autoresize />
        </div>
      </div>

      <!-- 底部数据明细表格 -->
      <div class="table-card">
        <table>
          <thead>
            <tr>
              <th class="col-rank">排名</th>
              <th>公司名称</th>
              <th>代码</th>
              <th>细分行业</th>
              <th class="col-value">{{ currentIndicatorLabel }}（{{ indicatorUnit }}）</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, idx) in rankedData" :key="item.code">
              <td class="col-rank">
                <span v-if="idx === 0" class="rank-badge gold">🥇</span>
                <span v-else-if="idx === 1" class="rank-badge silver">🥈</span>
                <span v-else-if="idx === 2" class="rank-badge bronze">🥉</span>
                <span v-else class="rank-num">{{ idx + 1 }}</span>
              </td>
              <td class="col-name">{{ item.name }}</td>
              <td class="col-code">{{ item.code }}</td>
              <td class="col-industry">{{ item.sector || '-' }}</td>
              <td class="col-value">{{ item.value }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- 无数据 -->
    <div v-else-if="!loading" class="empty-state">
      <h3>暂无自选公司数据</h3>
      <p>请先在「自选列表」中添加公司，或确认当前行业/年份有数据</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { TreemapChart } from 'echarts/charts'
import { TooltipComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { getWatchlist, getCompaniesByCodes, getFinancialsByYear } from '../../lib/supabase.js'

use([TreemapChart, TooltipComponent, GridComponent, CanvasRenderer])

// ============================================================
// 选项
// ============================================================
const industryOptions = ['日常消费', '可选消费', '信息技术', '工业', '金融', '房地产', '材料', '公用事业', '医疗保健', '能源', '通讯服务']

const yearOptions = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016]

const indicatorOptions = [
  { value: 'gross_profit', label: '毛利润', note: '营业收入-营业成本，稳定趋升、越高越好', unit: '亿元', isPercent: false },
  { value: 'gross_margin', label: '毛利率', note: '毛利润/营业收入，只有具备某种可持续竞争优势才能在长期运营中一直保持赢利', unit: '%', isPercent: true },
  { value: 'selling_to_gross', label: '销售费用占毛利比', note: '销售费用/毛利润，部分有持续竞争力的品牌公司，销售费用占毛利的比重也可能50-60%，如快消品，若低于30%则比较有竞争力', unit: '%', isPercent: true },
  { value: 'admin_to_gross', label: '管理费用占毛利比', note: '管理费用/毛利润，销售费用及一般管理费用占毛利润的比例越少越好，两项合计30%以下最好', unit: '%', isPercent: true },
  { value: 'selling_admin_to_gross', label: '销管费用占毛利比', note: '（销售费用+管理费用）/毛利润，销售费用及一般管理费用占毛利润的比例越少越好，两项合计30%以下最好，高于80%则回避', unit: '%', isPercent: true },
  { value: 'rd_to_gross', label: '研发费用占毛利比', note: '研发费用/毛利润，尽量回避那些必须经常花费巨额研发费用的公司，高于15%则回避', unit: '%', isPercent: true },
  { value: 'sga_rd_to_gross', label: '销管研三费占毛利比', note: '（销售费用+管理费用+研发费用）/毛利润，越低越好，高于80%则回避', unit: '%', isPercent: true },
  { value: 'finance_expense', label: '财务费用', note: '利息支出-利息收入，正值代表净支出，负值代表净收入', unit: '亿元', isPercent: false, dualColor: true },
  { value: 'finance_to_gross', label: '财务费用占毛利比', note: '财务费用/毛利润，小于15%为宜，高于15%则回避', unit: '%', isPercent: true },
  { value: 'operating_profit', label: '经营利润', note: '毛利润-销售费用-管理费用-研发费用-财务费用+权益性投资损益，衡量所有经营相关的利润，稳定趋升，越高越好', unit: '亿元', isPercent: false },
  { value: 'hard_profit', label: '硬朗度利润', note: '经营现金流净额-资本开支，衡量企业自由现金流，越高越好', unit: '亿元', isPercent: false },
  { value: 'total_profit', label: '税前利润', note: '利润总额，包括经营利润与非经常性损益，是不同类资产之间比价的桥梁', unit: '亿元', isPercent: false },
  { value: 'parent_net_profit', label: '归母净利润', note: '归属母公司股东的全部净利润，稳定趋升，越高越好', unit: '亿元', isPercent: false },
  { value: 'deducted_net_profit', label: '扣非净利润', note: '扣除非经常损益后的净利润，稳定趋升，越高越好', unit: '亿元', isPercent: false },
  { value: 'inventory', label: '存货', note: '对于制造类企业，要查看其存货增长的同时净利润是否相应增长。存货在某些年份迅速增加，而其后又迅速减少的制造类公司，它很可能处于高度竞争、时而繁荣时而衰退的行业，其中没有任何一家公司能让人变得富有。', unit: '亿元', isPercent: false },
  { value: 'anchor_assets', label: '锚定资产', note: '货币、银行存款、债权、固定收益及金融类类现金资产，不含长期股权，不能独立产生经营性现金流的资产（不适用金融类企业）', unit: '亿元', isPercent: false },
  { value: 'anchor_asset_ratio', label: '锚定资产占比', note: '锚定资产/总资产，过滤掉增发和发债等因素带来的现金增加后，该项稳定趋升、越高代表企业荷包越鼓。', unit: '%', isPercent: true },
  { value: 'effective_asset_return', label: '有效资产收益率', note: '扣非净利润/（总资产-锚定资产），衡量一年能收回多少比例的有效资产，越高则赚钱机器含金量越足', unit: '%', isPercent: true },
  { value: 'net_profit_margin', label: '净利润率', note: '净利润/营业总收入，如果一直保持在20%以上，那么很可能具有某种长期竞争优势。如果一直保持在10%以下，则很可能处于一个高度竞争行业，行业中没有一家公司能长期维持竞争优势，建议回避。', unit: '%', isPercent: true },
  { value: 'advance_contract_liab', label: '预收款', note: '预收账款+合同负债，观察其是否随营收同比例变化', unit: '亿元', isPercent: false },
  { value: 'advance_to_revenue', label: '预收款占总营收比', note: '（预收账款+合同负债）/营业收入，行业内横向比较可判断企业话语权，越高则越大', unit: '%', isPercent: true },
  { value: 'debt_ratio_ex_advance', label: '剔除预收款的资产负债率', note: '（总负债-预收账款-合同负债）／（总资产-预收账款-合同负债），越低越好，高于80%要警惕', unit: '%', isPercent: true },
  { value: 'debt_equity_ex_cash', label: '剔除预收款后的债务股权比', note: '（总负债-预收账款-合同负债）／（净资产-预收账款-合同负债+库存公司），越低越好，通常低于80%是好公司，具备持续竞争优势', unit: '%', isPercent: true },
  { value: 'roe', label: 'ROE', note: '净利润/期末净资产，越高越好，15%以上优秀', unit: '%', isPercent: true },
  { value: 'total_shares', label: '总股本', note: '全部市场股本合计', unit: '亿股', isPercent: false },
]

// ============================================================
// 状态
// ============================================================
const filters = ref({
  industry: '日常消费',
  year: 2025,
  indicator: 'gross_profit',
})

const loading = ref(false)
const watchlistCodes = ref([])
const companies = ref([])
const financials = ref([])

const currentIndicator = computed(() => {
  return indicatorOptions.find(i => i.value === filters.value.indicator) || indicatorOptions[0]
})

const currentIndicatorLabel = computed(() => currentIndicator.value.label)

const indicatorNote = computed(() => currentIndicator.value.note)

const indicatorUnit = computed(() => currentIndicator.value.unit)

const indicatorIsPercent = computed(() => currentIndicator.value.isPercent)

// ============================================================
// 数据加载
// ============================================================
async function loadData() {
  loading.value = true
  try {
    // 1. 获取自选列表
    const wl = await getWatchlist()
    watchlistCodes.value = wl.map(w => w.code)

    if (watchlistCodes.value.length === 0) {
      companies.value = []
      financials.value = []
      return
    }

    // 2. 并行获取公司信息和财务数据
    const [compData, finData] = await Promise.all([
      getCompaniesByCodes(watchlistCodes.value),
      getFinancialsByYear(watchlistCodes.value, filters.value.year),
    ])

    companies.value = compData
    financials.value = finData
  } catch (e) {
    console.error('数据加载失败:', e)
    companies.value = []
    financials.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})

// 行业/年份切换时重新加载（仅针对财务数据）
watch([() => filters.value.year], () => {
  loadData()
})

// ============================================================
// 计算属性：筛选后的公司数据
// ============================================================
const filteredCompanyData = computed(() => {
  // 财务数据 map
  const finMap = {}
  for (const f of financials.value) {
    finMap[f.code] = f
  }

  // 公司 map
  const compMap = {}
  for (const c of companies.value) {
    compMap[c.code] = c
  }

  const results = []
  for (const code of watchlistCodes.value) {
    const comp = compMap[code]
    const fin = finMap[code]
    if (!comp) continue

    // 行业筛选（如果公司有 sector 则过滤，没有则包含）
    if (comp.sector && comp.sector !== filters.value.industry) continue

    const value = fin ? getIndicatorValue(fin, filters.value.indicator) : null
    if (value == null) continue

    // 指标值转换：毛利润 元→亿元，毛利率保持原值(%)
    const displayValue = currentIndicator.value.isPercent
      ? Number(Number(value).toFixed(2))
      : Number((value / 1e8).toFixed(2))

    results.push({
      name: comp.name || code,
      code: code,
      sector: comp.sector || '-',
      value: displayValue,
    })
  }

  // 按值降序排列
  results.sort((a, b) => b.value - a.value)
  return results
})

const hasData = computed(() => filteredCompanyData.value.length > 0)

// 排名数据（取前17个用于表格展示）
const rankedData = computed(() => {
  return filteredCompanyData.value.slice(0, 50)
})

// ============================================================
// 统计指标
// ============================================================
const avgValue = computed(() => {
  const vals = filteredCompanyData.value.map(d => d.value)
  if (vals.length === 0) return '-'
  return (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2)
})

const maxValue = computed(() => {
  const vals = filteredCompanyData.value.map(d => d.value)
  if (vals.length === 0) return '-'
  return Math.max(...vals).toFixed(2)
})

const minValue = computed(() => {
  const vals = filteredCompanyData.value.map(d => d.value)
  if (vals.length === 0) return '-'
  return Math.min(...vals).toFixed(2)
})

// ============================================================
// ECharts Treemap 配置
// ============================================================
const treemapOption = computed(() => {
  const data = filteredCompanyData.value
  if (data.length === 0) return null

  const isDualColor = currentIndicator.value.dualColor
  const grad = colorGradients[filters.value.indicator] || RED_GRAD

  function hexToRgb(hex) {
    const r = parseInt(hex.slice(1,3), 16)
    const g = parseInt(hex.slice(3,5), 16)
    const b = parseInt(hex.slice(5,7), 16)
    return { r, g, b }
  }
  function rgbToHex(r, g, b) {
    return '#' + [r, g, b].map(v => Math.round(v).toString(16).padStart(2, '0')).join('')
  }

  const treemapData = data.map((item) => {
    if (isDualColor) {
      // 双色：正值红色渐变，负值绿色渐变（绝对值越大越深）
      if (item.value >= 0) {
        const maxVal = Math.max(...data.filter(d => d.value >= 0).map(d => d.value), 1)
        const t = maxVal > 0 ? item.value / maxVal : 0
        const mx = hexToRgb(RED_GRAD.max), mn = hexToRgb(RED_GRAD.min)
        const r = Math.round(mn.r + (mx.r - mn.r) * t)
        const g = Math.round(mn.g + (mx.g - mn.g) * t)
        const b = Math.round(mn.b + (mx.b - mn.b) * t)
        return { name: item.name, value: item.value, itemStyle: { color: rgbToHex(r, g, b) } }
      } else {
        const absVals = data.filter(d => d.value < 0).map(d => Math.abs(d.value))
        const maxAbs = Math.max(...absVals, 1)
        const t = Math.abs(item.value) / maxAbs
        const mx = hexToRgb(GREEN_GRAD.max), mn = hexToRgb(GREEN_GRAD.min)
        const r = Math.round(mn.r + (mx.r - mn.r) * t)
        const g = Math.round(mn.g + (mx.g - mn.g) * t)
        const b = Math.round(mn.b + (mx.b - mn.b) * t)
        return { name: item.name, value: item.value, itemStyle: { color: rgbToHex(r, g, b) } }
      }
    }
    // 单一颜色渐变
    const maxVal = Math.max(...data.map(d => d.value), 1)
    const minVal = Math.min(...data.map(d => d.value), 0)
    const t = maxVal > minVal ? (item.value - minVal) / (maxVal - minVal) : 0
    const mx = hexToRgb(grad.max), mn = hexToRgb(grad.min)
    const r = Math.round(mn.r + (mx.r - mn.r) * t)
    const g = Math.round(mn.g + (mx.g - mn.g) * t)
    const b = Math.round(mn.b + (mx.b - mn.b) * t)
    return { name: item.name, value: item.value, itemStyle: { color: rgbToHex(r, g, b) } }
  })

  return {
    tooltip: {
      formatter: (params) => {
        return `${params.name}<br/>${currentIndicatorLabel.value}: <b>${params.value}${currentIndicator.value.unit === '亿元' ? '亿元' : '%'}</b>`
      },
    },
    series: [
      {
        type: 'treemap',
        width: '100%',
        height: '100%',
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        label: {
          show: true,
          position: 'inside',
          align: 'center',
          verticalAlign: 'middle',
          color: '#fff',
          fontSize: 13,
          fontWeight: 'bold',
          formatter: (p) => {
            const u = currentIndicator.value.unit === '亿元' ? '亿' : '%'
            return `{b|${p.name}}\n{s|${p.value}${u}}`
          },
          rich: {
            b: { fontSize: 13, fontWeight: 'bold', color: '#fff', lineHeight: 22, align: 'center' },
            s: { fontSize: 11, color: 'rgba(255,255,255,0.85)', lineHeight: 18, align: 'center' },
          },
        },
        upperLabel: { show: false },
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 2,
          gapWidth: 2,
        },
        levels: [
          {
            itemStyle: {
              borderWidth: 0,
              gapWidth: 3,
            },
          },
        ],
        data: treemapData,
      },
    ],
  }
})

// ============================================================
// 辅助函数
// ============================================================
function getIndicatorValue(fin, indicator) {
  const map = {
    gross_profit: fin.gross_profit, gross_margin: fin.gross_margin,
    selling_to_gross: fin.selling_to_gross, admin_to_gross: fin.admin_to_gross,
    selling_admin_to_gross: fin.selling_admin_to_gross, rd_to_gross: fin.rd_to_gross,
    sga_rd_to_gross: fin.sga_rd_to_gross, finance_expense: fin.finance_expense,
    finance_to_gross: fin.finance_to_gross, operating_profit: fin.operating_profit,
    hard_profit: fin.hard_profit, total_profit: fin.total_profit,
    parent_net_profit: fin.parent_net_profit, deducted_net_profit: fin.deducted_net_profit,
    inventory: fin.inventory, anchor_assets: fin.anchor_assets,
    anchor_asset_ratio: fin.anchor_asset_ratio, effective_asset_return: fin.effective_asset_return,
    net_profit_margin: fin.net_profit_margin, advance_contract_liab: fin.advance_contract_liab,
    advance_to_revenue: fin.advance_to_revenue, debt_ratio_ex_advance: fin.debt_ratio_ex_advance,
    debt_equity_ex_cash: fin.debt_equity_ex_cash, roe: fin.roe,
    total_shares: fin.total_shares,
  }
  return map[indicator] != null ? Number(map[indicator]) : null
}
</script>

<style scoped>
.sector-insight {
  max-width: 1300px;
  margin: 0 auto;
}

/* ===== 头部筛选区域 ===== */
.filter-bar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.filter-left {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-group label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.filter-group select {
  padding: 10px 36px 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  background: #fff;
  color: #1e293b;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  min-width: 160px;
  outline: none;
  transition: border-color 0.15s;
}

.filter-group select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px #dbeafe;
}

.filter-right {
  display: flex;
  align-items: flex-end;
  padding-bottom: 2px;
}

.current-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 13px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.badge-label {
  color: #94a3b8;
}

.badge-value {
  color: #1e293b;
  font-weight: 600;
}

.badge-sep {
  color: #cbd5e1;
  margin: 0 2px;
}

/* ===== 统计卡片 ===== */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 18px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.stat-label {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.stat-value.blue { color: #2563eb; }
.stat-value.green { color: #10b981; }
.stat-value.red { color: #ef4444; }
.stat-value.orange { color: #f59e0b; }

.stat-unit {
  font-size: 13px;
  font-weight: 500;
  color: #94a3b8;
}

/* ===== 图表卡片 ===== */
.chart-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  margin-bottom: 24px;
}

.chart-card-title {
  margin: 0 0 16px 0;
  font-size: 17px;
  font-weight: 700;
  color: #111;
}

.chart-card-subtitle {
  font-size: 13px;
  font-weight: 400;
  color: #94a3b8;
}

.chart-wrap {
  height: 500px;
}

/* ===== 表格卡片 ===== */
.table-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  overflow: hidden;
}

.table-card table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.table-card th {
  text-align: left;
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.table-card td {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  color: #1e293b;
}

.table-card tbody tr:hover td {
  background: #f8fafc;
}

.col-rank { width: 64px; text-align: center; }
.col-value { text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }

.rank-num {
  color: #94a3b8;
  font-weight: 500;
}

.rank-badge {
  font-size: 18px;
}

.col-name { font-weight: 600; }
.col-code { color: #64748b; font-family: 'SF Mono', monospace; font-size: 13px; }
.col-industry { color: #64748b; font-size: 13px; }

/* ===== Loading / Empty ===== */
.loading {
  text-align: center;
  padding: 60px 20px;
  color: #64748b;
}
.loading p { margin-top: 12px; }
.spinner {
  display: inline-block;
  width: 32px;
  height: 32px;
  border: 3px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #64748b;
}
.empty-state h3 { margin-bottom: 8px; color: #334155; }

/* ===== 响应式 ===== */
@media (max-width: 900px) {
  .filter-bar {
    flex-direction: column;
  }

  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .chart-wrap {
    height: 350px;
  }
}

@media (max-width: 600px) {
  .stats-row {
    grid-template-columns: 1fr;
  }
}
</style>