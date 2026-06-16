"""
探针 v4：追查AKShare完整财务报表函数
- stock_balance_sheet_by_report_em
- stock_profit_sheet_by_report_em
- stock_cash_flow_sheet_by_report_em
- stock_balance_sheet_by_yearly_em
- stock_profit_sheet_by_yearly_em
"""
import akshare as ak
import pandas as pd
import time

def try_func(name, func, *args, **kwargs):
    """安全调用AKShare函数"""
    print(f"\n{'='*80}")
    print(f"🔍 {name}")
    try:
        result = func(*args, **kwargs)
        if isinstance(result, pd.DataFrame):
            if result.empty:
                print(f"   ❌ 空DataFrame")
                return None
            print(f"   ✅ 形状: {result.shape}")
            print(f"   列名 ({len(result.columns)}个): {list(result.columns)}")
            print(f"   前3行:")
            print(result.head(3).to_string())
            return result
        else:
            print(f"   ✅ 返回类型: {type(result).__name__}, 值: {result}")
            return result
    except Exception as e:
        print(f"   ❌ {type(e).__name__}: {e}")
        return None

def main():
    stock = "600519"

    # === 1. 利润表(按报告期) ===
    df1 = try_func("stock_profit_sheet_by_report_em", ak.stock_profit_sheet_by_report_em, symbol=stock)
    if df1 is not None:
        # 找年度12-31数据和研发费用
        annuals = df1[df1['REPORT_DATE'].str.endswith('1231', na=False)] if 'REPORT_DATE' in df1.columns else df1
        print(f"\n   年报行数: {len(annuals)}")
        targets = ['研发费用', '营业收入', '营业成本', '销售费用', '管理费用', '财务费用',
                   '营业利润', '利润总额', '归母净利润', '扣非净利润']
        found_in_cols = []
        for t in targets:
            cols = [c for c in df1.columns if t in c]
            if cols:
                found_in_cols.extend(cols)
        if found_in_cols:
            print(f"   目标列: {found_in_cols}")

    time.sleep(0.5)

    # === 2. 资产负债表(按报告期) ===
    df2 = try_func("stock_balance_sheet_by_report_em", ak.stock_balance_sheet_by_report_em, symbol=stock)
    if df2 is not None:
        targets_bs = ['在建工程','商誉','长期借款','应付债券','合同负债','短期借款','总股本',
                      '存货','固定资产','货币资金','预收款项','现金']
        found = []
        for t in targets_bs:
            cols = [c for c in df2.columns if t in c]
            if cols:
                found.extend(cols)
        if found:
            print(f"\n   目标列: {found}")
        else:
            # 打印第一列(项目名)看看
            col0 = df2.columns[0]
            print(f"\n   第一列: {col0}")
            items_matched = df2[df2[col0].str.contains('|'.join(targets_bs[:6]), na=False)]
            if not items_matched.empty:
                print(f"   在项目列中匹配到: {items_matched[col0].tolist()}")

    time.sleep(0.5)

    # === 3. 现金流量表(按报告期) ===
    df3 = try_func("stock_cash_flow_sheet_by_report_em", ak.stock_cash_flow_sheet_by_report_em, symbol=stock)
    if df3 is not None:
        targets_cf = ['经营活动','现金流','固定资产','购建']
        found = []
        for t in targets_cf:
            cols = [c for c in df3.columns if t in c]
            if cols:
                found.extend(cols)
        if found:
            print(f"\n   目标列: {found}")
        else:
            col0 = df3.columns[0]
            items_matched = df3[df3[col0].str.contains('|'.join(targets_cf), na=False)]
            if not items_matched.empty:
                print(f"   在项目列中匹配到: {items_matched[col0].tolist()}")

    time.sleep(0.5)

    # === 4. 年度版资产负债表 ===
    df4 = try_func("stock_balance_sheet_by_yearly_em", ak.stock_balance_sheet_by_yearly_em, symbol=stock)

    time.sleep(0.5)

    # === 5. 年度版利润表 ===
    df5 = try_func("stock_profit_sheet_by_yearly_em", ak.stock_profit_sheet_by_yearly_em, symbol=stock)

    time.sleep(0.5)

    # === 6. 年度版现金流量表 ===
    df6 = try_func("stock_cash_flow_sheet_by_yearly_em", ak.stock_cash_flow_sheet_by_yearly_em, symbol=stock)

    print(f"\n{'='*80}")
    print("✅ 探针 v4 完成")


if __name__ == "__main__":
    main()