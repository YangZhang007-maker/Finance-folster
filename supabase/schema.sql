-- A-Share Finance: Database Schema
-- Run this in Supabase SQL Editor

-- 1. Companies table
CREATE TABLE companies (
  id SERIAL PRIMARY KEY,
  code VARCHAR(10) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  industry VARCHAR(100),
  market VARCHAR(10),  -- SH, SZ, BJ
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_companies_code ON companies(code);
CREATE INDEX idx_companies_name ON companies(name);

-- 2. Financial indicators table
CREATE TABLE financial_indicators (
  id SERIAL PRIMARY KEY,
  code VARCHAR(10) NOT NULL REFERENCES companies(code),
  report_date DATE NOT NULL,
  -- Valuation
  pe_ratio DECIMAL(18,4),
  pb_ratio DECIMAL(18,4),
  ps_ratio DECIMAL(18,4),
  peg_ratio DECIMAL(18,4),
  -- Profitability
  roe DECIMAL(18,4),
  roa DECIMAL(18,4),
  gross_margin DECIMAL(18,4),
  net_margin DECIMAL(18,4),
  -- Growth
  revenue_growth DECIMAL(18,4),
  net_profit_growth DECIMAL(18,4),
  -- Financial health
  debt_to_assets DECIMAL(18,4),
  current_ratio DECIMAL(18,4),
  free_cash_flow DECIMAL(18,4),
  -- Dividend
  dividend_yield DECIMAL(18,4),
  -- Market data
  market_cap DECIMAL(18,4),
  total_revenue DECIMAL(18,4),
  net_profit DECIMAL(18,4),
  total_assets DECIMAL(18,4),
  net_assets DECIMAL(18,4),
  -- Custom composite
  buffett_index DECIMAL(18,4),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(code, report_date)
);

CREATE INDEX idx_fin_code ON financial_indicators(code);
CREATE INDEX idx_fin_date ON financial_indicators(report_date);
CREATE INDEX idx_fin_code_date ON financial_indicators(code, report_date);

-- 3. Watchlist table
CREATE TABLE watchlist (
  id SERIAL PRIMARY KEY,
  code VARCHAR(10) NOT NULL REFERENCES companies(code),
  added_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(code)
);

-- Enable RLS (Row Level Security) for public access
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_indicators ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;

-- Public read policies
CREATE POLICY "Allow public read companies" ON companies FOR SELECT USING (true);
CREATE POLICY "Allow public read indicators" ON financial_indicators FOR SELECT USING (true);
CREATE POLICY "Allow public read watchlist" ON watchlist FOR SELECT USING (true);

-- Public write policies (since this is a personal dashboard)
CREATE POLICY "Allow public insert watchlist" ON watchlist FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public delete watchlist" ON watchlist FOR DELETE USING (true);
CREATE POLICY "Allow public insert companies" ON companies FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public insert indicators" ON financial_indicators FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update indicators" ON financial_indicators FOR UPDATE USING (true);
