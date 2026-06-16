"""
计算 annual_financials_v2 的 15 个派生字段
仅处理 2016-2025 年数据，缺失值按 0 处理（除法分母为 0 时结果 NULL）
用法：python calc_derived_fields.py [--test N] [--dry-run]
"""
import os, sys, json, time, argparse
from supabase import create_client

_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    for line in open(_env_path):
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
BATCH_SIZE = 200

def safe_div(a, b):
    """除法：分母为0或NULL时返回NULL"""
    if a is None or b is None or b == 0:
        return None
    return a / b

def calc_row(row):
    """计算单行的所有派生字段"""
    # 源字段，NULL 视为 0（除法类除外）
    parent_np = row.get("parent_net_profit") or 0
    total_assets = row.get("total_assets") or 0
    cash_eq = row.get("cash_and_equivalents") or 0
    goodwill = row.get("goodwill") or 0
    op_cf = row.get("operating_cash_flow") or 0
    capex = row.get("capex") or 0
    fixed_asset = row.get("fixed_asset") or 0
    cip = row.get("construction_in_progress") or 0
    inventory = row.get("inventory") or 0
    op_rev = row.get("operating_revenue") or 0
    total_shares = row.get("total_shares") or 0
    selling = row.get("selling_expense") or 0
    gross_p = row.get("gross_profit") or 0
    admin = row.get("admin_expense") or 0
    rd = row.get("rd_expense") or 0
    finance = row.get("finance_expense") or 0
    advance = row.get("advance_contract_liab") or 0
    total_liab = row.get("total_liabilities") or 0
    parent_eq = row.get("parent_equity") or 0
    short_loan = row.get("short_term_loan") or 0
    long_loan = row.get("long_term_loan") or 0
    bonds = row.get("bonds_payable") or 0

    result = {}

    # 1. 有效资产收益率 = 归母净利润 / (总资产 - 货币资金 - 商誉) * 100
    denom = total_assets - cash_eq - goodwill
    result["effective_asset_return"] = safe_div(parent_np * 100, denom) if parent_np else None

    # 2. 硬朗度利润 = 经营活动现金流净额 - 资本开支
    result["hard_profit"] = op_cf - capex

    # 3. 锚定资产 = 固定资产 + 在建工程 + 存货
    result["anchor_assets"] = fixed_asset + cip + inventory

    # 4. 锚定资产占比 = (固定资产 + 在建工程 + 存货) / 总资产 * 100
    anchor = fixed_asset + cip + inventory
    result["anchor_asset_ratio"] = safe_div(anchor * 100, total_assets)

    # 5. 净利润率 = 归母净利润 / 营业收入 * 100
    result["net_profit_margin"] = safe_div(parent_np * 100, op_rev) if parent_np else None

    # 6. 每股净利润 = 归母净利润 / 总股本
    result["eps_calculated"] = safe_div(parent_np, total_shares) if parent_np else None

    # 7-12. 费用占毛利比
    if gross_p:
        result["selling_to_gross"] = safe_div(selling * 100, gross_p)
        result["admin_to_gross"] = safe_div(admin * 100, gross_p)
        result["selling_admin_to_gross"] = safe_div((selling + admin) * 100, gross_p)
        result["rd_to_gross"] = safe_div(rd * 100, gross_p)
        result["sga_rd_to_gross"] = safe_div((selling + admin + rd) * 100, gross_p)
        result["finance_to_gross"] = safe_div(finance * 100, gross_p)
    else:
        for k in ["selling_to_gross", "admin_to_gross", "selling_admin_to_gross",
                   "rd_to_gross", "sga_rd_to_gross", "finance_to_gross"]:
            result[k] = None

    # 13. 预收款占总营收比 = 预收款/合同负债 / 营业收入 * 100
    result["advance_to_revenue"] = safe_div(advance * 100, op_rev)

    # 14. 剔除预收款后的资产负债率 = (总负债 - 预收款) / (总资产 - 预收款) * 100
    result["debt_ratio_ex_advance"] = safe_div((total_liab - advance) * 100, (total_assets - advance))

    # 15. 剔除预收款后的债务股权比 = (短期借款+长期借款+应付债券-货币资金) / 归母股东权益
    net_debt = short_loan + long_loan + bonds - cash_eq
    result["debt_equity_ex_cash"] = safe_div(net_debt, parent_eq)

    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 获取所有 2016-2025 记录
    print("📋 获取 2016-2025 数据...")
    all_rows = []
    offset = 0
    while True:
        fields = "id,code,year,parent_net_profit,total_assets,cash_and_equivalents,goodwill,operating_cash_flow,capex,fixed_asset,construction_in_progress,inventory,operating_revenue,total_shares,selling_expense,gross_profit,admin_expense,rd_expense,finance_expense,advance_contract_liab,total_liabilities,parent_equity,short_term_loan,long_term_loan,bonds_payable"
        r = supabase.table("annual_financials_v2").select(fields).gte("year", 2016).lte("year", 2025).range(offset, offset + 999).execute()
        if not r.data:
            break
        all_rows.extend(r.data)
        if len(r.data) < 1000:
            break
        offset += 1000
        print(f"  已读 {len(all_rows)} 行...")

    print(f"  共 {len(all_rows)} 行")

    if args.test:
        all_rows = all_rows[:args.test]
        print(f"  🧪 测试模式: {args.test} 行")

    if args.dry_run:
        print("\n🔍 Dry-run 模式，仅打印前5行计算结果...")
        for row in all_rows[:5]:
            result = calc_row(row)
            print(f"\n  {row['code']} {row['year']}:")
            for k, v in result.items():
                print(f"    {k} = {v}")
        return

    # 批量计算和更新
    print(f"\n🚀 计算并更新 (batch={BATCH_SIZE})...")
    batch = []
    success, total = 0, len(all_rows)
    start = time.time()

    for i, row in enumerate(all_rows):
        derived = calc_row(row)
        derived["id"] = row["id"]
        derived["code"] = row["code"]
        derived["year"] = row["year"]
        batch.append(derived)

        if len(batch) >= BATCH_SIZE:
            for attempt in range(5):
                try:
                    supabase.table("annual_financials_v2").upsert(batch, on_conflict="code,year").execute()
                    success += len(batch)
                    break
                except Exception as e:
                    if attempt < 4:
                        time.sleep(15 * (2 ** attempt))
                    else:
                        print(f"  ❌ 写入失败: {e}")
            batch = []

            elapsed = time.time() - start
            spd = success / (elapsed / 3600) if elapsed > 0 else 0
            print(f"  [{success}/{total}] {success/total*100:.1f}% | {spd:.0f}/h")

    # 最后一批
    if batch:
        for attempt in range(5):
            try:
                supabase.table("annual_financials_v2").upsert(batch, on_conflict="code,year").execute()
                success += len(batch)
                break
            except Exception:
                time.sleep(15 * (2 ** attempt))

    elapsed = time.time() - start
    print(f"\n✅ 完成! {success}/{total} 行, 耗时 {elapsed/60:.1f}min")


if __name__ == "__main__":
    main()