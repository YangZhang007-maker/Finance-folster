#!/usr/bin/env python3
"""用 curl 批量更新 Supabase companies 表的 sector 字段"""
import subprocess, json, os, time, sys

ENV = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(ENV):
    for line in open(ENV):
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

MAPPING_FILE = os.path.join(os.path.dirname(__file__), "sector_mapping.json")

def supabase_patch(code, sector):
    """用 curl PATCH 更新单条记录"""
    url = f"{SUPABASE_URL}/rest/v1/companies?code=eq.{code}"
    for attempt in range(3):
        try:
            r = subprocess.run([
                "curl", "-s", "--noproxy", "*",
                "-X", "PATCH",
                url,
                "-H", f"apikey: {SUPABASE_KEY}",
                "-H", f"Authorization: Bearer {SUPABASE_KEY}",
                "-H", "Content-Type: application/json",
                "-H", "Prefer: return=minimal",
                "-d", json.dumps({"sector": sector}),
                "--connect-timeout", "10", "--max-time", "20",
            ], capture_output=True, text=True, timeout=25)
            if r.returncode == 0 and (not r.stdout.strip() or "error" not in r.stdout.lower()):
                return True
            if "PGRST" in r.stdout or "42" in r.stdout:
                # 永久性错误，不重试
                print(f"  ⚠️ {code}: {r.stdout[:100]}")
                return False
        except Exception as e:
            if attempt < 2:
                time.sleep(3)
    return False

def main():
    code_to_sector = json.load(open(MAPPING_FILE))
    print(f"📋 加载 {len(code_to_sector)} 条映射")

    # 批量更新
    total = len(code_to_sector)
    success = 0
    failed = 0
    start = time.time()

    for i, (code, sector) in enumerate(code_to_sector.items()):
        if supabase_patch(code, sector):
            success += 1
        else:
            failed += 1

        if (i + 1) % 100 == 0:
            elapsed = time.time() - start
            spd = (i + 1) / (elapsed / 60) if elapsed > 0 else 0
            print(f"  [{i+1}/{total}] ✅{success} ❌{failed} | {spd:.0f}/min")

    elapsed = time.time() - start
    print(f"\n✅ 完成! 成功 {success}/{total} ({elapsed/60:.1f}min)")

    # 验证
    print("\n🔍 验证...")
    r = subprocess.run([
        "curl", "-s", "--noproxy", "*",
        f"{SUPABASE_URL}/rest/v1/companies?select=code,name,sector&not.is=sector.null&limit=3",
        "-H", f"apikey: {SUPABASE_KEY}",
        "-H", f"Authorization: Bearer {SUPABASE_KEY}",
    ], capture_output=True, text=True, timeout=15)
    try:
        data = json.loads(r.stdout)
        for row in data:
            print(f"  {row['code']} {row['name']} → {row['sector']}")
    except:
        print(f"  (raw) {r.stdout[:200]}")

    # 覆盖率
    r2 = subprocess.run([
        "curl", "-s", "--noproxy", "*", "-I",
        f"{SUPABASE_URL}/rest/v1/companies?select=count&not.is=sector.null",
        "-H", f"apikey: {SUPABASE_KEY}",
        "-H", f"Authorization: Bearer {SUPABASE_KEY}",
        "-H", "Prefer: count=exact",
    ], capture_output=True, text=True, timeout=15)
    for line in r2.stderr.split("\n"):
        if "content-range" in line.lower():
            print(f"  覆盖率: {line.strip()}")

if __name__ == "__main__":
    main()