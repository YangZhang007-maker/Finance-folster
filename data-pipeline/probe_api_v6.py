"""
探针 v6：最终定案 - 确认所有 22 个字段的完整方案
1. stock_financial_abstract 能覆盖哪些字段
2. 东方财富 REST API 能覆盖哪些
3. 缺失的如何补
"""
import requests
import json
import time
import akshare as ak
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://emweb.securities.eastmoney.com/",
}

def call_em(report_name, stock, extra_filter="", ps=5):
    url = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
    f = f'(SECURITY_CODE="{stock}"){extra_filter}'
    params = {"reportName": report_name, "columns": "ALL", "filter": f,
              "pageNumber": 1, "pageSize": ps, "sortColumns": "REPORT_DATE",
              "sortTypes": -1, "source": "WEB", "client": "WEB"}
    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    d = r.json()
    return d["result"]["data"] if d.get("success") else None

def main():
    # ========== 1. stock_financial_abstract 完整字段清单 ==========
    print("="*80)
    print("📊 Part 1: stock_financial_abstract 能给什么？")
    try:
        df = ak.stock_financial_abstract(symbol="600519")
        common = df[df["选项"] == "常用指标"].set_index("指标")
        # 找最近年报列
        date_cols = [c for c in df.columns if str(c).isdigit() and c.endswith("1231")]
        latest = date_cols[0]

        # 我们需要的22个字段 vs AKShare 能提供的
        targets = {
            "营业收入": "营业总收入",
            "营业成本": "营业成本",
            "销售费用": None,
            "管理费用": None,
            "研发费用": None,
            "财务费用": None,
            "营业利润": None,
            "利润总额": None,
            "归母净利润": "归母净利润",
            "扣非净利润": "扣非净利润",
            "预收款_合同负债": None,
            "存货": None,
            "固定资产": None,
            "在建工程": None,
            "现金及等价物": None,
            "商誉": "商誉",
            "短期借款": None,
            "长期借款": None,
            "应付债券": None,
            "总股本": None,
            "经营现金流净额": "经营现金流量净额",
            "购建固定资产支出": None,
        }
        print(f"   最新年报列: {latest}")
        for cn_name, ak_name in targets.items():
            if ak_name and ak_name in common.index:
                val = common.loc[ak_name, latest]
                print(f"   ✅ {cn_name} (AKShare: {ak_name}): {val}")
            elif ak_name:
                print(f"   ❌ {cn_name}: {ak_name} 不在指标列表中")
            else:
                print(f"   ❓ {cn_name}: 需从REST API获取")

        # 打印所有常用指标的行名，帮助发现更多字段
        print(f"\n   📋 常用指标 全部行名:")
        for idx in common.index:
            print(f"      {idx}")
    except Exception as e:
        print(f"   ❌ {e}")

    # ========== 2. 万科(高负债)资产负债表 - 确认借款字段 ==========
    print(f"\n{'='*80}")
    print("📊 Part 2: 万科 000002 资产负债表(高负债公司，SHORT_LOAN应有值)")
    vanke_bs = call_em("RPT_DMSK_FN_BALANCE", "000002")
    if vanke_bs:
        rec = vanke_bs[0]  # 最新报告期
        loan_cols = [k for k in rec if any(t in k.upper() for t in
                    ['LOAN','BORROW','BOND','DEBT','ADVANCE','CONTRACT',
                     'GOODWILL','CONSTRUCT','SHARE','CAPITAL','TOTAL_EQUITY'])]
        print(f"   万科 {rec.get('REPORT_DATE','?')}")
        for c in sorted(loan_cols):
            print(f"     {c}: {rec[c]}")
        # 再看看 TOTAL_EQUITY
        print(f"\n   ⚠️ 关键: TOTAL_EQUITY={rec.get('TOTAL_EQUITY')} (这其实是股东权益合计，非总股本)")

    # ========== 3. 寻找完整版利润表(含研发费用) ==========
    print(f"\n{'='*80}")
    print("📊 Part 3: 搜索完整利润表 endpoint(含研发费用行)")

    # 东方财富可能有报告期明细版本
    income_detail_names = [
        "RPT_DMSK_FN_INCOME_DETAIL",
        "RPT_DMSK_FN_INCOME_NEW",
        "RPT_DMSK_FN_PROFIT",
        "RPT_F10_FN_INCOME",
        "RPT_DMSK_FN_INCOMESTATEMENT",
    ]
    for rn in income_detail_names:
        result = call_em(rn, "002594", page_size=1)  # 比亚迪
        if result:
            rec = result[0]
            # 找研发费用
            rd_cols = [k for k in rec if any(t in k.upper() for t in
                       ['RD','DEV','RESEARCH','DEVELOP','研发'])]
            print(f"  ✅ {rn}: {len(rec)}字段, 研发相关: {rd_cols if rd_cols else '无'}")
        else:
            print(f"  ❌ {rn}: 不存在")
        time.sleep(0.2)

    # ========== 4. 尝试新会计准则分类的报表 ==========
    print(f"\n{'='*80}")
    print("📊 Part 4: 按证监会分类的报表系统")

    # 东方财富有按报告类型分类的API
    # DATE_TYPE_CODE: 001=年报, 003=季报
    # 试试不同的查询组合
    all_report_codes = [
        "RPT_DMSK_FN_BALANCE",     # 旧版摘要(已确认57字段)
        # 试试金融行业的 - 可能有不同的字段集
    ]

    # 试银行(有大量贷款相关字段)
    print("   测试 工商银行 601398 资产负债表:")
    icbc_bs = call_em("RPT_DMSK_FN_BALANCE", "601398")
    if icbc_bs:
        rec = icbc_bs[0]
        # 银行特有的字段
        special = [k for k in rec if k not in ['SECUCODE','SECURITY_CODE','INDUSTRY_CODE',
                   'ORG_CODE','SECURITY_NAME_ABBR','INDUSTRY_NAME','MARKET','SECURITY_TYPE_CODE',
                   'TRADE_MARKET_CODE','DATE_TYPE_CODE','REPORT_TYPE_CODE','DATA_STATE',
                   'NOTICE_DATE','REPORT_DATE']]
        for k in sorted(special):
            if rec[k] is not None:
                print(f"     {k}: {rec[k]}")

    # ========== 5. 关键：查找东方财富“详细报表”API ==========
    print(f"\n{'='*80}")
    print("📊 Part 5: 东方财富年度报告详细数据")

    # 东方财富有 F10 资料页面，其中财务分析 -> 资产负债表/利润表/现金流量表
    # 这些数据可能来自不同的API
    # 参考：https://emweb.securities.eastmoney.com/pc_hsf10/pages/index.html

    # 尝试 F10 系列的 API
    f10_names = [
        "RPT_F10_FINANCE_MAINFINADATA",     # F10主要财务数据
        "RPT_F10_FINANCE_BALANCESHEET",     # F10资产负债表
        "RPT_F10_FINANCE_INCOMESTATEMENT",  # F10利润表
        "RPT_F10_FINANCE_CASHFLOW",         # F10现金流量表
        "RPT_F10_FINANCE_ABSTRACT",         # F10财务摘要
        "RPT_DMSK_FN_BALANCE_DETAIL",       # 资产负债表明细
        "RPT_DMSK_FN_INCOME_DETAIL",        # 利润表明细
    ]
    for rn in f10_names:
        result = call_em(rn, "002594", page_size=1)
        if result:
            rec = result[0]
            print(f"  ✅ {rn}: {len(rec)}字段")
            # 找目标缺失字段
            for t in ['GOODWILL','CONSTRUCT','RD','RESEARCH','DEV','BOND','CONTRACT',
                      'LONG','BORROW','SHARE_CAPITAL','TOTAL_SHARE']:
                found = [k for k in rec if t.upper() in k.upper()]
                if found:
                    vals = {k: rec[k] for k in found}
                    print(f"     {vals}")
        else:
            print(f"  ❌ {rn}: 不存在")
        time.sleep(0.2)

    print(f"\n{'='*80}")
    print("✅ 探针 v6 完成")


if __name__ == "__main__":
    main()