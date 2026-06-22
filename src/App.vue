<template>
  <div class="app">
    <nav class="navbar">
      <div class="nav-inner">
        <router-link to="/" class="logo">A股财务数据</router-link>
        <div class="nav-links">
          <router-link to="/" exact-active-class="active-link">搜索公司</router-link>
          <router-link to="/watchlist" active-class="active-link">自选列表</router-link>
          <router-link to="/metrics" active-class="active-link">指标统计</router-link>
          <router-link to="/charts" active-class="active-link">趋势图表</router-link>
          <router-link to="/money-machine" active-class="active-link">赚钱机器</router-link>
          <router-link to="/buffett" active-class="active-link">巴菲特指标</router-link>
          <router-link to="/sector-insight" active-class="active-link">行业洞察</router-link>
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
