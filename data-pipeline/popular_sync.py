"""Sync popular A-share stocks' financial data."""
import os, time
import pandas as pd
import akshare as ak
from supabase import create_client
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

supabase = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

POPULAR = [
    '600519','000858','002594','601398','601939','601288',
    '600036','601318','000333','300750','601857','600900',
    '601166','600276','600030','000651','002415','601012',
    '600809','000568','000725','603259','688981','300059',
    '002475','601899','600585','000002','601088','600028',
    '600031','600104','002714','300015','601668','600690',
    '600887','000063','002230','300124','688111','600436',
    '600309','002049','603986','300760','601615','002142',
    '600048','000001',
]

def gv(series, key):
    val = series.get(key)
    return None if val is None or (isinstance(val, float) and pd.isna(val)) else float(val)

batch = []
for i, code in enumerate(POPULAR):
    try:
        df = ak.stock_financial_abstract(symbol=code)
        date_cols = [c for c in df.columns if c not in ("选项","指标") and str(c).isdigit()]
        if not date_cols:
            continue
        latest = date_cols[0]
        common = df[df["选项"]=="常用指标"].set_index("指标")[latest]
        growth = df[df["选项"]=="成长能力"].set_index("指标")[latest]
        risk = df[df["选项"]=="财务风险"].set_index("指标")[latest]
        ind = {
            "code": code, "report_date": f"{latest[:4]}-{latest[4:6]}-{latest[6:]}",
            "roe": gv(common,"净资产收益率(ROE)"), "roa": gv(common,"总资产报酬率(ROA)"),
            "gross_margin": gv(common,"毛利率"), "net_margin": gv(common,"销售净利率"),
            "debt_to_assets": gv(common,"资产负债率"), "net_profit": gv(common,"净利润"),
            "total_revenue": gv(common,"营业总收入"), "net_assets": gv(common,"每股净资产"),
            "free_cash_flow": gv(common,"每股现金流"),
            "revenue_growth": gv(growth,"营业总收入增长率"),
            "net_profit_growth": gv(growth,"归属母公司净利润增长率"),
            "current_ratio": gv(risk,"流动比率"),
        }
        batch.append(ind)
        print(f'{i+1}/{len(POPULAR)}: {code} OK')
    except Exception as e:
        print(f'{code}: {e}')
    time.sleep(1.5)

if batch:
    clean = [{k:v for k,v in ind.items() if v is not None} for ind in batch]
    supabase.table("financial_indicators").upsert(clean, on_conflict="code,report_date").execute()
    print(f'Upserted {len(clean)} stocks')
