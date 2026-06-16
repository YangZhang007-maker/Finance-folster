"""
探针 v5：绕过AKShare，直接调用东方财富三大报表JSON API
AKShare 报表函数失败是因为它去爬HTML页面获取 company_type，
但我们直接调 JSON API 不需要那一步。
"""
import requests
import json
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://emweb.securities.eastmoney.com/",
}

def call_em_api(report_name, stock_code="600519", page_size=15, extra_filter=""):
    """直接调用东方财富securities API"""
    url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
    filter_str = f'(SECURITY_CODE="{stock_code}"){extra_filter}'
    params = {
        "reportName": report_name,
        "columns": "ALL",
        "filter": filter_str,
        "pageNumber": 1,
        "pageSize": page_size,
        "sortColumns": "REPORT_DATE",
        "sortTypes": -1,
        "source": "WEB",
        "client": "WEB",
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
    data = resp.json()
    if data.get("success"):
        return data["result"]["data"]
    return None

def print_mapping(records, field_map, label=""):
    """给定字段映射，打印匹配结果"""
    print(f"\n  📋 {label}:")
    if not records:
        print("     无数据")
        return
    rec = records[0]
    found_any = False
    for target_name, em_field in field_map.items():
        if em_field in rec:
            val = rec.get(em_field)
            print(f"     ✅ {target_name} ({em_field}): {val}")
            found_any = True
        else:
            print(f"     ❌ {target_name} ({em_field}): 字段不存在")
    if not found_any:
        # 打印所有字段帮助发现
        print(f"     所有字段: {list(rec.keys())}")

def main():
    stock = "600519"  # 茅台

    # ==========================================
    # Part 1: 利润表 - 已经是完整的！
    # ==========================================
    print("="*80)
    print("📊 Part 1: 利润表 (RPT_DMSK_FN_INCOME)")
    income = call_em_api("RPT_DMSK_FN_INCOME", stock)
    income_field_map = {
        "营业收入": "TOTAL_OPERATE_INCOME",
        "营业成本": "TOTAL_OPERATE_COST",
        "营业税金及附加": "OPERATE_TAX_ADD",
        "销售费用": "SALE_EXPENSE",
        "管理费用": "MANAGE_EXPENSE",
        "研发费用": "OPERATE_EXPENSE",  # 待验证 - 茅台用 OPERATE_EXPENSE
        "财务费用": "FINANCE_EXPENSE",
        "营业利润": "OPERATE_PROFIT",
        "利润总额": "TOTAL_PROFIT",
        "归母净利润": "PARENT_NETPROFIT",
        "扣非净利润": "DEDUCT_PARENT_NETPROFIT",
        "所得税": "INCOME_TAX",
    }
    print_mapping(income, income_field_map, "利润表")

    # 注意：研发费用可能是 OPERATE_EXPENSE（已存在），但在制造业公司中
    # 利润表通常有单独的 研发费用 项目
    # 茅台的 OPERATE_EXPENSE 等于是营业成本大类，研发费用在其中
    if income:
        # 看看有没有其他含研发/RD/DEV的字段
        rec = income[0]
        rnd_cols = [k for k in rec if any(t in k.upper() for t in ['RD','DEV','RESEARCH','DEVELOP'])]
        print(f"\n  🔍 含研发相关的列名: {rnd_cols if rnd_cols else '无'}")
        print(f"  💡 茅台各费用字段值:")
        for f in ['SALE_EXPENSE', 'MANAGE_EXPENSE', 'FINANCE_EXPENSE', 'OPERATE_EXPENSE', 'OPERATE_COST']:
            if f in rec:
                print(f"     {f}: {rec[f]}")

    # ==========================================
    # Part 2: 资产负债表 - 缺少很多字段
    # ==========================================
    print(f"\n{'='*80}")
    print("📊 Part 2: 资产负债表 (RPT_DMSK_FN_BALANCE)")
    balance = call_em_api("RPT_DMSK_FN_BALANCE", stock)

    # 已确认的字段
    balance_ok = {
        "存货": "INVENTORY",
        "固定资产": "FIXED_ASSET",
        "预收款/预收款项": "ADVANCE_RECEIVABLES",
        "货币资金/现金等价物": "MONETARYFUNDS",
        "短期借款": "SHORT_LOAN",
    }
    print_mapping(balance, balance_ok, "资产负债表-已确认")

    # 缺失字段（需要找）
    if balance:
        rec = balance[0]
        print(f"\n  🔍 缺失字段搜索:")
        missing = ['GOODWILL','CONSTRUCT','BOND','LONG_TERM','CONTRACT','LIABILITY',
                   'SHARE','CAPITAL','在建','商誉','借款','债券','负债','总股本']
        all_found = set()
        for term in missing:
            for k in rec:
                if term.upper() in k.upper():
                    all_found.add(k)
        for k in sorted(all_found):
            print(f"     {k}: {rec[k]}")

    # ==========================================
    # Part 3: 现金流量表 - 基本完整
    # ==========================================
    print(f"\n{'='*80}")
    print("📊 Part 3: 现金流量表 (RPT_DMSK_FN_CASHFLOW)")
    cashflow = call_em_api("RPT_DMSK_FN_CASHFLOW", stock)
    cf_field_map = {
        "经营活动现金流净额": "NETCASH_OPERATE",
        "购建固定资产支付现金": "CONSTRUCT_LONG_ASSET",
    }
    print_mapping(cashflow, cf_field_map, "现金流量表")

    # ==========================================
    # Part 4: 尝试不同的 reportName 找完整资产负债表
    # ==========================================
    print(f"\n{'='*80}")
    print("📊 Part 4: 尝试找完整版资产负债表API")

    # 东方财富可能有多个报表系统
    # - "RPT_DMSK_FN_BALANCE" 是旧版摘要（57字段）
    # - 新会计准则版可能叫不同的名字

    possible_names = [
        "RPT_DMSK_FN_BALANCE_NEW",
        "RPT_DMSK_FN_BALANCESHEET",
        "RPT_DMSK_FN_BALANCE_ALL",
        "RPT_DMSK_FN_ASSETLIABILITY",
        "RPT_F10_FINANCE_BALANCESHEET",
        "RPT_LICO_FN_CPD",
        "RPT_F10_FN_BALANCE",
    ]
    for rn in possible_names:
        result = call_em_api(rn, stock, page_size=1)
        if result:
            print(f"  ✅ {rn}: {len(result[0])}个字段")
            rec = result[0]
            # 检查缺失字段
            for t in ['GOODWILL','CONSTRUCT','BOND','LONG_BORROW','CONTRACT_LIAB','SHARE']:
                found = [k for k in rec if t.upper() in k.upper()]
                if found:
                    print(f"     {found}: {[rec[k] for k in found]}")
        else:
            print(f"  ❌ {rn}: 不存在")
        time.sleep(0.3)

    # ==========================================
    # Part 5: 用比亚迪(制造业)测试资产负债表缺失字段
    # ==========================================
    print(f"\n{'='*80}")
    print("📊 Part 5: 比亚迪(RPT_DMSK_FN_BALANCE) - 制造业应该有商誉/在建工程")
    byd_balance = call_em_api("RPT_DMSK_FN_BALANCE", "002594")
    if byd_balance:
        rec = byd_balance[0]
        # 找所有包含 ASSET 的字段
        asset_cols = [k for k in rec if 'ASSET' in k.upper() or 'GOODWILL' in k.upper()
                     or 'CONSTRUCT' in k.upper() or 'BORROW' in k.upper()
                     or 'BOND' in k.upper() or 'LOAN' in k.upper()
                     or 'DEBT' in k.upper() or 'CONTRACT' in k.upper()
                     or 'LIABI' in k.upper()]
        for c in sorted(asset_cols):
            print(f"     {c}: {rec[c]}")

    # ==========================================
    # Part 6: 研发费用 - 检查非金融公司的利润表
    # ==========================================
    print(f"\n{'='*80}")
    print("📊 Part 6: 比亚迪利润表 - 查找研发费用字段")
    byd_income = call_em_api("RPT_DMSK_FN_INCOME", "002594")
    if byd_income:
        rec = byd_income[0]
        print(f"   比亚迪利润表所有非None字段:")
        for k, v in sorted(rec.items()):
            if v is not None:
                print(f"     {k}: {v}")

    print(f"\n{'='*80}")
    print("✅ 探针 v5 完成")


if __name__ == "__main__":
    main()