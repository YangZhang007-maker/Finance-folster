"""
探针 v9：终极方案探索
1. 打印 stock_financial_abstract 全部7个分类的所有行，找缺失字段
2. 尝试 datacenter API 的其他 reportName
3. 确认最终可行的 22 字段方案
"""
import akshare as ak
import pandas as pd
import requests
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 200)
pd.set_option('display.width', 300)
pd.set_option('display.max_colwidth', 40)

def main():
    # ============ 1. stock_financial_abstract 全量探索 ============
    print("="*100)
    print("📊 Part 1: stock_financial_abstract 所有分类的所有指标")
    try:
        df = ak.stock_financial_abstract(symbol="600519")
        date_cols = [c for c in df.columns if str(c).isdigit() and c.endswith("1231")]
        latest = date_cols[0] if date_cols else None
        print(f"   日期列: {date_cols}")
        print(f"   最新年报: {latest}")

        for option in df["选项"].unique():
            subset = df[df["选项"] == option]
            print(f"\n   --- {option} ({len(subset)}行) ---")
            for _, row in subset.iterrows():
                indicator = row["指标"]
                val = row[latest] if latest else "N/A"
                print(f"      {indicator}: {val}")

    except Exception as e:
        print(f"   ❌ {e}")
        import traceback
        traceback.print_exc()

    # ============ 2. 用比亚迪确认研发费用字段 ============
    print(f"\n{'='*100}")
    print("📊 Part 2: 比亚迪 stock_financial_abstract")
    try:
        df2 = ak.stock_financial_abstract(symbol="002594")
        date_cols = [c for c in df2.columns if str(c).isdigit() and c.endswith("1231")]
        latest = date_cols[0]
        for option in df2["选项"].unique():
            subset = df2[df2["选项"] == option]
            # 找研发相关的行
            rd = subset[subset["指标"].str.contains('研发', na=False)]
            if not rd.empty:
                print(f"\n   [{option}] 研发相关:")
                for _, row in rd.iterrows():
                    print(f"      {row['指标']}: {row[latest]}")
    except Exception as e:
        print(f"   ❌ {e}")

    # ============ 3. 尝试一些新的 reportName ============
    print(f"\n{'='*100}")
    print("📊 Part 3: 尝试不同的 reportName codes")
    url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"

    candidates = [
        "RPT_DMSK_FN_INCOME_STATEMENT",
        "RPT_F10_FINANCE_INCOME",
        "RPT_DMSK_FN_BALANCEFULL",
        "RPT_DMSK_FN_BS",
        "RPT_DMSK_FN_IS",
        "RPT_DMSK_FN_CF",
    ]

    for rn in candidates:
        params = {
            "reportName": rn,
            "columns": "ALL",
            "filter": '(SECURITY_CODE="600519")',
            "pageNumber": 1, "pageSize": 1,
            "sortColumns": "REPORT_DATE", "sortTypes": -1,
            "source": "WEB", "client": "WEB",
        }
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=10)
            d = r.json()
            if d.get("success"):
                recs = d["result"]["data"]
                if recs:
                    print(f"  ✅ {rn}: {len(recs[0])}字段")
            else:
                print(f"  ❌ {rn}: {d.get('message','?')}")
        except Exception as e:
            print(f"  ❌ {rn}: {e}")
        time.sleep(0.3)

    # ============ 4. 试试东方财富新版F10 API ============
    print(f"\n{'='*100}")
    print("📊 Part 4: 新版东方财富F10财务数据API")
    # 新版F10页面: https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html
    # 对应的API可能是不同的路径

    f10_urls = [
        "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/zcfzbAjax",
        "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/lrbAjax",
        "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/xjllbAjax",
        # 新版本可能的路径
        "https://emweb.securities.eastmoney.com/pc_hsf10/api/zcfzb",
        "https://emweb.securities.eastmoney.com/pc_hsf10/api/lrb",
        "https://emweb.securities.eastmoney.com/pc_hsf10/api/xjllb",
    ]
    for url in f10_urls:
        try:
            params = {"code": "SH600519", "companyType": "4", "reportDateType": "1"}
            r = requests.get(url, params=params, headers=HEADERS, timeout=10)
            ct = r.headers.get("content-type", "")
            print(f"  {url}: HTTP {r.status_code}, content-type={ct}, len={len(r.text)}")
            if "json" in ct:
                print(f"    JSON: {r.text[:300]}")
        except Exception as e:
            print(f"  {url}: ❌ {e}")
        time.sleep(0.3)

    print(f"\n{'='*100}")
    print("✅ 探针 v9 完成")


if __name__ == "__main__":
    main()