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
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]  # service_role key for writes
BATCH_SIZE = 50
DELAY_BETWEEN_BATCHES = 2  # seconds, to avoid rate limiting

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_all_stocks():
    """Fetch all A-share stock basic info."""
    print("Fetching all A-share stocks...")
    df = ak.stock_zh_a_spot_em()
    df = df.rename(columns={
        "代码": "code",
        "名称": "name",
        "市盈率-动态": "pe_ratio",
        "市净率": "pb_ratio",
        "总市值": "market_cap",
        "60日涨跌幅": "change_60d",
    })
    # Filter out invalid codes
    df = df[df["code"].str.match(r"^(60|00|30|68)\d{4}$")]
    print(f"Got {len(df)} stocks")
    return df


def upsert_companies(df):
    """Upsert companies table."""
    print("Upserting companies...")
    batch = []
    for _, row in df.iterrows():
        code = row["code"]
        name = row.get("name", "")
        batch.append({"code": code, "name": name})
        if len(batch) >= BATCH_SIZE:
            supabase.table("companies").upsert(batch, on_conflict="code").execute()
            batch = []
            time.sleep(0.3)
    if batch:
        supabase.table("companies").upsert(batch, on_conflict="code").execute()
    print("Companies upserted.")


def fetch_financial_indicators(code):
    """Fetch financial analysis indicators for a single stock."""
    try:
        df = ak.stock_financial_analysis_indicator(symbol=code)
        if df.empty:
            return None
        latest = df.iloc[-1]  # most recent period
        return {
            "code": code,
            "report_date": str(latest.get("日期", "")),
            "pe_ratio": parse_float(latest.get("市盈率")),
            "pb_ratio": parse_float(latest.get("市净率")),
            "ps_ratio": parse_float(latest.get("市销率")),
            "roe": parse_float(latest.get("净资产收益率")),
            "roa": parse_float(latest.get("总资产收益率")),
            "gross_margin": parse_float(latest.get("销售毛利率")),
            "net_margin": parse_float(latest.get("销售净利率")),
            "revenue_growth": parse_float(latest.get("营业收入增长率")),
            "net_profit_growth": parse_float(latest.get("净利润增长率")),
            "debt_to_assets": parse_float(latest.get("资产负债率")),
            "current_ratio": parse_float(latest.get("流动比率")),
            "net_assets": parse_float(latest.get("每股净资产")),
            "free_cash_flow": parse_float(latest.get("每股经营现金流")),
        }
    except Exception as e:
        print(f"  Error fetching {code}: {e}")
        return None


def fetch_spot_indicators(code):
    """Fetch real-time market indicators (PE, PB, market cap, etc.)."""
    try:
        df = ak.stock_individual_info_em(symbol=code)
        # Returns a DataFrame with 'item' and 'value' columns
        result = {}
        for _, row in df.iterrows():
            item = str(row["item"])
            value = row["value"]
            if "市盈率" in item:
                result["pe_ratio"] = parse_numeric(value)
            elif "市净率" in item:
                result["pb_ratio"] = parse_numeric(value)
            elif "总市值" in item:
                result["market_cap"] = parse_numeric(value)
            elif "流通市值" in item:
                result["circulating_cap"] = parse_numeric(value)
            elif "营业收入" in item:
                result["total_revenue"] = parse_numeric(value)
            elif "净利润" in item:
                result["net_profit"] = parse_numeric(value)
            elif "总资产" in item:
                result["total_assets"] = parse_numeric(value)
            elif "净资产" in item:
                result["net_assets"] = parse_numeric(value)
        result["code"] = code
        return result
    except Exception as e:
        print(f"  Error spot {code}: {e}")
        return None


def parse_float(val):
    """Safely parse a value to float, handling percentage strings."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, str):
        val = val.replace("%", "").replace(",", "").strip()
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_numeric(val):
    """Parse numeric value that may be a string like '1.23万亿'."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        val = str(val).replace(",", "").strip()
        multiplier = 1
        if "万亿" in val:
            multiplier = 1e12
            val = val.replace("万亿", "")
        elif "亿" in val:
            multiplier = 1e8
            val = val.replace("亿", "")
        elif "万" in val:
            multiplier = 1e4
            val = val.replace("万", "")
        return float(val) * multiplier
    except (ValueError, TypeError):
        return None


def compute_composite(indicators):
    """Compute composite/buffett-style indicators."""
    if not indicators:
        return
    # Buffett Indicator: Market Cap to various fundamentals
    mc = indicators.get("market_cap")
    na = indicators.get("net_assets")
    tr = indicators.get("total_revenue")
    ta = indicators.get("total_assets")

    if mc and na and na > 0:
        indicators["buffett_index"] = round(float(mc) / float(na), 4)

    # PEG: PE / growth rate
    pe = indicators.get("pe_ratio")
    growth = indicators.get("net_profit_growth")
    if pe and growth and growth > 0:
        indicators["peg_ratio"] = round(float(pe) / float(growth), 4)

    return indicators


def sync_all():
    """Main sync function."""
    print("=== Starting A-Share Financial Data Sync ===")

    # Step 1: Fetch and upsert all companies
    stocks = fetch_all_stocks()
    upsert_companies(stocks)

    # Step 2: Get top ~500 stocks by market cap for detailed financials
    top_stocks = stocks.head(500) if len(stocks) > 500 else stocks
    codes = top_stocks["code"].tolist()

    print(f"\nFetching financial indicators for {len(codes)} stocks...")
    indicators_batch = []
    for i, code in enumerate(codes):
        if i > 0 and i % BATCH_SIZE == 0:
            print(f"  Progress: {i}/{len(codes)}")
            # Upsert batch
            if indicators_batch:
                clean_batch = [{k: v for k, v in ind.items() if v is not None}
                               for ind in indicators_batch if ind]
                supabase.table("financial_indicators").upsert(
                    clean_batch, on_conflict="code,report_date"
                ).execute()
            indicators_batch = []
            time.sleep(DELAY_BETWEEN_BATCHES)

        spot = fetch_spot_indicators(code)
        if spot:
            compute_composite(spot)
            indicators_batch.append(spot)

    # Final batch
    if indicators_batch:
        clean_batch = [{k: v for k, v in ind.items() if v is not None}
                       for ind in indicators_batch if ind]
        supabase.table("financial_indicators").upsert(
            clean_batch, on_conflict="code,report_date"
        ).execute()

    print(f"=== Sync complete. Total stocks processed: {len(codes)} ===")


if __name__ == "__main__":
    sync_all()
