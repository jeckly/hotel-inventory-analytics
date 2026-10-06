"""
setup_and_import_postgres.py
============================
Automated Database Setup & Bulk CSV Import to PostgreSQL
1. Creates 'inventory_db' if it doesn't exist.
2. Applies 'schema_ddl.sql' (10 tables, PK, FK, CHECK constraints, indexes).
3. Bulk imports all 10 CSVs into tables in dependency order.
4. Resets auto-increment sequences.
5. Verifies and prints table row counts.
"""

import os
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pandas as pd

DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = int(os.getenv("PGPORT", "5432"))
DB_USER = os.getenv("PGUSER", "postgres")
DB_PASS = os.getenv("PGPASSWORD", "postgres")
TARGET_DB = "inventory_db"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIR = os.path.join(BASE_DIR, "mock_data")
DDL_PATH = os.path.join(BASE_DIR, "schema_ddl.sql")


def wait_and_connect_server():
    """Attempt connecting to the default postgres database."""
    print(f"Connecting to PostgreSQL server at {DB_HOST}:{DB_PORT} as '{DB_USER}'...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn


def create_database(server_conn):
    """Ensure target database exists."""
    with server_conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TARGET_DB,))
        exists = cur.fetchone()
        if not exists:
            print(f"Creating database '{TARGET_DB}'...")
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TARGET_DB)))
            print(f"[OK] Database '{TARGET_DB}' created.")
        else:
            print(f"[OK] Database '{TARGET_DB}' already exists.")


def apply_ddl(conn):
    """Run schema_ddl.sql on target database."""
    print("Applying schema_ddl.sql...")
    with open(DDL_PATH, "r", encoding="utf-8") as f:
        ddl_sql = f.read()
    with conn.cursor() as cur:
        cur.execute(ddl_sql)
    conn.commit()
    print("[OK] Schema created successfully.")


def import_csv_data(conn):
    """Import CSV data into tables using COPY in dependency order."""
    import_plan = [
        ("locations",         "01_locations.csv"),
        ("suppliers",         "02_suppliers.csv"),
        # item_categories is already seeded in DDL
        ("items",             "04_items.csv"),
        ("warehouses",        "06_warehouses.csv"),
        ("users",             "07_users.csv"),
        ("item_suppliers",    "05_item_suppliers.csv"),
        ("inventory_stock",   "08_inventory_stock.csv"),
        ("transactions",      "09_transactions.csv"),
        ("transaction_lines", "10_transaction_lines.csv"),
    ]

    print("\nImporting CSV files into PostgreSQL...")
    with conn.cursor() as cur:
        for table, filename in import_plan:
            filepath = os.path.join(CSV_DIR, filename)
            if not os.path.exists(filepath):
                print(f"[WARN] File {filepath} not found, skipping.")
                continue

            # Read CSV header to get column list
            df_sample = pd.read_csv(filepath, nrows=1)
            columns = list(df_sample.columns)
            cols_clause = ", ".join(columns)

            with open(filepath, "r", encoding="utf-8") as f:
                copy_query = f"COPY {table} ({cols_clause}) FROM STDIN WITH (FORMAT csv, HEADER true, ENCODING 'utf-8')"
                cur.copy_expert(copy_query, f)
            print(f"  [OK] Imported {filename:<26s} -> {table}")

        # Reset sequences
        seq_resets = [
            ("locations", "location_id", "locations_location_id_seq"),
            ("suppliers", "supplier_id", "suppliers_supplier_id_seq"),
            ("item_categories", "category_id", "item_categories_category_id_seq"),
            ("items", "item_id", "items_item_id_seq"),
            ("item_suppliers", "item_supplier_id", "item_suppliers_item_supplier_id_seq"),
            ("warehouses", "warehouse_id", "warehouses_warehouse_id_seq"),
            ("users", "user_id", "users_user_id_seq"),
            ("inventory_stock", "stock_id", "inventory_stock_stock_id_seq"),
            ("transactions", "txn_id", "transactions_txn_id_seq"),
            ("transaction_lines", "line_id", "transaction_lines_line_id_seq"),
        ]
        for tbl, col, seq in seq_resets:
            cur.execute(f"SELECT setval('{seq}', (SELECT COALESCE(MAX({col}), 1) FROM {tbl}));")

    conn.commit()
    print("[OK] All tables imported and sequences reset.")


def verify_tables(conn):
    """Print count of rows in all tables."""
    tables = [
        "locations", "suppliers", "item_categories", "items",
        "item_suppliers", "warehouses", "users",
        "inventory_stock", "transactions", "transaction_lines",
    ]
    print("\n" + "=" * 50)
    print("  VERIFIKASI ROW COUNT DI POSTGRESQL")
    print("=" * 50)
    with conn.cursor() as cur:
        for tbl in tables:
            cur.execute(f"SELECT COUNT(*) FROM {tbl};")
            count = cur.fetchone()[0]
            print(f"  {tbl:<22s} : {count:>6,} baris")
    print("=" * 50)


def main():
    server_conn = wait_and_connect_server()
    create_database(server_conn)
    server_conn.close()

    db_conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=TARGET_DB,
    )
    apply_ddl(db_conn)
    import_csv_data(db_conn)
    verify_tables(db_conn)
    db_conn.close()
    print("\n[SUCCESS] Setup dan import database PostgreSQL selesai 100%!")


if __name__ == "__main__":
    main()
