#!/usr/bin/env python3
"""Sync Supabase data to local PostgreSQL VIP database."""

import requests
import psycopg2
import psycopg2.extras

SUPABASE_URL = "https://otrmfvhktypuvyaxzset.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im90cm1mdmhrdHlwdXZ5YXh6c2V0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTc5ODMxMywiZXhwIjoyMDk1Mzc0MzEzfQ.7F6rF9MJHGGGEhinASPVZ7PuctU26s9Fu1SMi2WOS9w"

PG_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "zhangyang",
    "dbname": "VIP"
}

BATCH_SIZE = 1000

TABLES = {
    "companies": ["id", "code", "name", "industry", "market", "updated_at", "sector"],
    "watchlist": ["id", "code", "added_at"],
    "financial_indicators": [
        "id", "code", "report_date", "pe_ratio", "pb_ratio", "ps_ratio", "peg_ratio",
        "roe", "roa", "gross_margin", "net_margin", "revenue_growth",
        "net_profit_growth", "debt_to_assets", "current_ratio", "free_cash_flow",
        "dividend_yield", "market_cap", "total_revenue", "net_profit",
        "total_assets", "net_assets", "buffett_index", "updated_at"
    ],
    "annual_financials": [
        "id", "code", "report_date", "roe", "roa", "gross_margin", "net_margin",
        "debt_to_assets", "net_profit", "total_revenue", "gross_profit",
        "net_assets", "free_cash_flow", "revenue_growth", "net_profit_growth",
        "current_ratio", "pe_ratio", "pb_ratio", "market_cap", "buffett_index",
        "updated_at"
    ],
    "annual_financials_v2": [
        "id", "code", "stock_name", "year", "total_revenue", "gross_profit",
        "gross_margin", "net_margin", "roe", "total_market_cap", "revenue_yoy",
        "net_profit_yoy", "eps", "bps", "roa", "operating_revenue", "operating_cost",
        "selling_expense", "admin_expense", "rd_expense", "finance_expense",
        "operating_profit", "total_profit", "parent_net_profit", "deducted_net_profit",
        "advance_contract_liab", "inventory", "fixed_asset", "construction_in_progress",
        "cash_and_equivalents", "goodwill", "short_term_loan", "long_term_loan",
        "bonds_payable", "total_shares", "operating_cash_flow", "capex",
        "data_source", "created_at", "updated_at", "total_assets", "total_liabilities",
        "parent_equity", "effective_asset_return", "hard_profit", "anchor_assets",
        "anchor_asset_ratio", "net_profit_margin", "eps_calculated",
        "selling_to_gross", "admin_to_gross", "selling_admin_to_gross",
        "rd_to_gross", "sga_rd_to_gross", "finance_to_gross", "advance_to_revenue",
        "debt_ratio_ex_advance", "debt_equity_ex_cash"
    ],
}


def supabase_query(sql):
    """Execute SQL on Supabase via exec_sql RPC."""
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
        headers={
            "Authorization": f"Bearer {SERVICE_KEY}",
            "apikey": SERVICE_KEY,
            "Content-Type": "application/json"
        },
        json={"sql": sql},
        timeout=120
    )
    if resp.status_code != 200:
        print(f"  ERROR: HTTP {resp.status_code}: {resp.text[:300]}")
        print(f"  SQL: {sql[:300]}")
    resp.raise_for_status()
    return resp.json()


def sync_table(table_name, columns, batch_size=BATCH_SIZE):
    """Sync a table from Supabase to local PostgreSQL."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Get total count
    result = supabase_query(
        f"SELECT row_to_json(t) FROM (SELECT count(*) as cnt FROM {table_name}) t"
    )
    total = result[0]["cnt"]
    print(f"\n=== {table_name}: {total} rows ===")

    col_list = ", ".join(columns)
    pk_col = columns[0]

    # Truncate (except companies - upsert)
    if table_name != "companies":
        cur.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")

    offset = 0
    inserted = 0

    while offset < total:
        sql = (
            f"SELECT row_to_json(t) FROM ("
            f"SELECT {col_list} FROM {table_name} "
            f"ORDER BY {pk_col} "
            f"LIMIT {batch_size} OFFSET {offset}"
            f") t"
        )
        rows = supabase_query(sql)  # PostgREST unwraps JSON -> array of dicts

        if not rows:
            break

        if table_name == "companies":
            for row in rows:
                cur.execute(
                    f"INSERT INTO {table_name} ({col_list}) "
                    f"VALUES ({', '.join(['%s'] * len(columns))}) "
                    f"ON CONFLICT (id) DO UPDATE SET "
                    + ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != "id"),
                    [row.get(c) for c in columns]
                )
        else:
            psycopg2.extras.execute_values(
                cur,
                f"INSERT INTO {table_name} ({col_list}) VALUES %s",
                [[row.get(c) for c in columns] for row in rows],
                page_size=1000
            )

        inserted += len(rows)
        offset += batch_size
        print(f"  {inserted}/{total}")
        conn.commit()

    conn.commit()
    cur.close()
    conn.close()
    print(f"  ✅ {table_name}: {inserted} rows synced")


if __name__ == "__main__":
    for table, columns in TABLES.items():
        try:
            sync_table(table, columns)
        except Exception as e:
            print(f"  ❌ {table} failed: {e}")
            import traceback
            traceback.print_exc()