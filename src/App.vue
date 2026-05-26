<template>
  <div class="app">
    <nav class="navbar">
      <div class="nav-inner">
        <router-link to="/" class="logo">A股财务数据</router-link>
        <div class="nav-links">
          <router-link to="/" exact-active-class="active-link">搜索公司</router-link>
          <router-link to="/watchlist" active-class="active-link">自选列表</router-link>
          <router-link to="/metrics" active-class="active-link">指标统计</router-link>
        </div>
      </div>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>
