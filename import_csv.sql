-- ═══════════════════════════════════════════════════════════════
--  import_csv.sql
--  Bulk Import dari CSV ke PostgreSQL menggunakan \COPY
--
--  PENTING — Urutan Import (FK Dependency):
--  ┌───────────────────────────────────────────────────────────┐
--  │  Layer 0 (no FK)  : locations, suppliers, item_categories │
--  │  Layer 1 (1 FK)   : items, warehouses, users              │
--  │  Layer 2 (2 FK)   : item_suppliers, inventory_stock       │
--  │  Layer 3 (3-4 FK) : transactions                          │
--  │  Layer 4 (2 FK)   : transaction_lines                     │
--  └───────────────────────────────────────────────────────────┘
--
--  Cara Pakai:
--  1. Pastikan PostgreSQL sudah running & database sudah dibuat
--  2. Jalankan schema DDL terlebih dahulu:
--       psql -U <user> -d <dbname> -f schema_ddl.sql
--  3. Sesuaikan path CSV di bawah, lalu jalankan file ini:
--       psql -U <user> -d <dbname> -f import_csv.sql
--
--  CATATAN: Gunakan \COPY (client-side) bukan COPY (server-side)
--           agar tidak perlu superuser privilege.
-- ═══════════════════════════════════════════════════════════════

-- Atur path folder CSV Anda di sini:
-- (Ganti sesuai lokasi aktual di laptop Anda)
\set csv_dir 'C:/Users/jeckly/Documents/antigravity/cool-pascal/mock_data'


-- ─────────────────────────────────────────────────────────────
--  LAYER 0: Root Tables (tidak ada FK dependency)
-- ─────────────────────────────────────────────────────────────

\echo '>>> Importing locations...'
\COPY locations(location_id, location_name, location_type, address, city, country, created_at)
FROM :'csv_dir'/01_locations.csv
WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\echo '>>> Importing suppliers...'
\COPY suppliers(supplier_id, supplier_name, contact_person, phone, email, address, city, country, lead_time_days, is_active, created_at)
FROM :'csv_dir'/02_suppliers.csv
WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\echo '>>> Importing item_categories...'
-- Catatan: Seed data sudah di-INSERT di schema_ddl.sql.
-- Hapus INSERT di DDL jika ingin import dari CSV, ATAU skip langkah ini.
-- Uncomment baris berikut jika DDL TIDAK berisi INSERT seed:
-- \COPY item_categories(category_id, category_name, description)
-- FROM :'csv_dir'/03_item_categories.csv
-- WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
\echo '    (skipped — seed data already in DDL)'


-- ─────────────────────────────────────────────────────────────
--  LAYER 1: Tables with 1 FK dependency
-- ─────────────────────────────────────────────────────────────

\echo '>>> Importing items...'
\COPY items(item_id, category_id, item_code, item_name, brand, purchase_uom, usage_uom, conversion_factor, unit_cost, selling_price, reorder_point, is_hazardous, is_active, created_at, updated_at)
FROM :'csv_dir'/04_items.csv
WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\echo '>>> Importing warehouses...'
\COPY warehouses(warehouse_id, location_id, warehouse_name, zone, created_at)
FROM :'csv_dir'/06_warehouses.csv
WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\echo '>>> Importing users...'
\COPY users(user_id, full_name, role, location_id, is_active, created_at)
FROM :'csv_dir'/07_users.csv
WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');


-- ─────────────────────────────────────────────────────────────
--  LAYER 2: Tables with 2 FK dependencies
-- ─────────────────────────────────────────────────────────────

\echo '>>> Importing item_suppliers...'
\COPY item_suppliers(item_supplier_id, item_id, supplier_id, last_purchase_price, last_supply_date, is_preferred)
FROM :'csv_dir'/05_item_suppliers.csv
WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');

\echo '>>> Importing inventory_stock...'
\COPY inventory_stock(stock_id, item_id, warehouse_id, batch_no, qty_on_hand, qty_reserved, expiry_date, rack_location, last_counted, updated_at)
FROM :'csv_dir'/08_inventory_stock.csv
WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');


-- ─────────────────────────────────────────────────────────────
--  LAYER 3: Tables with 3–4 FK dependencies
-- ─────────────────────────────────────────────────────────────

\echo '>>> Importing transactions...'
\COPY transactions(txn_id, txn_type, location_id, warehouse_id, supplier_id, user_id, reference_no, department_requestor, txn_date, remarks, created_at)
FROM :'csv_dir'/09_transactions.csv
WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');


-- ─────────────────────────────────────────────────────────────
--  LAYER 4: Tables with FK to transactions
-- ─────────────────────────────────────────────────────────────

\echo '>>> Importing transaction_lines...'
\COPY transaction_lines(line_id, txn_id, item_id, quantity, uom, unit_price, batch_no, expiry_date, room_number, remarks)
FROM :'csv_dir'/10_transaction_lines.csv
WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');


-- ─────────────────────────────────────────────────────────────
--  RESET SEQUENCES (agar auto-increment lanjut dari ID terbesar)
-- ─────────────────────────────────────────────────────────────

\echo '>>> Resetting sequences...'
SELECT setval('locations_location_id_seq',         (SELECT COALESCE(MAX(location_id), 1)       FROM locations));
SELECT setval('suppliers_supplier_id_seq',         (SELECT COALESCE(MAX(supplier_id), 1)       FROM suppliers));
SELECT setval('item_categories_category_id_seq',   (SELECT COALESCE(MAX(category_id), 1)       FROM item_categories));
SELECT setval('items_item_id_seq',                 (SELECT COALESCE(MAX(item_id), 1)           FROM items));
SELECT setval('item_suppliers_item_supplier_id_seq',(SELECT COALESCE(MAX(item_supplier_id), 1) FROM item_suppliers));
SELECT setval('warehouses_warehouse_id_seq',       (SELECT COALESCE(MAX(warehouse_id), 1)      FROM warehouses));
SELECT setval('users_user_id_seq',                 (SELECT COALESCE(MAX(user_id), 1)           FROM users));
SELECT setval('inventory_stock_stock_id_seq',      (SELECT COALESCE(MAX(stock_id), 1)          FROM inventory_stock));
SELECT setval('transactions_txn_id_seq',           (SELECT COALESCE(MAX(txn_id), 1)            FROM transactions));
SELECT setval('transaction_lines_line_id_seq',     (SELECT COALESCE(MAX(line_id), 1)           FROM transaction_lines));


-- ─────────────────────────────────────────────────────────────
--  VERIFIKASI: Hitung baris per tabel
-- ─────────────────────────────────────────────────────────────

\echo ''
\echo '══════════════════════════════════════════════'
\echo '  IMPORT VERIFICATION — Row Counts'
\echo '══════════════════════════════════════════════'

SELECT 'locations'         AS table_name, COUNT(*) AS row_count FROM locations
UNION ALL
SELECT 'suppliers',                       COUNT(*)              FROM suppliers
UNION ALL
SELECT 'item_categories',                 COUNT(*)              FROM item_categories
UNION ALL
SELECT 'items',                           COUNT(*)              FROM items
UNION ALL
SELECT 'item_suppliers',                  COUNT(*)              FROM item_suppliers
UNION ALL
SELECT 'warehouses',                      COUNT(*)              FROM warehouses
UNION ALL
SELECT 'users',                           COUNT(*)              FROM users
UNION ALL
SELECT 'inventory_stock',                 COUNT(*)              FROM inventory_stock
UNION ALL
SELECT 'transactions',                    COUNT(*)              FROM transactions
UNION ALL
SELECT 'transaction_lines',              COUNT(*)              FROM transaction_lines
ORDER BY table_name;
