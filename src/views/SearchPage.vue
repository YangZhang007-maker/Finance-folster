<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">搜索公司</h1>
    </div>

    <div class="search-box">
      <span class="search-icon">&#x1F50D;</span>
      <input
        v-model="query"
        class="input"
        placeholder="输入公司名称或股票代码搜索..."
        @input="onSearch"
        autofocus
      />
    </div>

    <div v-if="loading" class="loading"><div class="spinner"></div></div>

    <div v-else-if="query && results.length === 0 && searched" class="empty-state">
      <h3>未找到相关公司</h3>
      <p>试试其他关键词</p>
    </div>

    <div v-else-if="results.length > 0" class="results-list">
      <div v-for="stock in results" :key="stock.code" class="card" style="margin-bottom: 12px;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div>
            <div style="font-weight: 600; font-size: 16px;">
              {{ stock.name }}
              <span style="color: var(--text-secondary); font-weight: 400; font-size: 13px; margin-left: 8px;">{{ stock.code }}</span>
            </div>
            <div style="color: var(--text-secondary); font-size: 13px; margin-top: 2px;">
              {{ stock.industry || '-' }}
            </div>
          </div>
          <div style="display: flex; gap: 8px; align-items: center;">
            <button
              v-if="isInWatchlist(stock.code)"
              class="btn btn-sm"
              style="color: var(--success); border-color: var(--success);"
              disabled
            >已添加</button>
            <button
              v-else
              class="btn btn-primary btn-sm"
              @click="addStock(stock)"
            >加入自选</button>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="!query" class="empty-state">
      <h3>输入关键词搜索A股公司</h3>
      <p>支持公司名称、股票代码</p>
    </div>

    <div v-if="toast" :class="['toast', toastType]">{{ toast }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { searchCompanies, addToWatchlist, getWatchlist } from '../lib/supabase.js'

const query = ref('')
const results = ref([])
const loading = ref(false)
const searched = ref(false)
const watchlist = ref(new Set())
const toast = ref('')
const toastType = ref('toast-success')

let debounceTimer = null

async function loadWatchlist() {
  try {
    const data = await getWatchlist()
    watchlist.value = new Set(data.map(d => d.code))
  } catch (e) {
    // silent
  }
}

function isInWatchlist(code) {
  return watchlist.value.has(code)
}

function onSearch() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(async () => {
    if (!query.value.trim()) {
      results.value = []
      searched.value = false
      return
    }
    loading.value = true
    searched.value = true
    try {
      results.value = await searchCompanies(query.value.trim())
    } catch (e) {
      results.value = []
      showToast('搜索失败，请重试', 'toast-error')
    } finally {
      loading.value = false
    }
  }, 300)
}

async function addStock(stock) {
  try {
    await addToWatchlist(stock.code)
    watchlist.value.add(stock.code)
    showToast(`${stock.name} 已加入自选`)
  } catch (e) {
    showToast('添加失败，请重试', 'toast-error')
  }
}

function showToast(msg, type = 'toast-success') {
  toast.value = msg
  toastType.value = type
  setTimeout(() => { toast.value = '' }, 2000)
}

loadWatchlist()
</script>
