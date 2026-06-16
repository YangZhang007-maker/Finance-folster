"""
导出 Supabase 数据表到本地 PostgreSQL
用法: python export_to_local.py
"""
import os, sys, time
import psycopg2
from supabase import create_client

# Load Supabase env
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    for line in open(_env_path):
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

# Local PG config
LOCAL_HOST = "localhost"
LOCAL_PORT = 5432
LOCAL_USER = "postgres"
LOCAL_PASSWORD = "admin123"
LOCAL_DB = "VIP"
BATCH = 1000

# Tables to export (name, has_id_serial)
TABLES = [
    ("companies", True),
    ("annual_financials", True),
    ("annual_financials_v2", True),
]

def get_local_conn():
    return psycopg2.connect(
        host=LOCAL_HOST, port=LOCAL_PORT,
        user=LOCAL_USER, password=LOCAL_PASSWORD,
        dbname=LOCAL_DB
    )

def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_table_columns(supabase, table_name):
    """从 Supabase 获取表的第一行来确定列名"""
    r = supabase.table(table_name).select("*").limit(1).execute()
    if r.data:
        return list(r.data[0].keys()), r.data[0]
    return [], {}

def get_table_columns_detailed(supabase, table_name, sample):
    """获取所有列名，排除 id,created_at,updated_at (让本地自动生成)"""
    cols = list(sample.keys())
    # Keep id but will be set explicitly
    return cols

# 已知的文本列（名称、代码等）
TEXT_COLUMNS = {
    "code", "stock_name", "name", "report_date", "data_source",
    "industry", "market", "company_type",
}

def infer_column_type(col, val, table_name):
    """根据列名和样本值推断 PostgreSQL 类型"""
    if col == "id":
        return "BIGINT PRIMARY KEY"
    if col in TEXT_COLUMNS:
        return "TEXT"
    if isinstance(val, bool):
        return "BOOLEAN"
    if isinstance(val, str):
        return "TEXT"
    if isinstance(val, int):
        return "NUMERIC"
    if isinstance(val, float):
        # Detect percentages (small values like 0.1234 representing 12.34%)
        if abs(val) < 100 and val != int(val):
            return "NUMERIC"
        return "NUMERIC"
    if val is None:
        # Can't determine from NULL - use column name hints
        if col.endswith("_yoy") or col.endswith("_margin") or col.endswith("_ratio") or col.endswith("_return"):
            return "NUMERIC"
        # For columns in v2 that we know are numeric
        if table_name == "annual_financials_v2":
            return "NUMERIC"
        return "TEXT"
    return "TEXT"

def create_local_table(conn, table_name, columns, sample):
    """根据 Supabase 数据类型创建本地表"""
    cur = conn.cursor()

    # Drop existing
    cur.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE')

    # Build column defs
    col_defs = []
    for col in columns:
        val = sample.get(col)
        pg_type = infer_column_type(col, val, table_name)
        col_defs.append(f'"{col}" {pg_type}')

    sql = f'CREATE TABLE "{table_name}" (\n  ' + ',\n  '.join(col_defs) + '\n)'
    print(f"  SQL: {sql[:200]}...")
    cur.execute(sql)
    conn.commit()
    print(f"  ✅ 本地表 {table_name} 已创建")

def export_table(supabase, conn, table_name):
    """从 Supabase 分页读取，写入本地 PG"""
    print(f"\n📦 导出 {table_name}...")

    # Get column list from Supabase
    r = supabase.table(table_name).select("*").limit(1).execute()
    if not r.data:
        print(f"  ⚠️ 表为空，跳过")
        return 0

    columns = list(r.data[0].keys())
    print(f"  列数: {len(columns)}")

    # Create local table
    create_local_table(conn, table_name, columns, r.data[0])

    # Build INSERT statement
    quoted_cols = [f'"{c}"' for c in columns]
    placeholders = ','.join(['%s'] * len(columns))
    insert_sql = f'INSERT INTO "{table_name}" ({",".join(quoted_cols)}) VALUES ({placeholders}) ON CONFLICT ("id") DO NOTHING'

    # Export in batches
    offset = 0
    total = 0
    cur = conn.cursor()

    while True:
        r = supabase.table(table_name).select("*").range(offset, offset + BATCH - 1).execute()
        if not r.data:
            break

        rows = []
        for row in r.data:
            vals = []
            for col in columns:
                vals.append(row.get(col))
            rows.append(tuple(vals))

        # Insert into local DB
        try:
            cur.executemany(insert_sql, rows)
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"  ❌ 写入失败: {e}")
            # Try one by one
            for vals in rows:
                try:
                    cur.execute(insert_sql, vals)
                except:
                    pass
            conn.commit()

        total += len(r.data)
        print(f"  [{total}] ...", end="\r")

        if len(r.data) < BATCH:
            break
        offset += BATCH

    print(f"\n  ✅ {table_name}: {total} 行导入完成")
    return total

def verify(conn):
    print("\n📊 验证本地数据:")
    cur = conn.cursor()
    for table_name, _ in TABLES:
        cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        cnt = cur.fetchone()[0]
        print(f"  {table_name}: {cnt:,} 行")

def main():
    print("🔌 连接 Supabase...")
    supabase = get_supabase_client()

    print("🔌 连接本地 PostgreSQL...")
    conn = get_local_conn()
    print(f"  已连接: {LOCAL_DB}")

    for table_name, _ in TABLES:
        export_table(supabase, conn, table_name)

    verify(conn)
    conn.close()
    print("\n🎉 全部完成!")

if __name__ == "__main__":
    main()