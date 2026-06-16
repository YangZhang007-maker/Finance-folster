"""
探针 v3：追查缺失字段
1. 研发费用 - 利润表API没有，试试 AKShare 的 stock_financial_abstract
2. 在建工程、商誉、长期借款、应付债券、合同负债、总股本、短期借款
   资产负债表 API (RPT_DMSK_FN_BALANCE) 只返回57个字段(主要指标)
   需要找完整版资产负债表接口
3. 尝试不同 reportName code
"""
import requests
import json
import time

BASE_URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}

def try_report(report_name, stock="600519", desc=""):
    """尝试一个 reportName"""
    params = {
        "reportName": report_name,
        "columns": "ALL",
        "filter": f'(SECURITY_CODE="{stock}")(REPORT_DATE=\'2025-12-31\')',
        "pageNumber": 1,
        "pageSize": 1,
        "sortColumns": "REPORT_DATE",
        "sortTypes": -1,
        "source": "WEB",
        "client": "WEB",
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"  ❌ HTTP {resp.status_code}")
            return None
        data = resp.json()
        if data.get("success") and data.get("result", {}).get("data"):
            rec = data["result"]["data"][0]
            print(f"  ✅ 成功！{len(rec)}个字段")
            if desc:
                # 搜索目标字段
                targets = desc.split(",")
                for t in targets:
                    t = t.strip()
                    found = [k for k in rec if t.upper() in k.upper()]
                    if found:
                        for f in found:
                            print(f"     ✅ {f}: {rec[f]}")
                    else:
                        print(f"     ❌ 未找到: {t}")
            return rec
        else:
            msg = data.get("message", "no data")
            print(f"  ❌ {msg}")
            return None
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return None

def main():
    # ============ 1. 尝试不同资产负债表 reportName ============
    print("="*80)
    print("🔍 Part 1: 寻找完整版资产负债表")
    balance_codes = [
        "RPT_DMSK_FN_BALANCE",           # 已测试 - 57字段，缺少很多
        "RPT_DMSK_FN_BALANCESHEET",       # 尝试全大写法
        "RPT_DMSK_FN_BALANCESHEET_NEW",   # 新会计准则版?
        "RPT_DMSK_FN_FINAINDICATOR",     # 财务指标
        "RPT_DMSK_FN_BALANCESHEET_ALL",   # 完整版?
        "RPT_DMSK_FN_MAININDICATOR",     # 主要指标
    ]
    for code in balance_codes:
        print(f"\n📊 尝试: {code}")
        try_report(code, desc="在建工程,商誉,长期借款,应付债券,合同负债,短期借款,总股本")
        time.sleep(0.5)

    # ============ 2. 研发费用 - AKShare 探针 ============
    print(f"\n{'='*80}")
    print("🔍 Part 2: 用 AKShare stock_financial_abstract 确认研发费用字段")
    try:
        import akshare as ak
        df = ak.stock_financial_abstract(symbol="600519")
        # 找"研发费用"行
        print(f"   全部指标行: {df['指标'].unique()}")
        print(f"   选项列: {df['选项'].unique()}")
        rnd_rows = df[df['指标'].str.contains('研发', na=False)]
        if not rnd_rows.empty:
            print(f"\n   ✅ 研发相关行:")
            print(rnd_rows[['选项', '指标', df.columns[-1]]].to_string())
        else:
            print(f"   ❌ 没有研发费用行")
    except Exception as e:
        print(f"   ❌ AKShare 错误: {e}")

    # ============ 3. 尝试东方财富的"主要指标"接口找研发费用 ============
    print(f"\n{'='*80}")
    print("🔍 Part 3: 东方财富主要指标接口 (可能含研发费用)")
    try_report("RPT_DMSK_FN_MAININDICATOR", desc="研发费用,DEV_EXPENSE,RD_EXPENSE,RESEARCH")

    # ============ 4. 尝试找完整资产负债表 - 用不同参数 ============
    print(f"\n{'='*80}")
    print("🔍 Part 4: 尝试 DATE_TYPE_CODE=001 (年报) + 更多 columns")
    # RPT_DMSK_FN_BALANCE 但尝试不同 filter
    params = {
        "reportName": "RPT_DMSK_FN_BALANCE",
        "columns": "ALL",
        "filter": '(SECURITY_CODE="002594")',  # 比亚迪 - 制造业公司应该有这些字段
        "pageNumber": 1,
        "pageSize": 5,
        "sortColumns": "REPORT_DATE",
        "sortTypes": -1,
        "source": "WEB",
        "client": "WEB",
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        data = resp.json()
        if data.get("success"):
            recs = data["result"]["data"]
            # 过滤年报
            annuals = [r for r in recs if r.get("REPORT_DATE","").endswith("12-31")]
            if annuals:
                rec = annuals[0]
                print(f"  比亚迪年报，共 {len(rec)} 个字段")
                # 搜索所有可能的字段
                search_terms = ['GOODWILL','CONSTRUCT','BOND','LONG_TERM','SHORT_TERM',
                               'CONTRACT','SHARE_CAPITAL','TOTAL_SHARE','PAID_IN',
                               '在建','商誉','借款','应付债券','合同负债','股本']
                for term in search_terms:
                    found = [k for k in rec if term.upper() in k.upper()]
                    if found:
                        for f in found:
                            print(f"     ✅ {f}: {rec[f]}")
    except Exception as e:
        print(f"   ❌ {e}")

    # ============ 5. 试试通过 AKShare 获取完整资产负债表 ============
    print(f"\n{'='*80}")
    print("🔍 Part 5: AKShare stock_balance_sheet_by_report_em (完整资产负债表)")
    try:
        import akshare as ak
        df = ak.stock_balance_sheet_by_report_em(symbol="600519")
        print(f"   列名 ({len(df.columns)}个): {list(df.columns)}")
        print(f"   行数: {len(df)}")
        if not df.empty:
            # 搜索目标字段
            for term in ['在建工程','商誉','长期借款','应付债券','合同负债','短期借款','总股本','研发费用']:
                matched = df[df['REPORT_DATE'].str.endswith('1231', na=False)]
                # 找列名中包含term的
                cols = [c for c in df.columns if term in c]
                if cols:
                    print(f"   ✅ {term}: 列名={cols}")
                else:
                    # 检查是否在行中(项目列)
                    item_rows = df[df.iloc[:, 0].str.contains(term, na=False)]
                    if not item_rows.empty:
                        print(f"   ✅ {term}: 在项目列中，共{len(item_rows)}行")
                    else:
                        print(f"   ❌ {term}: 未找到")
    except Exception as e:
        print(f"   ❌ AKShare 错误: {e}")


if __name__ == "__main__":
    main()