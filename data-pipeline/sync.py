"""
A-Share Financial Data Sync Script
Fetches data from AKShare and upserts to Supabase.
Designed to run daily via GitHub Actions.
"""
import os
import time
import pandas as pd
import akshare as ak
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
BATCH_SIZE = 20
DELAY_BETWEEN_BATCHES = 5
DELAY_BETWEEN_STOCKS = 1.5
MAX_STOCKS = 300

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_all_stocks():
    """Fetch all A-share stock codes and names."""
    print("Fetching all A-share stocks...")
    df = ak.stock_info_a_code_name()
    df = df.rename(columns={"code": "code", "name": "name"})
    df["code"] = df["code"].astype(str).str.zfill(6)
    df = df[df["code"].str.match(r"^(60|00|30|68)\d{4}$")]
    print(f"Got {len(df)} stocks")
    return df


def upsert_companies(df):
    """Upsert companies table."""
    print("Upserting companies...")
    rows = []
    for _, row in df.iterrows():
        rows.append({"code": row["code"], "name": str(row.get("name", ""))[:100]})
        if len(rows) >= 100:
            supabase.table("companies").upsert(rows, on_conflict="code").execute()
            rows = []
            time.sleep(0.5)
    if rows:
        supabase.table("companies").upsert(rows, on_conflict="code").execute()
    print(f"Upserted {len(df)} companies.")


def get_val(series, key):
    val = series.get(key)
    if val is None:
        return None
    if isinstance(val, float) and pd.isna(val):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def fetch_financial_abstract(code):
    """Fetch detailed financial indicators for a single stock."""
    try:
        df = ak.stock_financial_abstract(symbol=code)
        if df.empty:
            return None

        date_cols = [c for c in df.columns if c not in ("选项", "指标") and str(c).isdigit()]
        if not date_cols:
            return None
        latest_date = date_cols[0]

        common = df[df["选项"] == "常用指标"].set_index("指标")[latest_date]
        growth = df[df["选项"] == "成长能力"].set_index("指标")[latest_date]
        risk = df[df["选项"] == "财务风险"].set_index("指标")[latest_date]

        result = {
            "code": code,
            "report_date": f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:]}",
            "roe": get_val(common, "净资产收益率(ROE)"),
            "roa": get_val(common, "总资产报酬率(ROA)"),
            "gross_margin": get_val(common, "毛利率"),
            "net_margin": get_val(common, "销售净利率"),
            "debt_to_assets": get_val(common, "资产负债率"),
            "net_profit": get_val(common, "净利润"),
            "total_revenue": get_val(common, "营业总收入"),
            "net_assets": get_val(common, "每股净资产"),
            "free_cash_flow": get_val(common, "每股现金流"),
            "revenue_growth": get_val(growth, "营业总收入增长率"),
            "net_profit_growth": get_val(growth, "归属母公司净利润增长率"),
            "current_ratio": get_val(risk, "流动比率"),
        }
        return result
    except Exception as e:
        print(f"  Error {code}: {e}")
        return None


def compute_composite(ind):
    """Compute composite indicators."""
    if not ind:
        return ind
    pe = ind.get("pe_ratio")
    growth = ind.get("net_profit_growth")
    if pe and growth and growth > 0:
        ind["peg_ratio"] = round(pe / growth, 4)

    # Buffett index approximation: ROE / PB or other composite
    roe = ind.get("roe")
    na = ind.get("net_assets")
    if roe and roe > 0:
        ind["buffett_index"] = round(roe, 4)

    return ind


def sync_all():
    print("=== Starting A-Share Financial Data Sync ===")

    # Step 1: Fetch all stocks
    stocks = fetch_all_stocks()
    upsert_companies(stocks)

    # Step 2: Sample stocks evenly across all code prefixes
    # (stock_info_a_code_name returns codes sorted: 000xxx first, 600xxx last)
    step = max(1, len(stocks) // MAX_STOCKS)
    sampled = stocks.iloc[::step].head(MAX_STOCKS)
    codes = sampled["code"].tolist()

    print(f"\nFetching financial indicators for {len(codes)} stocks...")
    batch = []

    for i, code in enumerate(codes):
        if i > 0 and i % BATCH_SIZE == 0:
            print(f"  Progress: {i}/{len(codes)}")
            upsert_batch(batch)
            batch = []
            time.sleep(DELAY_BETWEEN_BATCHES)

        fin = fetch_financial_abstract(code)
        if fin:
            compute_composite(fin)
            batch.append(fin)

        time.sleep(DELAY_BETWEEN_STOCKS)

    # Final batch
    if batch:
        upsert_batch(batch)

    print(f"=== Sync complete. Processed {len(codes)} stocks ===")


def upsert_batch(batch):
    if not batch:
        return
    clean = [{k: v for k, v in ind.items() if v is not None} for ind in batch]
    try:
        supabase.table("financial_indicators").upsert(
            clean, on_conflict="code,report_date"
        ).execute()
        print(f"  Upserted {len(clean)} indicators")
    except Exception as e:
        print(f"  Upsert error: {e}")


if __name__ == "__main__":
    sync_all()
