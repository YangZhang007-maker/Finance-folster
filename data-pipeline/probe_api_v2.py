"""
探针脚本 v2：确认缺失字段
- 研发费用（利润表）
- 合同负债、在建工程、商誉、长期借款、应付债券、总股本（资产负债表）
- 指定年报 DATE_TYPE_CODE=001
"""
import requests
import json
import time

BASE_URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}

def probe_report(name, report_name, extra_params=None):
    params = {
        "reportName": report_name,
        "columns": "ALL",
        "filter": '(SECURITY_CODE="600519")(REPORT_DATE=\'2025-12-31\')',
        "pageNumber": 1,
        "pageSize": 1,
        "sortColumns": "REPORT_DATE",
        "sortTypes": -1,
        "source": "WEB",
        "client": "WEB",
    }
    if extra_params:
        params.update(extra_params)

    print(f"\n{'='*80}")
    print(f"📊 测试: {name} - 年报(2025-12-31)")

    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            print(f"   ❌ HTTP {resp.status_code}: {resp.text[:300]}")
            return None

        data = resp.json()
        if not data.get("success"):
            print(f"   ❌ API 失败: {data.get('message')}")
            return None

        records = data.get("result", {}).get("data", [])
        if not records:
            print(f"   ❌ 无数据")
            return None

        rec = records[0]
        print(f"\n   📋 年报数据所有字段 ({len(rec)}个):")
        for key, value in sorted(rec.items()):
            print(f"      {key}: {value}")

        return rec

    except Exception as e:
        print(f"   ❌ 异常: {type(e).__name__}: {e}")
        return None

def main():
    print("🔍 探针 v2：查年报缺失字段")

    # 利润表 - 找研发费用
    rec1 = probe_report("利润表(年报)", "RPT_DMSK_FN_INCOME")

    # 资产负债表 - 找合同负债、在建工程、商誉、长期借款、应付债券、总股本
    rec2 = probe_report("资产负债表(年报)", "RPT_DMSK_FN_BALANCE")

    # 尝试用不同code获取资产负债表 - 找个制造业公司（制造业有在建工程、商誉等）
    # 用比亚迪 002594
    print(f"\n\n{'='*80}")
    print(f"📊 测试: 资产负债表(比亚迪002594 年报)")
    params = {
        "reportName": "RPT_DMSK_FN_BALANCE",
        "columns": "ALL",
        "filter": '(SECURITY_CODE="002594")(REPORT_DATE=\'2025-12-31\')',
        "pageNumber": 1,
        "pageSize": 1,
        "sortColumns": "REPORT_DATE",
        "sortTypes": -1,
        "source": "WEB",
        "client": "WEB",
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                records = data.get("result", {}).get("data", [])
                if records:
                    rec = records[0]
                    print(f"\n   📋 比亚迪资产负债表所有字段 ({len(rec)}个):")
                    for key, value in sorted(rec.items()):
                        print(f"      {key}: {value}")
    except Exception as e:
        print(f"   ❌ {e}")

    print(f"\n{'='*80}")
    print("✅ 探针 v2 完成")


if __name__ == "__main__":
    main()