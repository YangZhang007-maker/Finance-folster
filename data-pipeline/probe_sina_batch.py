"""
小批量探针：验证新浪财经 API 的稳定性和数据完整性
随机选 5 只不同板块的股票，测试三张报表的数据获取
"""
import akshare as ak
import pandas as pd
import time
import sys

# 5只随机股票，覆盖不同板块
TEST_STOCKS = [
    ("sh600519", "600519", "贵州茅台", "主板上海"),
    ("sz000858", "000858", "五粮液", "主板深圳"),
    ("sz002594", "002594", "比亚迪", "中小板"),
    ("sh688981", "688981", "中芯国际", "科创板"),
    ("sz300750", "300750", "宁德时代", "创业板"),
]

# 我们要从每张报表中提取的字段
BALANCE_SHEET_FIELDS = {
    "存货": "存货",
    "固定资产": "固定资产净额",  # 或用 固定资产及清理合计
    "在建工程": "在建工程",
    "商誉": "商誉",
    "货币资金": "货币资金",
    "短期借款": "短期借款",
    "长期借款": "长期借款",
    "应付债券": "应付债券",
    "预收款项": "预收款项",
    "合同负债": "合同负债",
    "实收资本(或股本)": "实收资本(或股本)",
}

INCOME_STATEMENT_FIELDS = {
    "营业收入": "营业收入",
    "营业成本": "营业成本",
    "销售费用": "销售费用",
    "管理费用": "管理费用",
    "研发费用": "研发费用",
    "财务费用": "财务费用",
    "营业利润": "营业利润",
    "利润总额": "利润总额",
    "归母净利润": "归属于母公司所有者的净利润",
    "扣非净利润": None,  # 新浪无此字段，从datacenter补
}

CASH_FLOW_FIELDS = {
    "经营活动现金流净额": "经营活动产生的现金流量净额",
    "购建固定资产支付现金": "购建固定资产、无形资产和其他长期资产所支付的现金",
}

def test_sina_report(stock_sina, stock_code, name, report_type):
    """测试新浪单张报表"""
    try:
        df = ak.stock_financial_report_sina(stock=stock_sina, symbol=report_type)
        if df is None or df.empty:
            return None, f"返回空数据"
        return df, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def extract_annual_data(df, field_map, field_label_map):
    """从报表DataFrame中提取年报数据"""
    # 筛选年报(报告日=xxx1231)
    if '报告日' not in df.columns:
        return None

    df['报告日_str'] = df['报告日'].astype(str)
    annuals = df[df['报告日_str'].str.endswith('1231')].copy()
    annuals = annuals.sort_values('报告日_str')

    # 取最近10年
    annuals = annuals.tail(10)

    results = {}
    years = []
    for _, row in annuals.iterrows():
        year = row['报告日_str'][:4]
        years.append(year)

    results['years'] = years

    for our_name, sina_col in field_map.items():
        if sina_col is None:
            continue
        if sina_col in df.columns:
            values = []
            for _, row in annuals.iterrows():
                val = row.get(sina_col)
                values.append(float(val) if pd.notna(val) else None)
            results[our_name] = values
        else:
            results[our_name] = [None] * len(years)

    return results


def main():
    print("="*80)
    print("🔍 小批量探针：新浪财经 API 稳定性测试")
    print(f"   测试股票: {len(TEST_STOCKS)} 只")
    print("="*80)

    total_success = 0
    total_fail = 0
    all_results = []

    for stock_sina, stock_code, name, market in TEST_STOCKS:
        print(f"\n{'='*80}")
        print(f"📊 {stock_code} {name} ({market})")

        stock_result = {"code": stock_code, "name": name}

        for report_type in ["资产负债表", "利润表", "现金流量表"]:
            df, error = test_sina_report(stock_sina, stock_code, name, report_type)

            if error:
                print(f"   ❌ {report_type}: {error}")
                total_fail += 1
                stock_result[report_type] = "FAIL"
            else:
                print(f"   ✅ {report_type}: {df.shape[0]}行 × {df.shape[1]}列")

                # 提取年报数据
                if report_type == "资产负债表":
                    field_map = BALANCE_SHEET_FIELDS
                elif report_type == "利润表":
                    field_map = INCOME_STATEMENT_FIELDS
                else:
                    field_map = CASH_FLOW_FIELDS

                data = extract_annual_data(df, field_map, field_map)
                if data:
                    years = data['years']
                    print(f"      年报: {years[0]}~{years[-1]} ({len(years)}年)")

                    # 检查每个字段的完整性
                    for field_name in field_map:
                        if field_name in data and field_map[field_name] is not None:
                            non_null = sum(1 for v in data[field_name] if v is not None)
                            status = "✅" if non_null >= 8 else "⚠️" if non_null >= 5 else "❌"
                            print(f"      {status} {field_name}: {non_null}/{len(years)}年有值")

                    # 打印第一年的数据作为样本
                    print(f"      📋 {years[0]} 样本数据:")
                    for field_name in field_map:
                        if field_name in data and field_map[field_name] is not None:
                            val = data[field_name][0]
                            if val is not None:
                                if abs(val) >= 1e8:
                                    print(f"         {field_name}: {val/1e8:.2f}亿")
                                elif abs(val) >= 1e4:
                                    print(f"         {field_name}: {val/1e4:.2f}万")
                                else:
                                    print(f"         {field_name}: {val:.2f}")

                total_success += 1
                stock_result[report_type] = "OK"

        all_results.append(stock_result)
        time.sleep(0.5)  # 股票间间隔

    # 汇总
    print(f"\n{'='*80}")
    print("📊 汇总:")
    print(f"   总请求: {len(TEST_STOCKS)*3}, 成功: {total_success}, 失败: {total_fail}")
    print(f"   成功率: {total_success/(len(TEST_STOCKS)*3)*100:.1f}%")

    if total_fail > 0:
        print(f"\n   ❌ 有 {total_fail} 个请求失败，需评估是否继续")
    else:
        print(f"\n   ✅ 全部成功！可以开始全量同步")

    return total_fail == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)