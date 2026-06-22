#!/usr/bin/env python3
"""逐只查询缺失的 sector，用 curl 子进程绕过代理"""
import subprocess, json, time, os

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

SUPABASE_URL = "https://otrmfvhktypuvyaxzset.supabase.co"
SUPABASE_KEY = "sb_publishable_0aEsxj4KvgtOoIHc6vLicQ_5k1M4ogU"

ENV = {"NO_PROXY": "*", "no_proxy": "*"}

def curl_get(url, timeout=15):
    """curl 子进程封装"""
    r = subprocess.run([
        "curl", "-s", "--noproxy", "*", "--connect-timeout", str(timeout), "--max-time", str(timeout),
        url,
        "-H", f"apikey: {SUPABASE_KEY}",
        "-H", f"Authorization: Bearer {SUPABASE_KEY}",
    ], capture_output=True, text=True, timeout=timeout+5, env={**os.environ, **ENV})
    return r.stdout

def get_sector_curl(code):
    """用 curl 获取申万行业"""
    if code.startswith(('6','9')):
        secid = f"1.{code}"
    else:
        secid = f"0.{code}"
    url = f"https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=2&fields=f57,f58,f100&secid={secid}"

    for retry in range(4):
        try:
            r = subprocess.run([
                "curl", "-s", "--noproxy", "*", "--connect-timeout", "10", "--max-time", "15",
                url,
                "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "-H", "Referer: https://quote.eastmoney.com/",
            ], capture_output=True, text=True, timeout=18, env={**os.environ, **ENV})
            if r.returncode == 0 and r.stdout.strip():
                d = json.loads(r.stdout)
                if d.get("data"):
                    sw = d["data"].get("f100", "")
                    if sw:
                        return SW2_TO_GICS.get(sw)
        except: pass
        if retry < 3:
            time.sleep(1.5 * (retry + 1))
    return None

def main():
    # 1. 获取缺失股票列表
    print("📋 获取缺失 sector 的股票...")
    missing = []
    offset = 0
    while True:
        result = curl_get(f"{SUPABASE_URL}/rest/v1/companies?select=code&sector=is.null&offset={offset}&limit=1000")
        try:
            data = json.loads(result)
        except:
            print(f"  解析失败 offset={offset}")
            break
        if not data: break
        missing.extend(d['code'] for d in data)
        if len(data) < 1000: break
        offset += 1000
        time.sleep(0.3)

    print(f"  共 {len(missing)} 只缺失")

    # 2. 逐只查询
    print(f"\n🔍 逐只查询...")
    result = {}
    success_streak = 0
    for i, code in enumerate(missing):
        sector = get_sector_curl(code)
        if sector:
            result[code] = sector
            success_streak += 1
        else:
            success_streak = 0

        # 如果连续失败10次，暂停30秒
        if success_streak == 0 and i > 0 and (i % 50 == 0):
            recent = sum(1 for c in missing[i-50:i] if c in result)
            if recent < 5:
                print(f"  ⚠️ 近期成功率低，暂停30秒...")
                time.sleep(30)

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(missing)}] ✅ {len(result)} ({len(result)*100/(i+1):.1f}%)")

        time.sleep(0.3)

    print(f"\n✅ 成功: {len(result)}/{len(missing)} ({len(result)*100/max(len(missing),1):.1f}%)")

    # 3. 保存 JSON
    out = os.path.join(os.path.dirname(__file__), "fill_sectors.json")
    json.dump(result, open(out, "w"), ensure_ascii=False)
    print(f"💾 保存: {out}")

    # 4. 统计
    from collections import Counter
    counts = Counter(result.values())
    for s, c in sorted(counts.items()):
        print(f"  {s}: {c}")

    # 5. 生成 SQL
    lines = ["-- 补全缺失 sector", "BEGIN;"]
    for code, sector in result.items():
        lines.append(f"UPDATE companies SET sector = '{sector}' WHERE code = '{code}' AND sector IS NULL;")
    lines.append("COMMIT;")
    sql_out = os.path.join(os.path.dirname(__file__), "update_sectors_fill.sql")
    with open(sql_out, "w") as f:
        f.write("\n".join(lines))
    print(f"💾 SQL: {sql_out}")

if __name__ == "__main__":
    main()