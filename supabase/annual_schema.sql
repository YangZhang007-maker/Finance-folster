-- 年度财务数据表 (10年历史)
DROP TABLE IF EXISTS annual_financials CASCADE;

CREATE TABLE annual_financials (
  id SERIAL PRIMARY KEY,
  code VARCHAR(10) NOT NULL,
  report_date DATE NOT NULL,
  roe REAL,
  roa REAL,
  gross_margin REAL,
  net_margin REAL,
  debt_to_assets REAL,
  net_profit REAL,
  total_revenue REAL,
  gross_profit REAL,
  net_assets REAL,
  free_cash_flow REAL,
  revenue_growth REAL,
  net_profit_growth REAL,
  current_ratio REAL,
  pe_ratio REAL,
  pb_ratio REAL,
  market_cap REAL,
  buffett_index REAL,
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(code, report_date)
);

CREATE INDEX idx_annual_code ON annual_financials(code);
CREATE INDEX idx_annual_date ON annual_financials(report_date);

ALTER TABLE annual_financials ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read annual" ON annual_financials FOR SELECT USING (true);
CREATE POLICY "Allow public insert annual" ON annual_financials FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update annual" ON annual_financials FOR UPDATE USING (true);