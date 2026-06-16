"""
探针 v10：最终尝试各种方式访问F10详细报表
"""
import requests
import time
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)

def try_f10_ajax():
    """用 session 先访问F10主页拿cookie，再调AJAX"""
    # Step 1: 先访问F10主页 (用新版URL)
    print("Step 1: 访问F10主页...")
    f10_url = "https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html"
    try:
        r = session.get(f10_url, timeout=15)
        print(f"  主页: HTTP {r.status_code}, cookies: {dict(session.cookies)}")
    except Exception as e:
        print(f"  主页: ❌ {e}")

    # Step 2: 访问财务分析页(新版可能是SPA)
    print("\nStep 2: 尝试新版F10 API...")

    # 新 F10 可能用不同的 API 端点
    new_api_urls = [
        # 新版可能的API格式
        ("https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/zcfzbAjaxNew",
         {"code": "SH600519", "companyType": "4", "reportDateType": "1"}),
        ("https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/zcfzbAjaxNew",
         {"code": "SH600519", "companyType": "4", "reportDateType": "0"}),
        # 旧版格式(无New后缀)
        ("https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/zcfzbAjax",
         {"code": "SH600519", "companyType": "4", "reportDateType": "1"}),
        # 试试直接用datacenter API的详细报表
    ]

    for url, params in new_api_urls:
        try:
            r = session.get(url, params=params, timeout=10)
            ct = r.headers.get('content-type', '')
            print(f"  {url.split('/')[-1]}: HTTP {r.status_code}, ct={ct[:50]}, len={len(r.text)}")
            if 'json' in ct.lower():
                print(f"    JSON: {r.text[:500]}")
            elif len(r.text) < 200:
                print(f"    Body: {r.text}")
        except Exception as e:
            print(f"  ❌ {e}")
        time.sleep(0.5)


def try_datacenter_variants():
    """尝试 datacenter API 找更详细的报表"""
    print("\n" + "="*80)
    print("尝试 datacenter API 不同参数组合")

    url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"

    # 尝试用 DATE_TYPE_CODE 过滤年报
    # 找有 在建工程 等字段的报表
    report_names = [
        # 可能包含完整资产负债表字段的 reportName
        ("RPT_DMSK_FN_BALANCE", '(SECURITY_CODE="600519")(DATE_TYPE_CODE="001")'),
        ("RPT_DMSK_FN_BALANCE", '(SECURITY_CODE="002594")(DATE_TYPE_CODE="001")'),
        # 试试不同年份(老数据可能有不同字段)
        ("RPT_DMSK_FN_BALANCE", '(SECURITY_CODE="600519")(REPORT_DATE=\'2019-12-31\')'),
        ("RPT_DMSK_FN_BALANCE", '(SECURITY_CODE="000002")(REPORT_DATE=\'2019-12-31\')'),
        # 试试银行的(银行有很多借款字段)
        ("RPT_DMSK_FN_BALANCE", '(SECURITY_CODE="601398")(REPORT_DATE=\'2025-12-31\')'),
    ]

    for rn, flt in report_names:
        params = {
            "reportName": rn, "columns": "ALL", "filter": flt,
            "pageNumber": 1, "pageSize": 1,
            "sortColumns": "REPORT_DATE", "sortTypes": -1,
            "source": "WEB", "client": "WEB",
        }
        try:
            r = session.get(url, params=params, timeout=10)
            d = r.json()
            if d.get("success") and d["result"]["data"]:
                rec = d["result"]["data"][0]
                # 找关键缺失字段
                key_fields = {}
                for k in rec:
                    ku = k.upper()
                    if any(t in ku for t in ['GOODWILL','CONSTRUCT','BOND','LONG_BORROW',
                                              'CONTRACT','BORROW','SHARE_CAP','RD_EXPENSE',
                                              'DEV_EXPENSE','RESEARCH','在建','商誉','借款',
                                              '债券','股本','合同','研发']):
                        key_fields[k] = rec[k]
                print(f"\n  {rn} | {flt[:50]}:")
                if key_fields:
                    for k, v in key_fields.items():
                        print(f"    {k}: {v}")
                else:
                    print(f"    (无匹配字段)")
            else:
                print(f"  ❌ {rn}: {d.get('message', 'no data')}")
        except Exception as e:
            print(f"  ❌ {rn}: {e}")
        time.sleep(0.3)


def try_f10_new_page():
    """尝试新版F10页面结构"""
    print("\n" + "="*80)
    print("尝试新版F10 SPA页面的API")

    # 新版东方财富F10使用SPA，API可能在 /pc_hsf10/api/ 下
    base = "https://emweb.securities.eastmoney.com/pc_hsf10/api"

    endpoints = [
        "/finance/zcfzb",  # 资产负债表
        "/finance/lrb",    # 利润表
        "/finance/xjllb",  # 现金流量表
        "/zcfzb/list",
        "/lrb/list",
        "/xjllb/list",
    ]

    for ep in endpoints:
        url = base + ep
        for code in ["SH600519", "SZ002594"]:
            params = {"code": code, "type": "0", "reportType": "annual"}
            try:
                r = session.get(url, params=params, timeout=10)
                ct = r.headers.get('content-type', '')
                if r.status_code == 200 and len(r.text) > 200:
                    print(f"  {ep}?code={code}: HTTP 200, ct={ct[:40]}, len={len(r.text)}")
                    if 'json' in ct.lower():
                        try:
                            print(f"    JSON keys: {list(r.json().keys())}")
                        except:
                            print(f"    Body[:300]: {r.text[:300]}")
            except Exception as e:
                pass
            time.sleep(0.2)


def try_akshare_workaround():
    """尝试通过修改AKShare源码的方式绕过"""
    print("\n" + "="*80)
    print("检查AKShare stock_balance_sheet_by_yearly_em 代码逻辑")

    import inspect
    import akshare as ak

    # 看看它实际访问的URL
    src = inspect.getsource(ak.stock_balance_sheet_by_yearly_em)
    # 找URL
    urls_in_src = re.findall(r'https?://[^\s"\']+', src)
    print(f"  源码中的URL: {urls_in_src}")

    # 关键：_stock_balance_sheet_by_report_ctype_em
    ctype_src = inspect.getsource(ak.stock_balance_sheet_by_yearly_em.__wrapped__
                                  if hasattr(ak.stock_balance_sheet_by_yearly_em, '__wrapped__')
                                  else ak.stock_balance_sheet_by_yearly_em)

    # 看看它访问F10页面的URL
    ctype_func_src = inspect.getsource(ak.stock_feature.stock_three_report_em._stock_balance_sheet_by_report_ctype_em)
    ctype_urls = re.findall(r'https?://[^\s"\']+', ctype_func_src)
    print(f"  ctype函数中的URL: {ctype_urls}")


if __name__ == "__main__":
    try_f10_ajax()
    try_datacenter_variants()
    try_f10_new_page()
    try_akshare_workaround()
    print("\n✅ 探针 v10 完成")