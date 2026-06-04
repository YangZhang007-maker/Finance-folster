"""
10-Year Annual Financial Data Sync for Supabase.
Usage: python sync_annual.py
"""
import os, time, socket, traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
import pandas as pd
import akshare as ak
from supabase import create_client, Client
from dotenv import load_dotenv

socket.setdefaulttimeout(15)
STOCK_TIMEOUT = 15
MAX_CONSECUTIVE_FAILURES = 30
PAUSE_SECONDS = 120
BATCH_SIZE = 50
DELAY = 0.3

load_dotenv()
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

PROGRESS_FILE = os.path.join(os.path.dirname(__file__), ".sync_annual_progress")

def save_progress(index):
    with open(PROGRESS_FILE, "w") as f:
        f.write(str(index))

def load_progress():
    try:
        with open(PROGRESS_FILE) as f:
            return int(f.read().strip())
    except:
        return 0

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

def fetch_stock_list():
    """Get ALL stock codes from Supabase with pagination."""
    print("Fetching stock list from Supabase...")
    codes = []
    offset = 0
    while True:
        result = supabase.table("companies").select("code").range(offset, offset + 999).execute()
        if not result.data:
            break
        codes.extend(r["code"] for r in result.data)
        offset += 1000
        if len(result.data) < 1000:
            break
    print(f"Got {len(codes)} stocks from database")
    return codes

def fetch_annual_financials(code):
    """Fetch ALL yearly (1231) financial data for a stock."""
    def _do():
        for attempt in range(2):
            try:
                df = ak.stock_financial_abstract(symbol=code)
                if df.empty:
                    return None
                date_cols = [c for c in df.columns if str(c).isdigit() and c.endswith("1231")]
                if not date_cols:
                    return None

                common = df[df["选项"] == "常用指标"].set_index("指标")
                growth = df[df["选项"] == "成长能力"].set_index("指标")
                risk = df[df["选项"] == "财务风险"].set_index("指标")

                results = []
                for date_col in date_cols:
                    row = {
                        "code": code,
                        "report_date": f"{date_col[:4]}-{date_col[4:6]}-{date_col[6:]}",
                        "roe": get_val(common[date_col], "净资产收益率(ROE)"),
                        "roa": get_val(common[date_col], "总资产报酬率(ROA)"),
                        "gross_margin": get_val(common[date_col], "毛利率"),
                        "net_margin": get_val(common[date_col], "销售净利率"),
                        "debt_to_assets": get_val(common[date_col], "资产负债率"),
                        "net_profit": get_val(common[date_col], "净利润"),
                        "total_revenue": get_val(common[date_col], "营业总收入"),
                        "net_assets": get_val(common[date_col], "每股净资产"),
                        "free_cash_flow": get_val(common[date_col], "每股现金流"),
                    }
                    if date_col in growth.columns:
                        row["revenue_growth"] = get_val(growth[date_col], "营业总收入增长率")
                        row["net_profit_growth"] = get_val(growth[date_col], "归属母公司净利润增长率")
                    if date_col in risk.columns:
                        row["current_ratio"] = get_val(risk[date_col], "流动比率")
                    if row["total_revenue"] and row["gross_margin"]:
                        row["gross_profit"] = round(row["total_revenue"] * row["gross_margin"] / 100, 2)
                    results.append(row)
                return results
            except Exception:
                if attempt < 1:
                    time.sleep(3)
                else:
                    return None

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_do)
        try:
            return future.result(timeout=STOCK_TIMEOUT)
        except FuturesTimeout:
            return None

def sync_annual():
    print(f"[{pd.Timestamp.now()}] === Starting 10-Year Annual Financial Data Sync ===")

    # Step 1: Get existing stock codes from Supabase
    codes = fetch_stock_list()

    # Step 2: Pre-filter stocks that already have annual data (incremental)
    print("Checking existing annual data...")
    try:
        existing = supabase.table("annual_financials").select("code").execute()
        existing_codes = set(r["code"] for r in existing.data)
        new_codes = [c for c in codes if c not in existing_codes]
        print(f"  {len(new_codes)} new, {len(codes) - len(new_codes)} already synced")
        codes = new_codes if new_codes else codes
    except Exception:
        print("  Could not check existing data, syncing all")

    start_idx = load_progress()
    if start_idx > 0:
        print(f"Resuming from {start_idx}/{len(codes)}...")

    total_rows = 0
    annual_batch = []
    errors = 0
    consecutive_failures = 0

    for i in range(start_idx, len(codes)):
        code = codes[i]

        if len(annual_batch) >= BATCH_SIZE:
            _upsert_annual(annual_batch)
            total_rows += len(annual_batch)
            annual_batch = []
            save_progress(i)
            print(f"  Progress: {i}/{len(codes)} ({total_rows} rows, {errors} errors)")
            time.sleep(2)

        try:
            annuals = fetch_annual_financials(code)
        except Exception:
            annuals = None

        if annuals is None:
            consecutive_failures += 1
            errors += 1
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(f"  Pausing: {consecutive_failures} consecutive failures")
                time.sleep(PAUSE_SECONDS)
                if consecutive_failures >= 50:
                    consecutive_failures = 0
            time.sleep(0.5)
            continue
        else:
            consecutive_failures = 0

        if len(annuals) > 10:
            annuals = annuals[-10:]
        annual_batch.extend(annuals)
        time.sleep(DELAY)

    if annual_batch:
        _upsert_annual(annual_batch)
        total_rows += len(annual_batch)

    try:
        os.remove(PROGRESS_FILE)
    except:
        pass

    print(f"[{pd.Timestamp.now()}] === Sync complete. Total rows: {total_rows}, Errors: {errors} ===")

def _upsert_annual(batch):
    if not batch:
        return
    clean = [{k: v for k, v in ind.items() if v is not None} for ind in batch]
    try:
        supabase.table("annual_financials").upsert(
            clean, on_conflict="code,report_date"
        ).execute()
    except Exception as e:
        print(f"  Upsert error: {str(e)[:80]}")

if __name__ == "__main__":
    try:
        sync_annual()
    except Exception as e:
        print(f"FATAL: {e}")
        traceback.print_exc()
        print(f"[{pd.Timestamp.now()}] Sync terminated with error.")