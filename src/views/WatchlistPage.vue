<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">自选列表</h1>
      <span style="color: var(--text-secondary); font-size: 14px;">{{ watchlist.length }} 家公司</span>
    </div>

    <div v-if="loading" class="loading"><div class="spinner"></div></div>

    <div v-else-if="watchlist.length === 0" class="empty-state">
      <h3>暂无自选公司</h3>
      <p>去搜索页面添加感兴趣的公司</p>
      <router-link to="/" class="btn btn-primary" style="margin-top: 16px; text-decoration: none;">去搜索</router-link>
    </div>

    <div v-else>
      <div v-for="item in enrichedWatchlist" :key="item.code" class="card" style="margin-bottom: 12px;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div>
            <div style="font-weight: 600; font-size: 16px;">
              {{ item.name }}
              <span style="color: var(--text-secondary); font-weight: 400; font-size: 13px; margin-left: 8px;">{{ item.code }}</span>
            </div>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <span v-if="item.pe" class="badge badge-gray">PE {{ item.pe }}</span>
            <span v-if="item.pb" class="badge badge-gray">PB {{ item.pb }}</span>
            <button class="btn btn-danger btn-sm" @click="removeStock(item.code)">移除</button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="toast" :class="['toast', toastType]">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getWatchlist, removeFromWatchlist, getFinancialIndicators, getCompanyNames } from '../lib/supabase.js'

const watchlist = ref([])
const indicators = ref([])
const loading = ref(true)
const toast = ref('')
const toastType = ref('toast-success')

const enrichedWatchlist = computed(() => {
  const indMap = {}
  for (const ind of indicators.value) {
    indMap[ind.code] = ind
  }
  return watchlist.value.map(item => {
    const ind = indMap[item.code] || {}
    return {
      code: item.code,
      name: item.name,
      pe: ind.pe_ratio ? Number(ind.pe_ratio).toFixed(1) : null,
      pb: ind.pb_ratio ? Number(ind.pb_ratio).toFixed(2) : null,
    }
  })
})

onMounted(async () => {
  try {
    const [wl, names] = await Promise.all([
      getWatchlist(),
      getCompanyNames([])
    ])
    // getWatchlist returns {code, companies(name)}
    watchlist.value = wl.map(item => ({
      code: item.code,
      name: item.companies?.name || item.code,
    }))

    const codes = watchlist.value.map(w => w.code)
    if (codes.length > 0) {
      // get names for display
      const nameMap = await getCompanyNames(codes)
      watchlist.value = codes.map(code => ({
        code,
        name: nameMap[code] || code,
      }))
      indicators.value = await getFinancialIndicators(codes)
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

async function removeStock(code) {
  try {
    await removeFromWatchlist(code)
    watchlist.value = watchlist.value.filter(w => w.code !== code)
    const name = watchlist.value.find(w => w.code === code)?.name || code
    showToast('已移除')
  } catch (e) {
    showToast('移除失败', 'toast-error')
  }
}

function showToast(msg, type = 'toast-success') {
  toast.value = msg
  toastType.value = type
  setTimeout(() => { toast.value = '' }, 2000)
}
</script>
