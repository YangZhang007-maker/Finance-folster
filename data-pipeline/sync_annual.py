"""
10-Year Annual Financial Data Sync for Supabase.
Fetches yearly financial data + PE/PB/市值 for all A-share stocks.
Usage: python sync_annual.py
"""
import os, sys, time, socket
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
import pandas as pd
import akshare as ak
from supabase import create_client, Client
from dotenv import load_dotenv

socket.setdefaulttimeout(30)
STOCK_TIMEOUT = 20

load_dotenv()
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BATCH_SIZE = 50
DELAY = 0.5
MAX_STOCKS = 99999


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
    """Get all stocks + PE/PB/市值 in one batch from Sina."""
    print("Fetching stock list + PE/PB/market cap...")
    df = ak.stock_zh_a_spot()
    df = df.rename(columns={
        "代码": "code", "名称": "name",
        "最新价": "price", "成交量": "volume", "成交额": "amount",
    })
    df["code"] = df["code"].astype(str)
    df = df[df["code"].str.match(r"^(60|00|30|68)\d{4}$")]
    return df


def fetch_annual_financials(code):
    """Fetch ALL yearly (1231) financial data for a stock, tagged with year."""
    def _do():
        for attempt in range(2):
            try:
                df = ak.stock_financial_abstract(symbol=code)
                if df.empty:
                    return None

                # Only annual reports (xxxx1231)
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
                    # revenue_growth / net_profit_growth from growth sheet
                    row["revenue_growth"] = get_val(growth[date_col], "营业总收入增长率") if date_col in growth.columns else None
                    row["net_profit_growth"] = get_val(growth[date_col], "归属母公司净利润增长率") if date_col in growth.columns else None
                    # current_ratio from risk sheet
                    row["current_ratio"] = get_val(risk[date_col], "流动比率") if date_col in risk.columns else None
                    # gross_profit = total_revenue * gross_margin / 100
                    if row["total_revenue"] and row["gross_margin"]:
                        row["gross_profit"] = round(row["total_revenue"] * row["gross_margin"] / 100, 2)

                    results.append(row)
                return results
            except Exception as e:
                if attempt < 1:
                    time.sleep(3)
                else:
                    print(f"  Error {code}: {e}")
                    return None

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_do)
        try:
            return future.result(timeout=STOCK_TIMEOUT)
        except FuturesTimeout:
            print(f"  Timeout {code}")
            return None


def add_valuation_data(annual_rows, spot_row):
    """Add PE/PB/market cap from spot data to each annual row."""
    # PE/PB from spot data only applies to most recent year;
    # for historical years these remain NULL
    # But we can add market cap estimate for recent year
    pass  # We'll handle this differently


def sync_annual():
    print("=== Starting 10-Year Annual Financial Data Sync ===")

    # Step 1: Get stock list with PE/PB
    spot_df = fetch_stock_list()
    print(f"Got {len(spot_df)} stocks")

    # Build PE/PB/market cap lookup from spot data
    # spot_df has NO PE/PB columns from Sina (non-trading hours) - skip for now
    pe_map = {}
    pb_map = {}

    # Upsert companies
    print("Upserting companies...")
    batch = []
    for _, row in spot_df.iterrows():
        batch.append({"code": row["code"], "name": str(row.get("name", ""))[:100]})
        if len(batch) >= 100:
            try:
                supabase.table("companies").upsert(batch, on_conflict="code").execute()
            except:
                pass
            batch = []
    if batch:
        supabase.table("companies").upsert(batch, on_conflict="code").execute()

    # Step 2: Process stocks for annual financial data
    codes = spot_df["code"].tolist()
    print(f"\nFetching 10-year annual financials for {len(codes)} stocks...")

    total_rows = 0
    annual_batch = []

    for i, code in enumerate(codes):
        if i > 0 and i % BATCH_SIZE == 0:
            print(f"  Progress: {i}/{len(codes)} ({total_rows} annual rows)")
            if annual_batch:
                _upsert_annual(annual_batch)
                annual_batch = []
            time.sleep(3)

        annuals = fetch_annual_financials(code)
        if annuals:
            # Filter to last 10 years only
            ten_years_ago = f"{pd.Timestamp.now().year - 10}1231"
            filtered = [r for r in annuals if r.get("report_date", "0000") >= f"{pd.Timestamp.now().year - 10}-12-31"]
            # Also keep the actual last 10 entries as a fallback
            if len(filtered) < 10:
                filtered = annuals[-10:] if len(annuals) > 10 else annuals

            # Add any spot PE/PB data (only applies to current year unfortunately)
            annual_batch.extend(filtered)
            total_rows += len(filtered)

        time.sleep(DELAY)

    if annual_batch:
        _upsert_annual(annual_batch)

    print(f"=== Sync complete. Total annual rows: {total_rows} ===")


def _upsert_annual(batch):
    if not batch:
        return
    clean = [{k: v for k, v in ind.items() if v is not None} for ind in batch]
    try:
        supabase.table("annual_financials").upsert(
            clean, on_conflict="code,report_date"
        ).execute()
        print(f"  Upserted {len(clean)} annual rows")
    except Exception as e:
        print(f"  Upsert error: {str(e)[:80]}")


if __name__ == "__main__":
    sync_annual()