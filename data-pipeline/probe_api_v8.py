"""
探针 v8：获取 company_type 然后调详细报表 API
AKShare 源码中的 _stock_balance_sheet_by_report_ctype_em 函数：
1. 访问 https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=SH600519
2. 从HTML中提取 id="hidctype" 的 value
3. 然后用这个值调 zcfzbAjaxNew / lrbAjaxNew / xjllbAjaxNew
"""
import requests
import re
import json
import time
from bs4 import BeautifulSoup
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://emweb.securities.eastmoney.com/",
}

def get_company_type(symbol):
    """从东方财富F10页面获取 company_type"""
    # symbol 格式: SH600519 或 600519
    if not symbol.startswith(("SH", "SZ")):
        if symbol.startswith("6") or symbol.startswith("9"):
            symbol = f"SH{symbol}"
        else:
            symbol = f"SZ{symbol}"

    url = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index"
    params = {"type": "web", "code": symbol}

    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")
            ctype_elem = soup.find(attrs={"id": "hidctype"})
            if ctype_elem and ctype_elem.get("value"):
                ct = ctype_elem["value"]
                print(f"   ✅ company_type = {ct}")
                return ct
            else:
                # Try finding by other means
                print(f"   ⚠️ hidctype not found, trying regex...")
                match = re.search(r'hidctype["\']?\s*value=["\'](\d+)["\']', resp.text)
                if match:
                    ct = match.group(1)
                    print(f"   ✅ company_type(regex) = {ct}")
                    return ct
                # Default
                print(f"   ⚠️ 使用默认值 4")
                return "4"
        except Exception as e:
            print(f"   ❌ attempt {attempt+1}: {e}")
            if attempt < 2:
                time.sleep(2)
    return "4"  # 默认

def fetch_detail_report(company_type, report_type, symbol):
    """
    report_type: "zcfzb" (资产负债表), "lrb" (利润表), "xjllb" (现金流量表)
    """
    if not symbol.startswith(("SH", "SZ")):
        if symbol.startswith("6") or symbol.startswith("9"):
            symbol = f"SH{symbol}"
        else:
            symbol = f"SZ{symbol}"

    url = f"https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/{report_type}AjaxNew"
    params = {
        "companyType": company_type,
        "reportDateType": "1",  # 1=按年度
        "code": symbol,
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        print(f"   HTTP {resp.status_code}, body前200字符: {resp.text[:200]}")
        data = resp.json()
        if "data" in data and data["data"]:
            df = pd.DataFrame(data["data"])
            return df
        else:
            print(f"   响应: {json.dumps(data, ensure_ascii=False)[:300]}")
            return None
    except Exception as e:
        print(f"   ❌ {e}")
        return None

def main():
    # 测试茅台
    print("="*80)
    print("🔍 茅台 600519")
    ct = get_company_type("600519")

    if ct:
        # 资产负债表
        print("\n📊 资产负债表:")
        bs = fetch_detail_report(ct, "zcfzb", "600519")
        if bs is not None:
            print(f"   形状: {bs.shape}, 列: {list(bs.columns)}")
            col0 = bs.columns[0]
            # 打印前20行科目名
            print(f"   前30个科目:")
            for i, name in enumerate(bs[col0][:30]):
                print(f"     {i}: {name}")

        time.sleep(1)

        # 利润表
        print("\n📊 利润表:")
        inc = fetch_detail_report(ct, "lrb", "600519")
        if inc is not None:
            col0 = inc.columns[0]
            print(f"   形状: {inc.shape}")
            for i, name in enumerate(inc[col0][:30]):
                print(f"     {i}: {name}")

        time.sleep(1)

        # 现金流量表
        print("\n📊 现金流量表:")
        cf = fetch_detail_report(ct, "xjllb", "600519")
        if cf is not None:
            col0 = cf.columns[0]
            print(f"   形状: {cf.shape}")
            for i, name in enumerate(cf[col0][:30]):
                print(f"     {i}: {name}")


if __name__ == "__main__":
    main()