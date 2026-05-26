"""
A-Share Financial Data Sync Script
Usage:
  python sync.py          # incremental: only stocks with stale/updated data
  python sync.py --full   # full: process all stocks (~2 hours)
"""
import os, sys, time
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
INCREMENTAL_DAYS = 30  # in incremental mode, skip stocks synced within this many days

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def retry_with_backoff(fn, name, max_retries=3):
    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as e:
            wait = (attempt + 1) * 10
            print(f"  {name} attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
    raise Exception(f"{name} failed after {max_retries} attempts")


def fetch_all_stocks():
    print("Fetching all A-share stocks...")
    def _fetch():
        df = ak.stock_info_a_code_name()
        df = df.rename(columns={"code": "code", "name": "name"})
        df["code"] = df["code"].astype(str).str.zfill(6)
        df = df[df["code"].str.match(r"^(60|00|30|68)\d{4}$")]
        return df

    df = retry_with_backoff(_fetch, "stock_info_a_code_name")
    print(f"Got {len(df)} stocks")
    return df


def upsert_companies(df):
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
    for attempt in range(3):
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

            return {
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
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
            else:
                print(f"  Error {code}: {e}")
                return None


def load_existing_data():
    """Load existing report dates from Supabase to determine stale stocks."""
    print("Loading existing data for incremental check...")
    result = supabase.table("financial_indicators").select("code,report_date,updated_at").execute()
    existing = {}
    for row in result.data:
        code = row["code"]
        # Keep the most recent entry per code
        if code not in existing or row.get("report_date", "") > existing[code].get("report_date", ""):
            existing[code] = row
    print(f"  Found {len(existing)} stocks with existing data")
    return existing


def compute_composite(ind):
    if not ind:
        return ind
    pe = ind.get("pe_ratio")
    growth = ind.get("net_profit_growth")
    if pe and growth and growth > 0:
        ind["peg_ratio"] = round(pe / growth, 4)
    roe = ind.get("roe")
    if roe and roe > 0:
        ind["buffett_index"] = round(roe, 4)
    return ind


def sync(mode="incr"):
    full = mode == "full"
    print(f"=== Starting A-Share Financial Data Sync (mode: {mode}) ===")

    # Step 1: Fetch all stocks and upsert companies
    stocks = fetch_all_stocks()
    upsert_companies(stocks)

    # Step 2: Determine which stocks to process
    all_codes = stocks["code"].tolist()
    codes_to_process = all_codes

    if not full:
        existing = load_existing_data()
        stale_codes = []
        new_codes = []
        for code in all_codes:
            if code not in existing:
                new_codes.append(code)
            else:
                # Check if data is older than INCREMENTAL_DAYS
                updated = existing[code].get("updated_at", "")
                if updated:
                    from datetime import datetime, timedelta
                    try:
                        dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                        if dt.replace(tzinfo=None) < datetime.now() - timedelta(days=INCREMENTAL_DAYS):
                            stale_codes.append(code)
                    except Exception:
                        stale_codes.append(code)
                else:
                    stale_codes.append(code)

        codes_to_process = new_codes + stale_codes
        skipped = len(all_codes) - len(codes_to_process)
        print(f"  New: {len(new_codes)}, Stale: {len(stale_codes)}, Skipped: {skipped}")

    print(f"\nFetching financial indicators for {len(codes_to_process)} stocks...")
    batch = []

    for i, code in enumerate(codes_to_process):
        if i > 0 and i % BATCH_SIZE == 0:
            print(f"  Progress: {i}/{len(codes_to_process)}")
            upsert_batch(batch)
            batch = []
            time.sleep(DELAY_BETWEEN_BATCHES)

        fin = fetch_financial_abstract(code)
        if fin:
            compute_composite(fin)
            batch.append(fin)

        time.sleep(DELAY_BETWEEN_STOCKS)

    if batch:
        upsert_batch(batch)

    print(f"=== Sync complete. Processed {len(codes_to_process)} stocks ===")


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
    mode = "full" if "--full" in sys.argv else "incr"
    sync(mode)
