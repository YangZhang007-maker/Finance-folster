"""
探针 v11：尝试移动端/新域名API获取完整财务报表
"""
import requests
import time
import re
import akshare as ak
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

def main():
    # ====== 1. 查看 AKShare 是怎么拿到 company_type 的 ======
    print("="*80)
    print("📊 Part 1: 尝试直接用浏览器访问新F10页面")

    # AKShare用的旧URL: emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index
    # 现在可能就是 emweb.securities.eastmoney.com/pc_hsf10/pages/index.html
    # 但返回 SPA，需要看看是不是有对应的 API

    # 注意！AKShare 源码里有个关键的 URL:
    # zcfzbDateAjaxNew - 先获取日期列表
    # zcfzbAjaxNew - 再获取数据

    # 这些URL返回HTML可能说明需要特定的请求头或referer
    import inspect
    src = inspect.getsource(ak.stock_balance_sheet_by_yearly_em)
    # 看看参数格式
    print("AKShare 源码关键行:")
    for line in src.split('\n'):
        if 'url' in line.lower() or 'param' in line.lower() or 'companyType' in line.lower() or 'reportDate' in line.lower() or 'dates' in line.lower():
            print(f"  {line.strip()}")

    # ====== 2. 尝试用 precise referer 访问 ======
    print(f"\n{'='*80}")
    print("📊 Part 2: 带正确Referer重试F10 API")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })

    # 先访问F10主页获取cookies
    print("访问 F10 主页...")
    r = session.get("https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index",
                     params={"type": "web", "code": "SH600519"},
                     timeout=15)
    print(f"  HTTP {r.status_code}, cookies: {dict(session.cookies)}")

    # 从主页提取 hidctype
    import re
    match = re.search(r'hidctype["\']?\s*value=["\'](\d+)["\']', r.text)
    if match:
        ct = match.group(1)
        print(f"  company_type from page: {ct}")

    # 用获取的 cookies 访问 AJAX
    print("\n尝试带 cookies 访问 zcfzbAjaxNew...")
    params = {"companyType": "4", "reportDateType": "1", "code": "SH600519"}
    r = session.get(
        "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/zcfzbAjaxNew",
        params=params,
        headers={"Referer": "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/Index?type=web&code=SH600519"},
        timeout=15
    )
    print(f"  HTTP {r.status_code}, content-type={r.headers.get('content-type','?')[:50]}")
    print(f"  Body[:500]: {r.text[:500]}")

    # ====== 3. 尝试新版URL模式 ======
    print(f"\n{'='*80}")
    print("📊 Part 3: 搜索东方财富新版F10 API")

    # 试着访问实际的F10 SPA应用
    r = session.get("https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html",
                     params={"type": "web", "code": "SH600519"},
                     timeout=15)
    print(f"SPA主页: HTTP {r.status_code}, len={len(r.text)}")

    # 找API端点
    api_patterns = re.findall(r'(?:api|url|src|href)\s*[:=]\s*["\']([^"\']*(?:api|Ajax|ajax)[^"\']*)', r.text)
    print(f"  可能的API端点: {api_patterns}")

    # 找所有URL
    all_urls = re.findall(r'["\']((?:https?:)?//[^"\']+)["\']', r.text)
    api_urls = [u for u in all_urls if 'api' in u.lower() or 'Ajax' in u]
    print(f"  可能的API URL: {api_urls[:10]}")

    # ====== 4. 试试直接查东方财富半年报/年报PDF中的报表数据API ======
    print(f"\n{'='*80}")
    print("📊 Part 4: 尝试 push2his.eastmoney.com (历史行情API)")

    # push2 是东方财富另一个数据系统
    # 试试看有没有财务数据接口
    push_urls = [
        "https://push2his.eastmoney.com/api/qt/stock/kline/get",
        "https://datacenter-web.eastmoney.com/api/data/v1/get",
    ]
    for url in push_urls:
        try:
            r = session.get(url, timeout=10)
            print(f"  {url}: HTTP {r.status_code}")
        except:
            print(f"  {url}: ❌")

    # ====== 5. AKShare Version Check ======
    print(f"\n{'='*80}")
    print("📊 Part 5: AKShare 版本与可用替代函数")
    print(f"  AKShare version: {ak.__version__}")

    # 搜索所有财务相关的函数
    fin_funcs = [f for f in dir(ak) if 'stock' in f.lower() and any(t in f.lower()
                 for t in ['balance','profit','income','cash','finance','report',
                          'sheet','annual','yearly','quarter'])]
    print(f"  财务相关函数 ({len(fin_funcs)}个):")
    for f in sorted(fin_funcs):
        print(f"    - {f}")

    # 特别注意 stock_financial_abstract_ths (同花顺源)
    # 和 stock_financial_abstract 的差异
    print(f"\n  📋 stock_financial_abstract vs stock_financial_abstract_ths:")
    for f in ['stock_financial_abstract', 'stock_financial_abstract_ths',
              'stock_financial_report_sina', 'stock_financial_analysis_indicator']:
        if f in dir(ak):
            print(f"    ✅ {f} 可用")

    # ====== 6. 最终确认: 用datacenter API能拿到的最全字段集 ======
    print(f"\n{'='*80}")
    print("📊 Part 6: datacenter API 全字段审查")

    url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"

    reports = {
        "利润表": ("RPT_DMSK_FN_INCOME", "600519"),
        "资产负债表": ("RPT_DMSK_FN_BALANCE", "600519"),
        "现金流量表": ("RPT_DMSK_FN_CASHFLOW", "600519"),
    }

    for name, (rn, code) in reports.items():
        params = {
            "reportName": rn, "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")(REPORT_DATE=\'2025-12-31\')',
            "pageNumber": 1, "pageSize": 1,
            "sortColumns": "REPORT_DATE", "sortTypes": -1,
            "source": "WEB", "client": "WEB",
        }
        try:
            r = session.get(url, params=params, timeout=15)
            d = r.json()
            if d.get("success") and d["result"]["data"]:
                rec = d["result"]["data"][0]
                # 打印所有有值的字段
                non_null = {k: v for k, v in rec.items() if v is not None}
                print(f"\n  {name} ({len(non_null)}/{len(rec)}个非空字段):")
                # 按字母排序打印
                for k in sorted(non_null.keys()):
                    v = non_null[k]
                    if isinstance(v, float):
                        print(f"    {k}: {v:,.2f}")
                    else:
                        print(f"    {k}: {v}")
        except Exception as e:
            print(f"  {name}: ❌ {e}")
        time.sleep(0.3)

    print(f"\n{'='*80}")
    print("✅ 探针 v11 完成")


if __name__ == "__main__":
    main()