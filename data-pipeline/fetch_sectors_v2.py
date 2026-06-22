#!/usr/bin/env python3
"""用 curl --noproxy '*' 逐页获取沪深A股申万行业，映射到GICS大类"""
import subprocess, json, os, time, sys

SW2_TO_GICS = {
    "白酒Ⅱ":"日常消费","非白酒":"日常消费","饮料乳品":"日常消费","食品加工":"日常消费",
    "休闲食品":"日常消费","调味发酵品Ⅱ":"日常消费","农产品加工":"日常消费","养殖业":"日常消费",
    "饲料":"日常消费","种植业":"日常消费","渔业":"日常消费","农业综合Ⅱ":"日常消费",
    "个护用品":"日常消费","化妆品":"日常消费",
    "乘用车":"可选消费","商用车":"可选消费","摩托车及其他":"可选消费","汽车零部件":"可选消费",
    "汽车服务":"可选消费","白色家电":"可选消费","黑色家电":"可选消费","小家电":"可选消费",
    "厨卫电器":"可选消费","家电零部件Ⅱ":"可选消费","其他家电Ⅱ":"可选消费","服装家纺":"可选消费",
    "纺织制造":"可选消费","饰品":"可选消费","家居用品":"可选消费","文娱用品":"可选消费",
    "一般零售":"可选消费","专业连锁Ⅱ":"可选消费","互联网电商":"可选消费","旅游及景区":"可选消费",
    "酒店餐饮":"可选消费","教育":"可选消费","体育Ⅱ":"可选消费","照明设备Ⅱ":"可选消费",
    "通用设备":"工业","专用设备":"工业","轨交设备Ⅱ":"工业","自动化设备":"工业",
    "电机Ⅱ":"工业","其他电源设备Ⅱ":"工业","电网设备":"工业","工程机械":"工业",
    "航空装备Ⅱ":"工业","航天装备Ⅱ":"工业","航海装备Ⅱ":"工业","地面兵装Ⅱ":"工业",
    "军工电子Ⅱ":"工业","基础建设":"工业","专业工程":"工业","工程咨询服务Ⅱ":"工业",
    "房屋建设Ⅱ":"工业","装修装饰Ⅱ":"工业","装修建材":"工业","环保设备Ⅱ":"工业",
    "环境治理":"工业","光伏设备":"工业","风电设备":"工业","电池":"工业",
    "铁路公路":"工业","航运港口":"工业","航空机场":"工业","物流":"工业",
    "贸易Ⅱ":"工业","专业服务":"工业","综合Ⅱ":"工业",
    "半导体":"信息技术","软件开发":"信息技术","IT服务Ⅱ":"信息技术","计算机设备":"信息技术",
    "消费电子":"信息技术","光学光电子":"信息技术","元件":"信息技术","其他电子Ⅱ":"信息技术",
    "银行Ⅱ":"金融","证券Ⅱ":"金融","多元金融":"金融",
    "房地产开发":"房地产","房地产服务":"房地产",
    "化学原料":"材料","化学制品":"材料","化学纤维":"材料","农化制品":"材料",
    "塑料":"材料","橡胶":"材料","工业金属":"材料","小金属":"材料",
    "能源金属":"材料","贵金属":"材料","金属新材料":"材料","冶钢原料":"材料",
    "普钢":"材料","特钢Ⅱ":"材料","水泥":"材料","玻璃玻纤":"材料",
    "非金属材料Ⅱ":"材料","电子化学品Ⅱ":"材料","造纸":"材料","包装印刷":"材料","林业Ⅱ":"材料",
    "电力":"公用事业","燃气Ⅱ":"公用事业",
    "化学制药":"医疗保健","中药Ⅱ":"医疗保健","生物制品":"医疗保健","医疗器械":"医疗保健",
    "医疗服务":"医疗保健","医药商业":"医疗保健","动物保健Ⅱ":"医疗保健","医疗美容":"医疗保健",
    "煤炭开采":"能源","油气开采Ⅱ":"能源","油服工程":"能源","炼化及贸易":"能源","焦炭Ⅱ":"能源",
    "通信设备":"通讯服务","通信服务":"通讯服务","广告营销":"通讯服务","游戏Ⅱ":"通讯服务",
    "影视院线":"通讯服务","数字媒体":"通讯服务","出版":"通讯服务","电视广播Ⅱ":"通讯服务",
}

OUTPUT = os.path.join(os.path.dirname(__file__), "sector_mapping.json")

def fetch_page(market, pn):
    """单页获取，返回 [{code, sw}, ...]"""
    url = f"https://push2.eastmoney.com/api/qt/clist/get?pn={pn}&pz=100&po=1&np=1&fields=f12,f100&fid=f3&fs={market}&fltt=2"
    for attempt in range(3):
        try:
            r = subprocess.run([
                "curl", "-s", "--noproxy", "*",
                "--connect-timeout", "15", "--max-time", "30",
                url,
                "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "-H", "Referer: https://data.eastmoney.com/",
            ], capture_output=True, text=True, timeout=35, env={**os.environ, "NO_PROXY": "*", "no_proxy": "*"})
            if r.returncode != 0 or not r.stdout.strip():
                if attempt < 2:
                    time.sleep(5)
                continue
            d = json.loads(r.stdout)
            return [{"code": i["f12"], "sw": i.get("f100", "")} for i in d.get("data", {}).get("diff", [])]
        except Exception as e:
            if attempt < 2:
                time.sleep(5)
    return None

def main():
    all_data = {}

    print("📋 获取沪市 (m:0+t:6)...")
    for pn in range(1, 30):
        items = fetch_page("m:0+t:6", pn)
        if items is None:
            print(f"  pn={pn}: ❌ 失败")
            continue
        for item in items:
            all_data[item["code"]] = item["sw"]
        print(f"  pn={pn}: {len(items)} 条, 累计 {len(all_data)}")
        if len(items) < 100:
            break
        time.sleep(1.5)

    print("\n📋 获取深市 (m:0+t:80)...")
    for pn in range(1, 40):
        items = fetch_page("m:0+t:80", pn)
        if items is None:
            print(f"  pn={pn}: ❌ 失败")
            continue
        for item in items:
            all_data[item["code"]] = item["sw"]
        print(f"  pn={pn}: {len(items)} 条, 累计 {len(all_data)}")
        if len(items) < 100:
            break
        time.sleep(1.5)

    # 映射
    code_to_sector = {}
    unmapped = set()
    for code, sw in all_data.items():
        if not sw:
            continue
        sector = SW2_TO_GICS.get(sw)
        if sector:
            code_to_sector[code] = sector
        else:
            unmapped.add(sw)

    print(f"\n✅ 共获取 {len(all_data)} 只股票")
    print(f"  映射成功: {len(code_to_sector)} 只")
    if unmapped:
        print(f"  ⚠️ 未映射: {len(unmapped)} 个行业: {sorted(unmapped)}")

    # 统计
    sector_counts = {}
    for s in code_to_sector.values():
        sector_counts[s] = sector_counts.get(s, 0) + 1
    print("\n📊 分类统计:")
    for s in sorted(sector_counts.keys()):
        print(f"  {s}: {sector_counts[s]} 只")

    # 保存
    json.dump(code_to_sector, open(OUTPUT, "w"), ensure_ascii=False, indent=2)
    print(f"\n💾 已保存到: {OUTPUT}")

if __name__ == "__main__":
    main()