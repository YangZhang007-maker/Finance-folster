-- ============================================================
-- annual_financials_v2: 扩展版年度财务数据表
-- 数据源: 新浪财经 stock_financial_report_sina (三大报表)
--         + annual_financials 旧表数据迁移
--         + datacenter API 补充 (扣非净利润)
-- ============================================================

CREATE TABLE IF NOT EXISTS annual_financials_v2 (
  id BIGSERIAL PRIMARY KEY,
  code VARCHAR(10) NOT NULL,
  stock_name VARCHAR(50),
  year INTEGER NOT NULL,

  -- === 从旧表 annual_financials 迁移 ===
  total_revenue NUMERIC(20,2),         -- 营业总收入
  gross_profit NUMERIC(20,2),          -- 毛利润
  gross_margin NUMERIC(10,4),          -- 毛利率(%)
  net_margin NUMERIC(10,4),            -- 净利率(%)
  roe NUMERIC(10,4),                   -- 净资产收益率(%)
  total_market_cap NUMERIC(20,2),      -- 总市值
  revenue_yoy NUMERIC(10,4),           -- 营业总收入同比增长率(%)
  net_profit_yoy NUMERIC(10,4),        -- 归母净利润同比增长率(%)
  eps NUMERIC(10,4),                   -- 基本每股收益
  bps NUMERIC(10,4),                   -- 每股净资产
  roa NUMERIC(10,4),                   -- 总资产报酬率(%)

  -- === 利润表 (新浪财经) ===
  operating_revenue NUMERIC(20,2),     -- 营业收入
  operating_cost NUMERIC(20,2),        -- 营业成本
  selling_expense NUMERIC(20,2),       -- 销售费用
  admin_expense NUMERIC(20,2),         -- 管理费用
  rd_expense NUMERIC(20,2),            -- 研发费用
  finance_expense NUMERIC(20,2),       -- 财务费用
  operating_profit NUMERIC(20,2),      -- 营业利润
  total_profit NUMERIC(20,2),          -- 利润总额
  parent_net_profit NUMERIC(20,2),     -- 归母净利润
  deducted_net_profit NUMERIC(20,2),   -- 扣非净利润 (从datacenter API补)

  -- === 资产负债表 (新浪财经) ===
  advance_contract_liab NUMERIC(20,2), -- 预收款/合同负债 (2017前取预收款项，2017后取合同负债)
  inventory NUMERIC(20,2),             -- 存货
  fixed_asset NUMERIC(20,2),           -- 固定资产
  construction_in_progress NUMERIC(20,2), -- 在建工程
  cash_and_equivalents NUMERIC(20,2),  -- 现金及现金等价物 (货币资金)
  goodwill NUMERIC(20,2),              -- 商誉
  short_term_loan NUMERIC(20,2),       -- 短期借款
  long_term_loan NUMERIC(20,2),        -- 长期借款
  bonds_payable NUMERIC(20,2),         -- 应付债券
  total_shares NUMERIC(20,2),          -- 总股本 (实收资本)
  total_assets NUMERIC(20,2),          -- 总资产
  total_liabilities NUMERIC(20,2),     -- 总负债
  parent_equity NUMERIC(20,2),         -- 归母股东权益 (净资产)

  -- === 现金流量表 (新浪财经) ===
  operating_cash_flow NUMERIC(20,2),   -- 经营活动现金流净额
  capex NUMERIC(20,2),                 -- 购建固定资产、无形资产和其他长期资产支付的现金

  -- === 计算指标 (派生字段) ===
  effective_asset_return NUMERIC(12,4),      -- 有效资产收益率 = 归母净利润/(总资产-货币资金-商誉)*100
  hard_profit NUMERIC(20,2),                 -- 硬朗度利润 = 经营现金流净额 - 资本开支
  anchor_assets NUMERIC(20,2),               -- 锚定资产 = 固定资产+在建工程+存货
  anchor_asset_ratio NUMERIC(12,4),          -- 锚定资产占比 = 锚定资产/总资产*100
  net_profit_margin NUMERIC(12,4),           -- 净利润率 = 归母净利润/营业收入*100
  eps_calculated NUMERIC(12,4),              -- 每股净利润 = 归母净利润/总股本
  selling_to_gross NUMERIC(12,4),            -- 销售费用占毛利比
  admin_to_gross NUMERIC(12,4),              -- 管理费用占毛利比
  selling_admin_to_gross NUMERIC(12,4),      -- 销售+管理费用占毛利比
  rd_to_gross NUMERIC(12,4),                 -- 研发费用占毛利比
  sga_rd_to_gross NUMERIC(12,4),             -- 销管研三费占毛利比
  finance_to_gross NUMERIC(12,4),            -- 财务费用占毛利比
  advance_to_revenue NUMERIC(12,4),          -- 预收款占总营收比
  debt_ratio_ex_advance NUMERIC(12,4),       -- 剔除预收款后资产负债率
  debt_equity_ex_cash NUMERIC(20,4),         -- 剔除预收款后债务股权比

  -- === 元数据 ===
  data_source VARCHAR(50) DEFAULT 'sina',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE(code, year)
);

-- ============================================================
-- RLS 策略 (与旧表一致: 公开读写)
-- ============================================================
ALTER TABLE annual_financials_v2 ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for all" ON annual_financials_v2
  FOR SELECT USING (true);

CREATE POLICY "Enable insert for all" ON annual_financials_v2
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update for all" ON annual_financials_v2
  FOR UPDATE USING (true);

-- ============================================================
-- 索引
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_v2_code ON annual_financials_v2(code);
CREATE INDEX IF NOT EXISTS idx_v2_code_year ON annual_financials_v2(code, year);
CREATE INDEX IF NOT EXISTS idx_v2_year ON annual_financials_v2(year);