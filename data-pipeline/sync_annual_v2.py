"""
全量同步脚本 v3：一体化获取+写入
- 每只股票: fetch DC → 立即写入 (不积压内存)
- 之后: Sina补缺失字段 (需IP解封)
- 之后: 旧表迁移

用法：
  python sync_annual_v2.py              # 全量(含DC+迁移)
  python sync_annual_v2.py --test N     # 测试
  python sync_annual_v2.py --skip-migrate  # 跳过迁移
  python sync_annual_v2.py --sina       # 仅Sina补字段(需IP解封)
"""
import os, sys, json, time, socket, requests, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
import numpy as np
from supabase import create_client

# ============================================================
# 环境
# ============================================================
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    for _line in open(_env_path):
        _line = _line.strip()
        if _line and "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k, _v)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), ".progress_v2.json")
FAILED_FILE = os.path.join(os.path.dirname(__file__), ".failed_v2.json")

DC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}
SINA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://finance.sina.com.cn/",
}
DC_URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
SINA_URL = "https://quotes.sina.cn/cn/api/openapi.php/CompanyFinanceService.getFinanceReport2022"

MAX_WORKERS = 3
STOCK_TIMEOUT = 30
BATCH_SIZE = 200
SINA_DELAY = 10.0

# ============================================================
# Field maps
# ============================================================
DC_FIELD_MAP = {
    "operating_revenue": ("RPT_DMSK_FN_INCOME", "TOTAL_OPERATE_INCOME"),
    "operating_cost": ("RPT_DMSK_FN_INCOME", "TOTAL_OPERATE_COST"),
    "selling_expense": ("RPT_DMSK_FN_INCOME", "SALE_EXPENSE"),
    "admin_expense": ("RPT_DMSK_FN_INCOME", "MANAGE_EXPENSE"),
    "finance_expense": ("RPT_DMSK_FN_INCOME", "FINANCE_EXPENSE"),
    "operating_profit": ("RPT_DMSK_FN_INCOME", "OPERATE_PROFIT"),
    "total_profit": ("RPT_DMSK_FN_INCOME", "TOTAL_PROFIT"),
    "parent_net_profit": ("RPT_DMSK_FN_INCOME", "PARENT_NETPROFIT"),
    "deducted_net_profit": ("RPT_DMSK_FN_INCOME", "DEDUCT_PARENT_NETPROFIT"),
    "inventory": ("RPT_DMSK_FN_BALANCE", "INVENTORY"),
    "fixed_asset": ("RPT_DMSK_FN_BALANCE", "FIXED_ASSET"),
    "cash_and_equivalents": ("RPT_DMSK_FN_BALANCE", "MONETARYFUNDS"),
    "advance_receipts_dc": ("RPT_DMSK_FN_BALANCE", "ADVANCE_RECEIVABLES"),
    "operating_cash_flow": ("RPT_DMSK_FN_CASHFLOW", "NETCASH_OPERATE"),
    "capex": ("RPT_DMSK_FN_CASHFLOW", "CONSTRUCT_LONG_ASSET"),
}

SINA_BS_FIELDS = {
    "construction_in_progress": "在建工程",
    "goodwill": "商誉",
    "short_term_loan": "短期借款",
    "long_term_loan": "长期借款",
    "bonds_payable": "应付债券",
    "contract_liabilities": "合同负债",
    "advance_receipts_sina": "预收款项",
    "total_shares": "实收资本(或股本)",
    "total_assets": "资产总计",
    "total_liabilities": "负债合计",
    "parent_equity": "归属于母公司股东权益合计",
}

SINA_INCOME_FIELDS = {
    "rd_expense": "研发费用",
}

# ============================================================
# Helpers
# ============================================================
def to_sina_code(code):
    return f"sh{code}" if code.startswith(("6", "9")) else f"sz{code}"

def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def clean_row(row):
    for k, v in list(row.items()):
        if v is not None and isinstance(v, float) and (np.isnan(v) or np.isinf(v)):
            row[k] = None
    return row

def upsert(supabase, rows):
    if not rows: return True
    for attempt in range(5):
        try:
            supabase.table("annual_financials_v2").upsert(rows, on_conflict="code,year").execute()
            return True
        except Exception:
            time.sleep(15 * (2 ** attempt))
    return False

# ============================================================
# DataCenter
# ============================================================
def fetch_dc_report(report_name, code):
    params = {
        "reportName": report_name, "columns": "ALL",
        "filter": f'(SECURITY_CODE="{code}")(DATE_TYPE_CODE="001")',
        "pageNumber": 1, "pageSize": 15,
        "sortColumns": "REPORT_DATE", "sortTypes": -1,
        "source": "WEB", "client": "WEB",
    }
    for attempt in range(3):
        try:
            r = requests.get(DC_URL, params=params, headers=DC_HEADERS, timeout=15)
            d = r.json()
            if d.get("success") and d["result"]["data"]:
                recs = d["result"]["data"]
                annuals = [r for r in recs if "12-31" in (r.get("REPORT_DATE") or "")]
                annuals.sort(key=lambda x: x["REPORT_DATE"])
                return {int(r["REPORT_DATE"][:4]): r for r in annuals[-10:]}
            if attempt < 2:
                time.sleep(2)
        except Exception:
            if attempt < 2:
                time.sleep(2)
    return {}

def fetch_dc_all(code):
    results = {}
    for rn in ["RPT_DMSK_FN_INCOME", "RPT_DMSK_FN_BALANCE", "RPT_DMSK_FN_CASHFLOW"]:
        results[rn] = fetch_dc_report(rn, code)
        time.sleep(0.05)
    return results

def dc_to_rows(dc_data, code, name):
    all_years = set()
    for d in dc_data.values():
        all_years.update(d.keys())
    if not all_years:
        return []

    rows = []
    for year in sorted(all_years):
        row = {"code": code, "stock_name": name, "year": year, "data_source": "datacenter"}
        for field_name, (report_name, dc_col) in DC_FIELD_MAP.items():
            rec = dc_data.get(report_name, {}).get(year, {})
            val = rec.get(dc_col)
            if val is not None:
                row[field_name] = float(val)
        # 预收款: 直接存入advance_contract_liab
        dc_adv = row.pop("advance_receipts_dc", None)
        if "advance_contract_liab" not in row or row.get("advance_contract_liab") is None:
            row["advance_contract_liab"] = dc_adv
        rows.append(clean_row(row))
    return rows

# ============================================================
# Sina
# ============================================================
def fetch_sina(stock_sina, report_type):
    smap = {"资产负债表": "fzb", "利润表": "lrb"}
    params = {"paperCode": stock_sina, "source": smap[report_type], "type": "0", "page": "1", "num": "1000"}
    for attempt in range(3):
        try:
            r = requests.get(SINA_URL, params=params, headers=SINA_HEADERS, timeout=15)
            if r.status_code == 456:
                return None  # IP banned
            if r.status_code == 200:
                return r.json()["result"]["data"]
            time.sleep(3)
        except Exception:
            time.sleep(3)
    return None

def extract_sina(data, field_map):
    if not data: return {}
    result = {}
    for d in data["report_date"]:
        ds = d["date_value"]
        if not ds.endswith("1231"): continue
        year = int(ds[:4])
        yd = {}
        for item in data["report_list"].get(ds, {}).get("data", []):
            for our, sina in field_map.items():
                if item.get("item_title") == sina:
                    try:
                        v = item.get("item_value")
                        if v is not None and v != "":
                            yd[our] = float(v)
                    except:
                        pass
        if yd:
            result[year] = yd
    return result

# ============================================================
# 旧表迁移
# ============================================================
def migrate(supabase):
    print("\n📦 迁移旧表...")
    offset, migrated, total = 0, 0, 0
    batch = []
    while True:
        try:
            r = supabase.table("annual_financials").select(
                "code,report_date,total_revenue,gross_profit,gross_margin,net_margin,roe,roa,net_profit,revenue_growth,net_profit_growth,market_cap"
            ).range(offset, offset + 999).execute()
            if not r.data: break
            for row in r.data:
                rd = row.get("report_date", "")
                if not rd or "-" not in rd: continue
                year = int(rd[:4])
                nr = {
                    "code": row["code"], "year": year,
                    "total_revenue": row.get("total_revenue"),
                    "gross_profit": row.get("gross_profit"),
                    "gross_margin": row.get("gross_margin"),
                    "net_margin": row.get("net_margin"),
                    "roe": row.get("roe"), "roa": row.get("roa"),
                    "total_market_cap": row.get("market_cap"),
                    "revenue_yoy": row.get("revenue_growth"),
                    "net_profit_yoy": row.get("net_profit_growth"),
                    "data_source": "migrated_v1",
                }
                batch.append(clean_row(nr))
                if len(batch) >= 200:
                    if upsert(supabase, batch):
                        migrated += len(batch)
                    batch = []
            total += len(r.data)
            print(f"  已读 {total}, 已迁移 {migrated}...")
            if len(r.data) < 1000: break
            offset += 1000
        except Exception as e:
            print(f"  ❌ {e}"); break
    if batch and upsert(supabase, batch):
        migrated += len(batch)
    print(f"  ✅ 迁移: {migrated} 条")
    return migrated

# ============================================================
# 进度
# ============================================================
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        return json.load(open(PROGRESS_FILE))
    return {"completed": [], "total": 0}

def save_progress(p):
    json.dump(p, open(PROGRESS_FILE, 'w'), ensure_ascii=False)

def load_failed():
    return json.load(open(FAILED_FILE)) if os.path.exists(FAILED_FILE) else []

def save_failed(f):
    json.dump(f, open(FAILED_FILE, 'w'), ensure_ascii=False)

# ============================================================
# Main
# ============================================================
def get_stocks(supabase):
    stocks = []
    offset = 0
    while True:
        try:
            r = supabase.table("companies").select("code,name").range(offset, offset+999).execute()
            if not r.data: break
            stocks.extend(r.data)
            if len(r.data) < 1000: break
            offset += 1000
        except Exception: break
    return stocks

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", type=int, default=0)
    parser.add_argument("--skip-migrate", action="store_true")
    parser.add_argument("--sina", action="store_true", help="仅Sina补字段")
    args = parser.parse_args()

    supabase = get_supabase()
    socket.setdefaulttimeout(30)

    # === Migration ===
    if not args.skip_migrate and not args.sina:
        migrate(supabase)

    # === Stocks ===
    print("\n📋 获取股票列表...")
    all_stocks = get_stocks(supabase)
    print(f"  共 {len(all_stocks)} 只")
    if args.test:
        all_stocks = all_stocks[:args.test]
        print(f"  🧪 测试: {args.test} 只")

    progress = load_progress()
    completed = set(progress.get("completed", []))
    todo = [s for s in all_stocks if s["code"] not in completed]
    print(f"  待处理: {len(todo)}, 已完成: {len(completed)}")

    if not todo and not args.sina:
        print("✅ 全部完成!"); return

    total = len(todo)
    start = time.time()
    failed = []
    success = 0
    batch = []

    # ============================================================
    # Phase 1: DC (fetch + write immediately)
    # ============================================================
    if not args.sina:
        print(f"\n🚀 DC同步 (workers={MAX_WORKERS}, batch={BATCH_SIZE})...")
        # Process in chunks
        CHUNK = 300
        for cs in range(0, total, CHUNK):
            chunk = todo[cs:cs + CHUNK]
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
                futures = {ex.submit(fetch_dc_all, s["code"]): s for s in chunk}
                for future in as_completed(futures):
                    stock = futures[future]
                    code, name = stock["code"], stock.get("name", "")
                    try:
                        dc_data = future.result(timeout=STOCK_TIMEOUT)
                    except:
                        dc_data = {}

                    rows = dc_to_rows(dc_data, code, name)
                    if rows:
                        batch.extend(rows)
                        completed.add(code)
                        success += 1
                    else:
                        failed.append(code)

                    # Flush batch
                    if len(batch) >= BATCH_SIZE:
                        upsert(supabase, batch)
                        batch = []

                    if (success + len(failed)) <= 10 or (success + len(failed)) % 200 == 0:
                        elapsed = time.time() - start
                        n = success + len(failed)
                        spd = n / (elapsed / 3600) if elapsed > 0 else 0
                        print(f"  [{n}/{total}] {n/total*100:.1f}% | {spd:.0f}/h | {code} {name}")

            # Flush remaining
            if batch:
                upsert(supabase, batch)
                batch = []

            # Save progress
            save_progress({"completed": list(completed), "total": success + len(failed)})
            save_failed(failed)

        elapsed = time.time() - start
        print(f"\n  DC完成: {success}/{total} ({elapsed/60:.1f}min)")

    # ============================================================
    # Phase 2: Sina (补缺失字段)
    # ============================================================
    if args.sina:
        print(f"\n🚀 Sina补字段 (延迟{SINA_DELAY}s)...")

        # 快速检查哪些股票缺少Sina数据（以total_assets为标记，上次跑过total_shares但没跑新字段）
        print("  检查已有Sina数据的股票...")
        has_sina = set()
        offset = 0
        while True:
            r = supabase.table("annual_financials_v2").select("code").not_.is_("total_assets","null").range(offset, offset+999).execute()
            if not r.data: break
            for row in r.data:
                has_sina.add(row["code"])
            if len(r.data) < 1000: break
            offset += 1000
        print(f"  已有Sina数据: {len(has_sina)} 只")

        todo = [s for s in all_stocks if s["code"] not in has_sina]
        print(f"  待处理: {len(todo)} 只")
        if not todo:
            print("  🎉 全部完成! Sina数据已100%覆盖"); return

        ss, sf = 0, 0
        for i, stock in enumerate(todo):
            code, name = stock["code"], stock.get("name", "")
            sc = to_sina_code(code)

            # Check IP ban
            bs_data = fetch_sina(sc, "资产负债表")
            if bs_data is None:
                print(f"  ⛔ IP被封! 退出Sina阶段 (已处理 {i}/{len(todo)})")
                save_failed([s["code"] for s in todo[i:]])
                break

            inc_data = fetch_sina(sc, "利润表")
            if inc_data is None:
                save_failed([s["code"] for s in todo[i:]])
                break

            bs_years = extract_sina(bs_data, SINA_BS_FIELDS)
            inc_years = extract_sina(inc_data, SINA_INCOME_FIELDS)

            # Build update rows
            all_years = set(bs_years.keys()) | set(inc_years.keys())
            updates = []
            for year in all_years:
                row = {"code": code, "year": year}
                if year in bs_years:
                    for our in SINA_BS_FIELDS:
                        if our in bs_years[year]:
                            val = bs_years[year][our]
                            if our == "contract_liabilities" and year >= 2017:
                                row["advance_contract_liab"] = val
                            elif our == "advance_receipts_sina" and year < 2017:
                                row["advance_contract_liab"] = val
                            elif our == "contract_liabilities" or our == "advance_receipts_sina":
                                # 如果合同负债/预收不清空
                                if "advance_contract_liab" not in row:
                                    row["advance_contract_liab"] = val
                            else:
                                row[our] = val
                if year in inc_years:
                    for our in SINA_INCOME_FIELDS:
                        if our in inc_years[year]:
                            row[our] = inc_years[year][our]
                updates.append(clean_row(row))

            if updates:
                if upsert(supabase, updates):
                    ss += 1
                else:
                    sf += 1
            else:
                sf += 1

            if (i+1) % 50 == 0:
                print(f"  [Sina {i+1}/{len(todo)}] ✅{ss} ❌{sf} | {code} {name}")
                save_failed(failed)

            time.sleep(SINA_DELAY)

        print(f"  Sina完成: ✅{ss} ❌{sf}")

    # ============================================================
    # Summary
    # ============================================================
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"📊 {'Sina补字段' if args.sina else 'DC同步'}完成!")
    print(f"   耗时: {elapsed/60:.1f}min")
    if not args.sina:
        print(f"   成功: {success}/{total}")
        if failed:
            print(f"   失败: {len(failed)} -> {FAILED_FILE}")


if __name__ == "__main__":
    main()