"""
探针 Plan B：测试替代数据源
1. stock_financial_abstract_ths (同花顺)
2. stock_financial_report_sina (新浪财经)
3. stock_financial_analysis_indicator
"""
import akshare as ak
import pandas as pd
import time

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 200)
pd.set_option('display.width', 300)
pd.set_option('display.max_colwidth', 50)

def test_ths():
    """测试同花顺源"""
    print("="*100)
    print("📊 Plan B-1: stock_financial_abstract_ths (同花顺)")
    try:
        df = ak.stock_financial_abstract_ths(symbol="600519", indicator="按年度")
        print(f"   形状: {df.shape}")
        print(f"   列名: {list(df.columns)}")

        # 所有行
        print(f"\n   所有数据:")
        for _, row in df.iterrows():
            print(f"     {row.to_dict()}")

    except Exception as e:
        print(f"   ❌ {e}")
        import traceback
        traceback.print_exc()

def test_sina():
    """测试新浪财经源"""
    print(f"\n{'='*100}")
    print("📊 Plan B-2: stock_financial_report_sina (新浪财经)")

    # 新浪函数可能有不同的调用方式
    try:
        # stock_financial_report_sina 可能需要不同的参数
        # 试试看文档
        import inspect
        try:
            src = inspect.getsource(ak.stock_financial_report_sina)
            print(f"   函数签名前5行:")
            for line in src.split('\n')[:10]:
                print(f"     {line}")
        except:
            pass

        # 尝试调用
        result = ak.stock_financial_report_sina(stock="sh600519", symbol="资产负债表")
        if result is not None:
            print(f"   返回类型: {type(result)}")
            if isinstance(result, pd.DataFrame):
                print(f"   形状: {result.shape}")
                print(f"   列名: {list(result.columns)}")
                print(f"\n   前20行:")
                print(result.head(20).to_string())
            else:
                print(f"   值: {result}")
        else:
            print(f"   ❌ 返回 None")
    except Exception as e:
        print(f"   ❌ {e}")
        import traceback
        traceback.print_exc()


def test_sina_all_reports():
    """测试新浪财经所有报表类型"""
    print(f"\n{'='*100}")
    print("📊 Plan B-3: 新浪财经 - 所有报表类型")

    reports = ["资产负债表", "利润表", "现金流量表"]

    for report in reports:
        try:
            result = ak.stock_financial_report_sina(stock="sh600519", symbol=report)
            if isinstance(result, pd.DataFrame):
                print(f"\n   ✅ {report}: 形状 {result.shape}")
                print(f"      列名: {list(result.columns)}")
                if not result.empty:
                    # 找每年的12-31数据
                    if '报告日' in result.columns or 'REPORT_DATE' in result.columns:
                        date_col = '报告日' if '报告日' in result.columns else 'REPORT_DATE'
                        annuals = result[result[date_col].astype(str).str.contains('12-31|1231', na=False)]
                        print(f"      年报行数: {len(annuals)}")

                    # 打印所有科目名（第一列）
                    col0 = result.columns[0]
                    print(f"      科目名 ({len(result[col0].unique())}个):")
                    for name in result[col0].unique()[:50]:
                        print(f"        - {name}")
            else:
                print(f"   ❌ {report}: 返回 {type(result)}")
        except Exception as e:
            print(f"   ❌ {report}: {e}")
        time.sleep(0.5)


def test_sina_other_stocks():
    """测试新浪财经对制造业公司的数据"""
    print(f"\n{'='*100}")
    print("📊 Plan B-4: 新浪财经 - 比亚迪 002594 资产负债表")

    try:
        result = ak.stock_financial_report_sina(stock="sz002594", symbol="资产负债表")
        if isinstance(result, pd.DataFrame):
            print(f"   形状: {result.shape}")
            print(f"   列名: {list(result.columns)}")
            col0 = result.columns[0]
            # 找我们的缺失字段
            missing = ['研发费用', '在建工程', '商誉', '长期借款', '应付债券', '短期借款', '合同负债', '总股本', '预收']
            for t in missing:
                matched = result[result[col0].astype(str).str.contains(t, na=False)]
                if not matched.empty:
                    val_cols = [c for c in result.columns if c != col0][:3]  # 前3个数据列
                    vals = {c: matched.iloc[0][c] for c in val_cols}
                    print(f"   ✅ {t}: {matched.iloc[0][col0]} -> {vals}")
                else:
                    print(f"   ❌ {t}: 未找到")
    except Exception as e:
        print(f"   ❌ {e}")
        import traceback
        traceback.print_exc()


def test_analysis_indicator():
    """测试财务分析指标"""
    print(f"\n{'='*100}")
    print("📊 Plan B-5: stock_financial_analysis_indicator")
    try:
        result = ak.stock_financial_analysis_indicator(symbol="600519")
        if isinstance(result, pd.DataFrame):
            print(f"   形状: {result.shape}")
            print(f"   列名: {list(result.columns)}")
            print(f"   前20行:")
            print(result.head(20).to_string())
        else:
            print(f"   返回: {type(result)}")
    except Exception as e:
        print(f"   ❌ {e}")


if __name__ == "__main__":
    test_ths()
    time.sleep(1)
    test_sina()
    time.sleep(1)
    test_sina_all_reports()
    time.sleep(1)
    test_sina_other_stocks()
    time.sleep(1)
    test_analysis_indicator()
    print(f"\n{'='*100}")
    print("✅ Plan B 探针完成")