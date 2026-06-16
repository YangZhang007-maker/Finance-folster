"""
探针脚本：测试东方财富三大报表 API 的返回字段
用 600519 茅台测试，打印完整返回结构

用法：python probe_api.py
"""
import requests
import json
import time

BASE_URL = "https://datacenter.eastmoney.com/securities/api/data/v1/get"

# 三大报表的 reportName
REPORTS = {
    "利润表": "RPT_DMSK_FN_INCOME",
    "资产负债表": "RPT_DMSK_FN_BALANCE",
    "现金流量表": "RPT_DMSK_FN_CASHFLOW",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}

def probe_report(name, report_name, stock_code="600519", page_size=12):
    """探测一个报表 API，返回最近 N 年的数据"""
    params = {
        "reportName": report_name,
        "columns": "ALL",
        "filter": f'(SECURITY_CODE="{stock_code}")',
        "pageNumber": 1,
        "pageSize": page_size,
        "sortColumns": "REPORT_DATE",
        "sortTypes": -1,
        "source": "WEB",
        "client": "WEB",
    }

    print(f"\n{'='*80}")
    print(f"📊 测试: {name} ({report_name})")
    print(f"   URL: {BASE_URL}")
    print(f"   Stock: {stock_code}")
    print(f"{'='*80}")

    for attempt in range(3):
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
            print(f"   HTTP Status: {resp.status_code}")

            if resp.status_code != 200:
                print(f"   ❌ 非200响应: {resp.text[:500]}")
                if attempt < 2:
                    print(f"   🔄 重试 {attempt+2}/3...")
                    time.sleep(3)
                    continue
                return None

            data = resp.json()
            if not data.get("success"):
                print(f"   ❌ API 返回失败: {data.get('message', 'unknown')}")
                return None

            result = data.get("result")
            if not result:
                print(f"   ❌ result 为空")
                return None

            total_pages = result.get("pages", 1)
            total_count = result.get("count", 0)
            records = result.get("data", [])

            print(f"   ✅ 成功！总记录数: {total_count}, 本页: {len(records)}, 总页数: {total_pages}")

            if records:
                print(f"\n   📋 第一条记录的所有字段:")
                first = records[0]
                for key, value in first.items():
                    print(f"      {key}: {value}")

                # 打印所有字段名方便后续 mapping
                print(f"\n   📋 全部字段名列表 ({len(first)}个):")
                print(f"      {list(first.keys())}")

                # 打印所有年份数据的关键字段
                print(f"\n   📅 所有记录的关键信息:")
                for rec in records:
                    report_date = rec.get("REPORT_DATE", "?")
                    # 尝试几个可能的金额字段
                    sec_code = rec.get("SECURITY_CODE", "?")
                    sec_name = rec.get("SECURITY_NAME_ABBR", "?")
                    print(f"      {report_date} | {sec_code} | {sec_name}")

            return records

        except requests.exceptions.Timeout:
            print(f"   ⏰ 超时 (attempt {attempt+1}/3)")
            if attempt < 2:
                time.sleep(3)
        except requests.exceptions.ConnectionError as e:
            print(f"   🔌 连接错误: {e}")
            if attempt < 2:
                time.sleep(5)
        except Exception as e:
            print(f"   ❌ 异常: {type(e).__name__}: {e}")
            if attempt < 2:
                time.sleep(3)

    return None


def main():
    results = {}
    for name, report_name in REPORTS.items():
        records = probe_report(name, report_name)
        results[name] = records
        # 请求间隔
        if records is not None:
            print(f"\n   ✅ {name} 探测完成")
        else:
            print(f"\n   ❌ {name} 探测失败")
        time.sleep(1)

    # 汇总
    print(f"\n{'='*80}")
    print(f"📊 汇总:")
    for name, records in results.items():
        status = f"✅ {len(records)}条记录" if records else "❌ 失败"
        print(f"   {name}: {status}")


if __name__ == "__main__":
    main()