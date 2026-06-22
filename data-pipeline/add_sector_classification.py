"""
给 companies 表添加 GICS 行业大类（sector）
1. 从东方财富 API 获取申万二级行业
2. 映射到 11 个 GICS 大类
3. ALTER TABLE + 批量更新 Supabase
"""
import os, time, json, requests

# ============================================================
# 环境
# ============================================================
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    for line in open(_env_path):
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

# ============================================================
# 申万二级行业 → 11 个 GICS 大类 映射表
# ============================================================
SW2_TO_GICS = {
    # ---- 日常消费 (Consumer Staples) ----
    "白酒Ⅱ": "日常消费",
    "非白酒": "日常消费",
    "饮料乳品": "日常消费",
    "食品加工": "日常消费",
    "休闲食品": "日常消费",
    "调味发酵品Ⅱ": "日常消费",
    "农产品加工": "日常消费",
    "养殖业": "日常消费",
    "饲料": "日常消费",
    "种植业": "日常消费",
    "渔业": "日常消费",
    "农业综合Ⅱ": "日常消费",
    "个护用品": "日常消费",
    "化妆品": "日常消费",

    # ---- 可选消费 (Consumer Discretionary) ----
    "乘用车": "可选消费",
    "商用车": "可选消费",
    "摩托车及其他": "可选消费",
    "汽车零部件": "可选消费",
    "汽车服务": "可选消费",
    "白色家电": "可选消费",
    "黑色家电": "可选消费",
    "小家电": "可选消费",
    "厨卫电器": "可选消费",
    "家电零部件Ⅱ": "可选消费",
    "其他家电Ⅱ": "可选消费",
    "服装家纺": "可选消费",
    "纺织制造": "可选消费",
    "饰品": "可选消费",
    "家居用品": "可选消费",
    "文娱用品": "可选消费",
    "一般零售": "可选消费",
    "专业连锁Ⅱ": "可选消费",
    "互联网电商": "可选消费",
    "旅游及景区": "可选消费",
    "酒店餐饮": "可选消费",
    "教育": "可选消费",
    "体育Ⅱ": "可选消费",
    "照明设备Ⅱ": "可选消费",

    # ---- 工业 (Industrials) ----
    "通用设备": "工业",
    "专用设备": "工业",
    "轨交设备Ⅱ": "工业",
    "自动化设备": "工业",
    "电机Ⅱ": "工业",
    "其他电源设备Ⅱ": "工业",
    "电网设备": "工业",
    "工程机械": "工业",
    "航空装备Ⅱ": "工业",
    "航天装备Ⅱ": "工业",
    "航海装备Ⅱ": "工业",
    "地面兵装Ⅱ": "工业",
    "军工电子Ⅱ": "工业",
    "基础建设": "工业",
    "专业工程": "工业",
    "工程咨询服务Ⅱ": "工业",
    "房屋建设Ⅱ": "工业",
    "装修装饰Ⅱ": "工业",
    "装修建材": "工业",
    "环保设备Ⅱ": "工业",
    "环境治理": "工业",
    "光伏设备": "工业",
    "风电设备": "工业",
    "电池": "工业",
    "铁路公路": "工业",
    "航运港口": "工业",
    "航空机场": "工业",
    "物流": "工业",
    "贸易Ⅱ": "工业",
    "专业服务": "工业",
    "综合Ⅱ": "工业",

    # ---- 信息技术 (Information Technology) ----
    "半导体": "信息技术",
    "软件开发": "信息技术",
    "IT服务Ⅱ": "信息技术",
    "计算机设备": "信息技术",
    "消费电子": "信息技术",
    "光学光电子": "信息技术",
    "元件": "信息技术",
    "其他电子Ⅱ": "信息技术",

    # ---- 金融 (Financials) ----
    "银行Ⅱ": "金融",
    "证券Ⅱ": "金融",
    "多元金融": "金融",

    # ---- 房地产 (Real Estate) ----
    "房地产开发": "房地产",
    "房地产服务": "房地产",

    # ---- 材料 (Materials) ----
    "化学原料": "材料",
    "化学制品": "材料",
    "化学纤维": "材料",
    "农化制品": "材料",
    "塑料": "材料",
    "橡胶": "材料",
    "工业金属": "材料",
    "小金属": "材料",
    "能源金属": "材料",
    "贵金属": "材料",
    "金属新材料": "材料",
    "冶钢原料": "材料",
    "普钢": "材料",
    "特钢Ⅱ": "材料",
    "水泥": "材料",
    "玻璃玻纤": "材料",
    "非金属材料Ⅱ": "材料",
    "电子化学品Ⅱ": "材料",
    "造纸": "材料",
    "包装印刷": "材料",
    "林业Ⅱ": "材料",

    # ---- 公用事业 (Utilities) ----
    "电力": "公用事业",
    "燃气Ⅱ": "公用事业",

    # ---- 医疗保健 (Healthcare) ----
    "化学制药": "医疗保健",
    "中药Ⅱ": "医疗保健",
    "生物制品": "医疗保健",
    "医疗器械": "医疗保健",
    "医疗服务": "医疗保健",
    "医药商业": "医疗保健",
    "动物保健Ⅱ": "医疗保健",
    "医疗美容": "医疗保健",

    # ---- 能源 (Energy) ----
    "煤炭开采": "能源",
    "油气开采Ⅱ": "能源",
    "油服工程": "能源",
    "炼化及贸易": "能源",
    "焦炭Ⅱ": "能源",

    # ---- 通讯服务 (Communication Services) ----
    "通信设备": "通讯服务",
    "通信服务": "通讯服务",
    "广告营销": "通讯服务",
    "游戏Ⅱ": "通讯服务",
    "影视院线": "通讯服务",
    "数字媒体": "通讯服务",
    "出版": "通讯服务",
    "电视广播Ⅱ": "通讯服务",
}

# ============================================================
# 从东方财富获取所有 A 股申万行业
# ============================================================
def fetch_all_industries():
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    session = requests.Session()
    session.trust_env = False  # 绕过系统代理
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://data.eastmoney.com/"}
    all_data = {}

    for market in ["m:0+t:6", "m:0+t:80"]:
        for pn in range(1, 60):
            params = {
                "pn": pn, "pz": 100, "po": 1, "np": 1,
                "fields": "f12,f100",
                "fid": "f3",
                "fs": market,
                "fltt": 2,
            }
            for retry in range(3):
                try:
                    r = session.get(url, params=params, headers=headers, timeout=30)
                    d = r.json()
                    break
                except Exception as e:
                    if retry < 2:
                        time.sleep(5)
                    else:
                        print(f"  ⚠️ 获取失败 pn={pn}: {e}")
                        d = {}
            if not d.get("data") or not d["data"].get("diff"):
                break
            items = d["data"]["diff"]
            for item in items:
                code = item.get("f12", "")
                if code:
                    all_data[code] = item.get("f100", "")
            if len(items) < 100:
                break
            time.sleep(0.3)  # 避免触发反爬

    return all_data

# ============================================================
# 主流程
# ============================================================
def main():
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("📋 获取申万行业分类...")
    sw_industries = fetch_all_industries()
    print(f"  共获取 {len(sw_industries)} 只股票申万行业")

    # 映射到 GICS 大类
    code_to_sector = {}
    unmapped = set()
    for code, sw2 in sw_industries.items():
        if not sw2:
            continue
        sector = SW2_TO_GICS.get(sw2)
        if sector:
            code_to_sector[code] = sector
        else:
            unmapped.add(sw2)

    print(f"  映射成功: {len(code_to_sector)} 只")
    if unmapped:
        print(f"  ⚠️ 未映射的申万行业: {len(unmapped)} 个")
        for sw in sorted(unmapped):
            # 检查哪些股票属于这个行业
            codes = [c for c, i in sw_industries.items() if i == sw]
            print(f"    {sw}: {codes[:5]}...")

    # 添加 sector 列（如果不存在）
    print("\n🔧 检查 sector 列...")
    try:
        supabase.table("companies").select("sector").limit(1).execute()
        print("  sector 列已存在")
    except:
        print("  添加 sector 列...")
        # 通过 REST 无法直接 ALTER TABLE，需要用 SQL
        # 尝试执行 SQL
        try:
            supabase.rpc("exec_sql", {"sql": "ALTER TABLE companies ADD COLUMN IF NOT EXISTS sector VARCHAR(20)"}).execute()
            print("  ✅ sector 列已添加")
        except:
            print("  ⚠️ 无法通过 RPC 添加列，请在 Supabase SQL Editor 中执行:")
            print("    ALTER TABLE companies ADD COLUMN IF NOT EXISTS sector VARCHAR(20);")
            print("    然后重新运行此脚本")
            return

    # 统计映射结果
    print("\n📊 分类统计:")
    sector_counts = {}
    for sector in code_to_sector.values():
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
    for sector in sorted(sector_counts.keys()):
        print(f"  {sector}: {sector_counts[sector]} 只")

    # 保存映射到 JSON 文件，供后续 curl 脚本使用
    output_file = os.path.join(os.path.dirname(__file__), "sector_mapping.json")
    json.dump(code_to_sector, open(output_file, "w"), ensure_ascii=False, indent=2)
    print(f"\n💾 映射已保存到: {output_file}")
    print(f"   共 {len(code_to_sector)} 条记录")

    print("\n📊 分类统计:")
    sector_counts = {}
    for sector in code_to_sector.values():
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
    for sector in sorted(sector_counts.keys()):
        print(f"  {sector}: {sector_counts[sector]} 只")


if __name__ == "__main__":
    main()