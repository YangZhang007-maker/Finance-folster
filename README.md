# A股财务数据平台

A股公司财务数据搜索、自选列表管理、多年指标趋势图表展示、行业洞察分析。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3 (Composition API) + Vite 8 |
| 路由 | Vue Router 4 |
| 图表库 | Chart.js 4 (vue-chartjs) + ECharts 6 (vue-echarts) |
| 数据库 | Supabase (PostgreSQL) |
| 数据管道 | Python 3 + AKShare + requests |
| 部署 | Vercel (前端) + GitHub Actions (定时同步) |
| 数据源 | 东方财富 DataCenter API / 新浪财经 API |

## 项目结构

```
a-share-finance/
├── src/                          # Vue 3 前端源码
│   ├── main.js                   # 应用入口，挂载 Vue + Router
│   ├── App.vue                   # 根组件，含导航栏
│   ├── style.css                 # 全局样式（CSS 变量、组件样式）
│   ├── router/
│   │   └── index.js              # 路由配置（7 个页面）
│   ├── lib/
│   │   └── supabase.js           # Supabase 客户端 + 所有数据查询 API
│   └── views/
│       ├── watchlist/
│       │   ├── SearchPage.vue    # 搜索公司页面
│       │   └── WatchlistPage.vue # 自选列表管理页面
│       ├── metrics/
│       │   └── MetricsPage.vue   # 15 项财务指标统计对比表
│       ├── charts/
│       │   └── TrendChartPage.vue# 10 年财务趋势图表（6 个指标）
│       ├── money-machine/
│       │   └── MoneyMachinePage.vue # 赚钱机器分析（6 张图表）
│       ├── buffett/
│       │   └── BuffettPage.vue   # 巴菲特指标分析（10 张图表）
│       └── sector-insight/
│           └── SectorInsightPage.vue # 行业洞察（Treemap + 排名表）
│
├── data-pipeline/                # Python 数据同步管道
│   ├── sync.py                   # 增量同步：财务指标（PE/PB/ROE等）
│   ├── sync_annual.py            # 全量同步：10 年年度财报（v1，AKShare）
│   ├── sync_annual_v2.py         # 全量同步：v2 扩展版（东方财富DC + 新浪补字段）
│   ├── calc_derived_fields.py    # 计算 15 个派生指标（费用比、资产负债率等）
│   ├── popular_sync.py           # 热门股票同步
│   ├── export_to_local.py        # 数据导出到本地
│   ├── upload_sectors.py         # 上传行业分类映射
│   ├── fetch_sectors_v2.py       # 获取行业分类数据
│   ├── fill_missing_sectors.py   # 补充缺失行业分类
│   ├── add_sector_classification.py # 添加行业分类
│   ├── generate_field_doc.py     # 生成字段说明文档
│   ├── sector_mapping.json       # 行业分类映射数据
│   ├── requirements.txt          # Python 依赖
│   └── run_sync.sh               # 同步脚本入口
│
├── supabase/                     # 数据库 Schema
│   ├── schema.sql                # 核心表：companies, financial_indicators, watchlist
│   ├── annual_schema.sql         # 年度财报表（v1）
│   └── v2_schema.sql             # 扩展年度财报表（v2，30+ 字段）
│
├── .github/workflows/
│   └── sync.yml                  # GitHub Actions：每日定时同步（北京时间 16:30）
├── .env / .env.example           # 环境变量（Supabase 连接配置）
├── vercel.json                   # Vercel 部署配置（SPA rewrite）
├── vite.config.js                # Vite 构建配置
├── index.html                    # HTML 入口
└── package.json                  # 前端依赖
```

## 功能模块

### 1. 搜索公司（`/`）— [SearchPage.vue](src/views/watchlist/SearchPage.vue)
- 输入公司名称或股票代码搜索 A 股（4815 家公司）
- 显示公司名称、代码、行业信息
- 一键加入自选列表

### 2. 自选列表（`/watchlist`）— [WatchlistPage.vue](src/views/watchlist/WatchlistPage.vue)
- 展示已添加的自选公司列表
- 显示 PE、PB 估值指标
- 支持移除操作

### 3. 指标统计（`/metrics`）— [MetricsPage.vue](src/views/metrics/MetricsPage.vue)
- 自选公司 15 项财务指标对比表
- 支持按任意列排序（升序/降序）
- 顶部统计卡片：平均 PE、ROE、PB
- 包含指标：PE、PB、PS、PEG、ROE、ROA、毛利率、净利率、营收增长、利润增长、资产负债率、流动比率、股息率、总市值、巴菲特指标

### 4. 趋势图表（`/charts`）— [TrendChartPage.vue](src/views/charts/TrendChartPage.vue)
- 搜索股票查看 10 年（2016-2025）财务趋势
- 6 个独立指标卡片：毛利润（柱状图）、毛利率（折线图）、净利润（柱状图）、净利率（折线图）、营业总收入（柱状图）、净资产收益率（折线图）
- 使用 Chart.js 渲染，数据标注在图表上

### 5. 赚钱机器（`/money-machine`）— [MoneyMachinePage.vue](src/views/money-machine/MoneyMachinePage.vue)
- 2×3 图表网格，深度分析公司盈利质量
- 6 张图表：资本开支趋势、净利润 vs 同比增速（双轴）、有效资产收益率、硬朗度利润（自由现金流）、锚定资产构成（堆叠柱状图）、锚定资产占比
- 使用 `annual_financials_v2` 表的扩展数据

### 6. 巴菲特指标（`/buffett`）— [BuffettPage.vue](src/views/buffett/BuffettPage.vue)
- 2×5 图表网格，价值投资视角分析
- 10 张图表：毛利润 vs 毛利率、毛利率趋势、三费占毛利比（堆叠面积图）、销管研三费合计占毛利比、经营利润 vs 归母净利润、扣非净利润趋势、存货 vs 预收款、预收款占总营收比、剔除预收款后的资产负债率（含 50% 警戒线）、剔除预收款后的债务股权比

### 7. 行业洞察（`/sector-insight`）— [SectorInsightPage.vue](src/views/sector-insight/SectorInsightPage.vue)
- 按行业（11 大类）+ 会计年度 + 25 个指标维度筛选
- ECharts Treemap 可视化展示行业内公司排名
- 统计卡片：公司数量、平均值、最大值、最小值
- 底部明细表格：排名、公司名称、代码、细分行业、指标值
- 支持指标：毛利润、毛利率、各项费用占毛利比、经营利润、硬朗度利润、归母净利润、扣非净利润、存货、锚定资产、有效资产收益率、预收款、资产负债率、债务股权比、ROE、总股本等

## 数据库表

| 表名 | 用途 | 关键字段 |
|------|------|---------|
| `companies` | 公司基本信息 | code, name, industry, sector |
| `watchlist` | 用户自选列表 | code → companies.code |
| `financial_indicators` | 最新财务指标 | PE/PB/ROE/毛利率等 15 项 |
| `annual_financials` | 年度财报（v1，旧） | 10 年年度数据 |
| `annual_financials_v2` | 年度财报（v2，扩展） | 30+ 字段，含资产负债表/利润表/现金流/派生指标 |

## 数据管道

### 数据源
- **东方财富 DataCenter API**：利润表、资产负债表、现金流量表核心字段
- **新浪财经 API**：补充在建工程、商誉、借款、合同负债、总股本等字段
- **AKShare**：股票列表、财务摘要指标

### 同步流程
1. **`sync.py`**（每日增量）：通过 GitHub Actions 每天北京时间 16:30 自动运行，从 AKShare 获取财务指标并写入 `financial_indicators` 表
2. **`sync_annual_v2.py`**（手动全量）：从东方财富 DC 获取三大报表数据，再用新浪 API 补全缺失字段，写入 `annual_financials_v2` 表
3. **`calc_derived_fields.py`**（手动）：计算 15 个派生指标（费用占比、资产负债率、有效资产收益率等）
4. **`upload_sectors.py`**（手动）：将行业分类映射写入 `companies.sector` 字段

### 运行方式
```bash
cd data-pipeline

# 安装依赖
pip install -r requirements.txt

# 增量同步财务指标
python sync.py

# 全量同步年度财报（v2）
python sync_annual_v2.py

# 计算派生指标
python calc_derived_fields.py
```

## 本地开发

```bash
# 安装依赖
npm install

# 配置环境变量
cp .env.example .env.local
# 编辑 .env.local，填入 Supabase URL 和 anon key

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 部署

- **前端**：部署在 [Vercel](https://vercel.com)，通过 `vercel.json` 配置 SPA rewrite
- **数据同步**：通过 GitHub Actions 每日定时运行（`.github/workflows/sync.yml`），北京时间 16:30

## 数据覆盖

- **股票数量**：4815 只 A 股（沪深北）
- **时间跨度**：2016-2025 年度（10 年）
- **行业分类**：11 大类（日常消费、可选消费、信息技术、工业、金融、房地产、材料、公用事业、医疗保健、能源、通讯服务）