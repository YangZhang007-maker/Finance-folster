"""
探针 v7：直连东方财富三大详细报表 API
绕过 AKShare 的 HTML 解析步骤，直接用 company_type 参数

URL 模式：
- 资产负债表: zcfzbAjaxNew (资产/负债/权益 全部科目)
- 利润表: lrbAjaxNew (收入/成本/费用 全部科目)
- 现金流量表: xjllbAjaxNew (经营/投资/筹资 现金流)

company_type: 1=通用, 2=银行, 3=保险, 4=证券
对大部分A股公司用 4（通用），失败的 fallback 到 3
"""
import requests
import json
import time
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://emweb.securities.eastmoney.com/",
}

# 三大报表 URL
REPORT_URLS = {
    "资产负债表": "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/zcfzbAjaxNew",
    "利润表": "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/lrbAjaxNew",
    "现金流量表": "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/xjllbAjaxNew",
}

def fetch_detail_report(url_key, stock_code, company_type=4):
    """
    获取详细报表数据
    stock_code: 如 "SH600519" 或 "600519"
    """
    # 确保带市场前缀
    if not stock_code.startswith(("SH", "SZ")):
        if stock_code.startswith("6") or stock_code.startswith("9"):
            stock_code = f"SH{stock_code}"
        else:
            stock_code = f"SZ{stock_code}"

    url = REPORT_URLS[url_key]
    params = {
        "companyType": str(company_type),
        "reportDateType": "1",  # 1=按年度
        "code": stock_code,
    }

    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
            data = resp.json()
            if "data" in data and data["data"]:
                # 返回的是按 REPORT_DATE 分列的宽表
                df = pd.DataFrame(data["data"])
                return df
            elif company_type != 3:
                # fallback to type 3
                params["companyType"] = "3"
                continue
            else:
                print(f"     ❌ type=3也无数据")
                return None
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"     ❌ {type(e).__name__}: {e}")
                return None
    return None


def main():
    stock = "600519"  # 茅台

    # ======== 利润表 ========
    print("="*80)
    print("📊 利润表 (lrbAjaxNew) - 茅台 600519")
    income = fetch_detail_report("利润表", stock)
    if income is not None:
        print(f"   形状: {income.shape}")
        print(f"   列名({len(income.columns)}): {list(income.columns)}")

        # 第一列通常是科目名称
        col0 = income.columns[0]
        date_cols = [c for c in income.columns if c != col0]
        print(f"   REPORT_DATE列: {date_cols}")

        # 找我们需要的科目
        targets = ['研发费用', '营业成本', '销售费用', '管理费用', '财务费用',
                   '营业利润', '利润总额', '营业收入', '归母净利润', '扣非净利润',
                   '税金及附加', '资产减值损失', '信用减值损失', '投资收益',
                   '公允价值变动收益', '其他收益', '营业外收入', '营业外支出']
        found_items = []
        for t in targets:
            matched = income[income[col0].str.contains(t, na=False)]
            if not matched.empty:
                found_items.append(t)
                # 打印最新年份的值
                if date_cols:
                    latest_col = date_cols[-1]  # 最后一个是最近年份
                    val = matched.iloc[0][latest_col]
                    print(f"   ✅ {t}: {val}")
                print(f"      匹配的行名: {matched.iloc[0][col0]}")
            #else:
            #    print(f"   ❌ 科目'{t}'未找到")

        # 如果不含"研发费用"，打印所有包含"研发"的行
        rd_rows = income[income[col0].str.contains('研发', na=False)]
        if not rd_rows.empty:
            print(f"   🔍 含'研发'的行: {rd_rows[col0].tolist()}")
        # 如果根本没有研发费用，看看是否在 OPERATE_EXPENSE 里已经包含
        # 实际上茅台是白酒企业，它的 OPERATE_EXPENSE = 营业总成本(含研发)
        # 制造业公司(比亚迪)应该有独立的研发费用行
        if '研发费用' not in found_items:
            print(f"   ⚠️ 茅台利润表没有独立的'研发费用'行(白酒企业)")
            print(f"   尝试比亚迪...")
        time.sleep(0.5)

    # ======== 比亚迪利润表（找研发费用）========
    print(f"\n📊 利润表 (比亚迪 002594) - 找研发费用")
    byd_income = fetch_detail_report("利润表", "002594")
    if byd_income is not None:
        col0 = byd_income.columns[0]
        date_cols = [c for c in byd_income.columns if c != col0]
        # 找研发费用行
        rd = byd_income[byd_income[col0].str.contains('研发费用', na=False)]
        if not rd.empty:
            latest = date_cols[-1]
            print(f"   ✅ 研发费用: {rd.iloc[0][latest]}")
            print(f"      行名: {rd.iloc[0][col0]}")
        # 打印所有行名
        print(f"\n   比亚迪利润表所有科目名:")
        for name in byd_income[col0]:
            print(f"     {name}")

    # ======== 资产负债表 ========
    print(f"\n{'='*80}")
    print("📊 资产负债表 (zcfzbAjaxNew) - 茅台 600519")
    balance = fetch_detail_report("资产负债表", stock)
    if balance is not None:
        print(f"   形状: {balance.shape}")
        col0 = balance.columns[0]
        date_cols = [c for c in balance.columns if c != col0]

        targets = ['在建工程', '商誉', '长期借款', '应付债券', '合同负债', '短期借款',
                   '存货', '固定资产', '货币资金', '预收款项', '预收账款', '总股本',
                   '实收资本', '股本', '现金及现金等价物', '开发支出', '无形资产']
        print(f"\n   目标科目:")
        for t in targets:
            matched = balance[balance[col0].str.contains(t, na=False)]
            if not matched.empty:
                latest = date_cols[-1]
                val = matched.iloc[0][latest]
                print(f"   ✅ {t}: {val}  (行: {matched.iloc[0][col0]})")

    # ======== 现金流量表 ========
    print(f"\n{'='*80}")
    print("📊 现金流量表 (xjllbAjaxNew) - 茅台 600519")
    cashflow = fetch_detail_report("现金流量表", stock)
    if cashflow is not None:
        print(f"   形状: {cashflow.shape}")
        col0 = cashflow.columns[0]
        date_cols = [c for c in cashflow.columns if c != col0]

        targets = ['经营活动产生的现金流量净额', '购建固定资产', '投资活动产生的现金流量净额',
                   '筹资活动产生的现金流量净额']
        print(f"\n   目标科目:")
        for t in targets:
            matched = cashflow[cashflow[col0].str.contains(t, na=False)]
            if not matched.empty:
                latest = date_cols[-1]
                val = matched.iloc[0][latest]
                print(f"   ✅ {t}: {val}  (行: {matched.iloc[0][col0]})")

    # ======== 尝试不同 company_type ========
    print(f"\n{'='*80}")
    print("📊 Part 2: 尝试不同 company_type")

    # 有些公司可能需要不同的 company_type
    # 先确认默认 type=4 对茅台适用
    for ct in [1, 2, 3, 4]:
        result = fetch_detail_report("资产负债表", stock, company_type=ct)
        if result is not None:
            rd_cols = [c for c in result.columns if 'REPORT_DATE' in c]
            # 找合同负债
            col0 = result.columns[0]
            cl = result[result[col0].str.contains('合同负债|预收', na=False)]
            print(f"   company_type={ct}: {result.shape}, 合同负债行: {cl[col0].tolist() if not cl.empty else '无'}")

    # ======== 完整字段汇总 ========
    print(f"\n{'='*80}")
    print("📊 完整字段Mapping汇总:")
    print("""
    数据源策略:
    ├── 利润表 (lrbAjaxNew)
    │   ├── 营业收入 (营业总收入)
    │   ├── 营业成本 (营业总成本)
    │   ├── 销售费用
    │   ├── 管理费用
    │   ├── 研发费用 ← 制造业公司有独立行
    │   ├── 财务费用
    │   ├── 营业利润
    │   ├── 利润总额
    │   ├── 归母净利润
    │   └── 扣非净利润
    │
    ├── 资产负债表 (zcfzbAjaxNew)
    │   ├── 预收款/合同负债
    │   ├── 存货
    │   ├── 固定资产
    │   ├── 在建工程
    │   ├── 现金及现金等价物
    │   ├── 商誉
    │   ├── 短期借款
    │   ├── 长期借款
    │   ├── 应付债券
    │   └── 总股本 (实收资本)
    │
    └── 现金流量表 (xjllbAjaxNew)
        ├── 经营活动现金流净额
        └── 购建固定资产支付现金
    """)

    print("✅ 探针 v7 完成")


if __name__ == "__main__":
    main()