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
MAX_CONSECUTIVE_FAILURES = 50
PAUSE_SECONDS = 60
BATCH_SIZE = 10  # smaller batches = less data loss on crash
DELAY = 0.2

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
    if val is None: return None
    if isinstance(val, float) and pd.isna(val): return None
    try: return float(val)
    except: return None

def fetch_stock_list():
    print("Fetching stock list from Supabase...", flush=True)
    codes = []
    offset = 0
    while True:
        result = supabase.table("companies").select("code").range(offset, offset+999).execute()
        if not result.data: break
        codes.extend(r["code"] for r in result.data)
        offset += 1000
        if len(result.data) < 1000: break
    print(f"Got {len(codes)} stocks", flush=True)
    return codes

def fetch_annual_financials(code):
    """Fetch ALL yearly (1231) financial data for a stock."""
    def _do():
        for attempt in range(3):
            try:
                df = ak.stock_financial_abstract(symbol=code)
                if df.empty: return None
                date_cols = [c for c in df.columns if str(c).isdigit() and c.endswith("1231")]
                if not date_cols: return None

                common = df[df["选项"] == "常用指标"].set_index("指标")
                growth = df[df["选项"] == "成长能力"].set_index("指标")
                risk = df[df["选项"] == "财务风险"].set_index("指标")

                results = []
                for dc in date_cols:
                    row = {
                        "code": code,
                        "report_date": f"{dc[:4]}-{dc[4:6]}-{dc[6:]}",
                        "roe": get_val(common[dc], "净资产收益率(ROE)"),
                        "roa": get_val(common[dc], "总资产报酬率(ROA)"),
                        "gross_margin": get_val(common[dc], "毛利率"),
                        "net_margin": get_val(common[dc], "销售净利率"),
                        "debt_to_assets": get_val(common[dc], "资产负债率"),
                        "net_profit": get_val(common[dc], "净利润"),
                        "total_revenue": get_val(common[dc], "营业总收入"),
                        "net_assets": get_val(common[dc], "每股净资产"),
                        "free_cash_flow": get_val(common[dc], "每股现金流"),
                    }
                    if dc in growth.columns:
                        row["revenue_growth"] = get_val(growth[dc], "营业总收入增长率")
                        row["net_profit_growth"] = get_val(growth[dc], "归属母公司净利润增长率")
                    if dc in risk.columns:
                        row["current_ratio"] = get_val(risk[dc], "流动比率")
                    if row["total_revenue"] and row["gross_margin"]:
                        row["gross_profit"] = round(row["total_revenue"] * row["gross_margin"] / 100, 2)
                    results.append(row)
                return results
            except Exception:
                if attempt < 2:
                    time.sleep(2)
                else:
                    return None

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_do)
        try:
            return future.result(timeout=STOCK_TIMEOUT)
        except FuturesTimeout:
            return None

def sync_annual():
    print(f"[{pd.Timestamp.now()}] === 10-Year Annual Sync ===", flush=True)

    codes = fetch_stock_list()

    # Incremental filter
    print("Checking existing...", flush=True)
    try:
        existing_codes = set()
        offset = 0
        while True:
            r = supabase.table("annual_financials").select("code").range(offset, offset+999).execute()
            if not r.data: break
            existing_codes.update(row["code"] for row in r.data)
            offset += 1000
            if len(r.data) < 1000: break
        new_codes = [c for c in codes if c not in existing_codes]
        print(f"  {len(new_codes)} new, {len(codes)-len(new_codes)} done", flush=True)
        codes = new_codes if new_codes else codes
    except Exception as e:
        print(f"  Check failed: {e}", flush=True)

    print(f"  Processing {len(codes)} stocks", flush=True)
    start_idx = load_progress()
    if start_idx > 0: print(f"Resume from {start_idx}", flush=True)

    total_rows = 0
    batch = []
    errors = 0
    cf = 0  # consecutive failures

    i = start_idx
    while i < len(codes):
        code = codes[i]
        i += 1

        # Upsert when batch is full OR after every 5 stocks (keep batch small)
        if len(batch) >= BATCH_SIZE:
            _upsert(batch)
            total_rows += len(batch)
            batch = []
            save_progress(i)
            print(f"  [{i}/{len(codes)}] {total_rows} rows, {errors} err", flush=True)
            time.sleep(2)

        annuals = fetch_annual_financials(code)
        if annuals is None:
            errors += 1
            cf += 1
            if cf >= MAX_CONSECUTIVE_FAILURES:
                print(f"  PAUSE: {cf} consecutive fails", flush=True)
                time.sleep(PAUSE_SECONDS)
                cf = 0
            time.sleep(0.3)
            continue
        else:
            cf = 0

        if len(annuals) > 10:
            annuals = sorted(annuals[:10], key=lambda r: r["report_date"])
        batch.extend(annuals)
        time.sleep(DELAY)

    if batch:
        _upsert(batch)
        total_rows += len(batch)

    try: os.remove(PROGRESS_FILE)
    except: pass
    print(f"[{pd.Timestamp.now()}] Done. {total_rows} rows, {errors} errors", flush=True)

def _upsert(batch):
    if not batch: return
    clean = [{k:v for k,v in ind.items() if v is not None} for ind in batch]
    for attempt in range(5):
        try:
            supabase.table("annual_financials").upsert(clean, on_conflict="code,report_date").execute()
            return
        except Exception as e:
            print(f"  Upsert retry {attempt+1}/5: {str(e)[:50]}", flush=True)
            time.sleep(5*(attempt+1))

if __name__ == "__main__":
    try:
        sync_annual()
    except Exception as e:
        print(f"FATAL: {e}", flush=True)
        traceback.print_exc()