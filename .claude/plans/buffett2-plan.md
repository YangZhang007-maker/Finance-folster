# 巴菲特指标2 模块实施计划

## 需求理解

创建一个新的"巴菲特指标2"页面，核心逻辑：
- **数据字段**：与"巴菲特指标"完全一致（10 个图表，使用 `annual_financials_v2` 的同一批字段）
- **图表样式**：与"趋势图表"一致（单指标简洁风，蓝色调，无 tooltip，数据标签标注在图表上，tooltip disabled）
- **每个指标独立成图**：不做双轴混合图，每个指标一个独立图表卡片

## 关键差异分析

### 巴菲特指标 vs 趋势图表的样式差异

| 对比维度 | 趋势图表（目标风格） | 巴菲特指标（当前风格） |
|---------|-------------------|---------------------|
| 颜色 | 统一蓝色 `#5A75C7` | 多色（蓝/橙/绿/红/紫） |
| Tooltip | **disabled** | enabled |
| 数据标签 | 自定义 `dataLabels` plugin 标注在柱/点上 | 无 |
| 图表标题 | 大号 `h3` 20px bold | 小号 `h3` 16px bold |
| 图表高度 | 400px | 350px |
| 图例 | 隐藏 | 双轴图显示 |
| Y 轴样式 | 简洁灰线 | 标准 |
| 单位 | 亿 / % | 万元 / % / x |
| 卡片 padding | 24px | 20px |
| 布局 | 单列，每图一个卡片 | 2 列网格 |

### 巴菲特指标10个图表 → 拆分为独立指标

现有巴菲特指标图表及拆分方案：

| # | 原图表 | 拆分后独立指标 | 图表类型 | 单位 |
|---|--------|-------------|---------|------|
| 1 | 毛利润 vs 毛利率（双轴） | ① 毛利润 + ② 毛利率 | Bar + Line | 亿 + % |
| 2 | 毛利率变化趋势 | ③ 毛利率趋势 | Line | % |
| 3 | 三费占毛利比（堆叠面积） | ④ 销售费用/毛利 ⑤ 管理费用/毛利 ⑥ 研发费用/毛利 | Line ×3 | % |
| 4 | 销管研三费合计占毛利比 | ⑦ 销管研三费合计/毛利 | Line | % |
| 5 | 经营利润 vs 归母净利润 | ⑧ 经营利润 + ⑨ 归母净利润 | Bar ×2 | 亿 |
| 6 | 扣非净利润趋势 | ⑩ 扣非净利润 | Bar | 亿 |
| 7 | 存货 vs 预收款 | ⑪ 存货 + ⑫ 预收款 | Bar ×2 | 亿 |
| 8 | 预收款占总营收比 | ⑬ 预收款/营收 | Line | % |
| 9 | 剔除预收款后的资产负债率 | ⑭ 资产负债率(剔预收) | Line | % |
| 10 | 剔除预收款后的债务股权比 | ⑮ 债务股权比(剔预收) | Line | x |

**共 15 个独立图表卡片**，每个卡片一个指标，使用趋势图表的简洁蓝色风格。

## 实施步骤

### Step 1: 创建路由
- 在 `src/router/index.js` 添加 `/buffett2` 路由，指向 `Buffett2Page.vue`

### Step 2: 创建页面组件
- 新建 `src/views/buffett2/Buffett2Page.vue`

### Step 3: 导航栏添加入口
- 在 `src/App.vue` 导航栏添加"巴菲特指标2"链接

### Step 4: 实现组件逻辑
组件结构：
- 搜索逻辑：复用 `getAnnualFinancialsV2` + `searchCompanies`（与巴菲特指标一致）
- 数据源：`annual_financials_v2` 表，2016-2025 年
- 样式：全盘采用 TrendChartPage 的蓝色简洁风格

15 个图表配置：

| 图表 | 字段 | 类型 | 颜色 | 单位 | 数据转换 |
|------|------|------|------|------|---------|
| 毛利润 | gross_profit | Bar | #5A75C7 | 亿 | / 1e8 |
| 毛利率 | gross_margin | Line | #5A75C7 | % | 原值 |
| 毛利率趋势 | gross_margin | Line | #5A75C7 | % | 原值（与上相同，但这是独立副本） |
| 销售费用/毛利 | selling_to_gross | Line | #5A75C7 | % | 原值 |
| 管理费用/毛利 | admin_to_gross | Line | #5A75C7 | % | 原值 |
| 研发费用/毛利 | rd_to_gross | Line | #5A75C7 | % | 原值 |
| 销管研三费/毛利 | sga_rd_to_gross | Line | #5A75C7 | % | 原值 |
| 经营利润 | operating_profit | Bar | #5A75C7 | 亿 | / 1e8 |
| 归母净利润 | parent_net_profit | Bar | #5A75C7 | 亿 | / 1e8 |
| 扣非净利润 | deducted_net_profit | Bar | #5A75C7 | 亿 | / 1e8 |
| 存货 | inventory | Bar | #5A75C7 | 亿 | / 1e8 |
| 预收款 | advance_contract_liab | Bar | #5A75C7 | 亿 | / 1e8 |
| 预收款/营收 | advance_to_revenue | Line | #5A75C7 | % | 原值 |
| 资产负债率(剔预收) | debt_ratio_ex_advance | Line | #5A75C7 | % | 原值，保留50%警戒线 |
| 债务股权比(剔预收) | debt_equity_ex_cash | Line | #5A75C7 | x | 原值 |

注意：毛利率"和"毛利率趋势"字段相同，合并为一个图表，实际共 **14 个独立图表**。

### Step 5: 验证
- 启动 `npm run dev` 验证页面正常工作

## 文件变更清单

| 文件 | 操作 |
|------|------|
| `src/router/index.js` | 修改：添加路由 |
| `src/App.vue` | 修改：添加导航链接 |
| `src/views/buffett2/Buffett2Page.vue` | 新建：页面组件 |

## 技术要点

1. 完全复用 TrendChartPage 的样式系统：`baseOptions(unit)`、`dataLabels` plugin、`BLUE` 色值、卡片布局
2. 数据源使用 `getAnnualFinancialsV2`（与 BuffettPage 一致）
3. 金额字段统一转换为"亿"（/ 1e8），百分比保持原值
4. 资产负债率图保留 50% 警戒线（annotation plugin）
5. 无合并图、无双轴图，每个指标独立成图