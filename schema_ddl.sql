-- ═══════════════════════════════════════════════════════════════
--  schema_ddl.sql
--  Sistem Pelacakan Inventaris Operasional — PostgreSQL DDL v2
--  10 tabel | 14 foreign keys | 7 CHECK constraints
--
--  Urutan tabel mengikuti dependency graph (parent → child):
--    1. locations
--    2. suppliers
--    3. item_categories
--    4. items              (FK → item_categories)
--    5. item_suppliers     (FK → items, suppliers)
--    6. warehouses         (FK → locations)
--    7. users              (FK → locations)
--    8. inventory_stock    (FK → items, warehouses)
--    9. transactions       (FK → locations, warehouses, suppliers, users)
--   10. transaction_lines  (FK → transactions, items)
-- ═══════════════════════════════════════════════════════════════

-- Safety: drop in reverse dependency order if re-creating
DROP TABLE IF EXISTS transaction_lines CASCADE;
DROP TABLE IF EXISTS transactions      CASCADE;
DROP TABLE IF EXISTS inventory_stock   CASCADE;
DROP TABLE IF EXISTS users             CASCADE;
DROP TABLE IF EXISTS warehouses        CASCADE;
DROP TABLE IF EXISTS item_suppliers    CASCADE;
DROP TABLE IF EXISTS items             CASCADE;
DROP TABLE IF EXISTS item_categories   CASCADE;
DROP TABLE IF EXISTS suppliers         CASCADE;
DROP TABLE IF EXISTS locations         CASCADE;


-- ─────────────────────────────────────────────────────────────
--  1. locations — Lokasi Operasional (Hotel / Pabrik)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE locations (
    location_id   SERIAL        PRIMARY KEY,
    location_name VARCHAR(100)  NOT NULL,
    location_type VARCHAR(20)   NOT NULL
                  CHECK (location_type IN ('hotel', 'factory', 'warehouse')),
    address       TEXT,
    city          VARCHAR(60),
    country       VARCHAR(60)   DEFAULT 'Germany',
    created_at    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);


-- ─────────────────────────────────────────────────────────────
--  2. suppliers — Master Supplier
-- ─────────────────────────────────────────────────────────────
CREATE TABLE suppliers (
    supplier_id    SERIAL        PRIMARY KEY,
    supplier_name  VARCHAR(100)  NOT NULL,
    contact_person VARCHAR(80),
    phone          VARCHAR(30),
    email          VARCHAR(120),
    address        TEXT,
    city           VARCHAR(60),
    country        VARCHAR(60)   DEFAULT 'Germany',
    lead_time_days SMALLINT      DEFAULT 0,
    is_active      BOOLEAN       DEFAULT TRUE,
    created_at     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);


-- ─────────────────────────────────────────────────────────────
--  3. item_categories — Kategori Barang
-- ─────────────────────────────────────────────────────────────
CREATE TABLE item_categories (
    category_id   SMALLSERIAL   PRIMARY KEY,
    category_name VARCHAR(50)   NOT NULL UNIQUE,
    description   TEXT
);

INSERT INTO item_categories (category_name, description) VALUES
    ('Amenities',  'Perlengkapan tamu: sabun, shampoo, sikat gigi, dll.'),
    ('Chemicals',  'Bahan kimia: disinfektan, pembersih lantai, dll.'),
    ('Minibar',    'Produk minibar: snack, minuman, bir, dll.');


-- ─────────────────────────────────────────────────────────────
--  4. items — Master Barang
-- ─────────────────────────────────────────────────────────────
CREATE TABLE items (
    item_id           SERIAL         PRIMARY KEY,
    category_id       SMALLINT       NOT NULL REFERENCES item_categories(category_id),
    item_code         VARCHAR(30)    NOT NULL UNIQUE,
    item_name         VARCHAR(120)   NOT NULL,
    brand             VARCHAR(80),
    purchase_uom      VARCHAR(20)    NOT NULL,
    usage_uom         VARCHAR(20)    NOT NULL,
    conversion_factor NUMERIC(10,2)  NOT NULL DEFAULT 1,
    unit_cost         NUMERIC(12,2)  DEFAULT 0,
    selling_price     NUMERIC(12,2),
    reorder_point     INT            DEFAULT 0,
    is_hazardous      BOOLEAN        DEFAULT FALSE,
    is_active         BOOLEAN        DEFAULT TRUE,
    created_at        TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_items_category ON items(category_id);
CREATE INDEX idx_items_code     ON items(item_code);


-- ─────────────────────────────────────────────────────────────
--  5. item_suppliers — Relasi Item ↔ Supplier (Many-to-Many)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE item_suppliers (
    item_supplier_id  SERIAL         PRIMARY KEY,
    item_id           INT            NOT NULL REFERENCES items(item_id),
    supplier_id       INT            NOT NULL REFERENCES suppliers(supplier_id),
    last_purchase_price NUMERIC(12,2),
    last_supply_date  DATE,
    is_preferred      BOOLEAN        DEFAULT FALSE,

    UNIQUE (item_id, supplier_id)
);

CREATE INDEX idx_is_item     ON item_suppliers(item_id);
CREATE INDEX idx_is_supplier ON item_suppliers(supplier_id);


-- ─────────────────────────────────────────────────────────────
--  6. warehouses — Gudang / Area Penyimpanan
-- ─────────────────────────────────────────────────────────────
CREATE TABLE warehouses (
    warehouse_id   SERIAL       PRIMARY KEY,
    location_id    INT          NOT NULL REFERENCES locations(location_id),
    warehouse_name VARCHAR(80)  NOT NULL,
    zone           VARCHAR(40),
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_warehouses_location ON warehouses(location_id);


-- ─────────────────────────────────────────────────────────────
--  7. users — Pengguna Sistem
-- ─────────────────────────────────────────────────────────────
CREATE TABLE users (
    user_id     SERIAL       PRIMARY KEY,
    full_name   VARCHAR(100) NOT NULL,
    role        VARCHAR(30)  NOT NULL
                CHECK (role IN (
                    'admin', 'procurement', 'warehouse_staff',
                    'housekeeping', 'front_desk', 'manager'
                )),
    location_id INT          REFERENCES locations(location_id),
    is_active   BOOLEAN      DEFAULT TRUE,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);


-- ─────────────────────────────────────────────────────────────
--  8. inventory_stock — Stok Real-Time per Gudang
-- ─────────────────────────────────────────────────────────────
CREATE TABLE inventory_stock (
    stock_id      BIGSERIAL     PRIMARY KEY,
    item_id       INT           NOT NULL REFERENCES items(item_id),
    warehouse_id  INT           NOT NULL REFERENCES warehouses(warehouse_id),
    batch_no      VARCHAR(50),
    qty_on_hand   INT           NOT NULL DEFAULT 0 CHECK (qty_on_hand >= 0),
    qty_reserved  INT           NOT NULL DEFAULT 0 CHECK (qty_reserved >= 0),
    expiry_date   DATE,
    rack_location VARCHAR(30),
    last_counted  TIMESTAMP,
    updated_at    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (item_id, warehouse_id, batch_no)
);

CREATE INDEX idx_stock_item      ON inventory_stock(item_id);
CREATE INDEX idx_stock_warehouse ON inventory_stock(warehouse_id);
CREATE INDEX idx_stock_expiry    ON inventory_stock(expiry_date);
CREATE INDEX idx_stock_rack      ON inventory_stock(rack_location);


-- ─────────────────────────────────────────────────────────────
--  9. transactions — Header Transaksi (7 tipe)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE transactions (
    txn_id                BIGSERIAL     PRIMARY KEY,
    txn_type              VARCHAR(20)   NOT NULL
                          CHECK (txn_type IN (
                              'RECEIVING',
                              'ISSUE',
                              'RETURN',
                              'TRANSFER',
                              'ADJUSTMENT',
                              'SPOILAGE_DAMAGE',
                              'MINIBAR_SALE'
                          )),
    location_id           INT           NOT NULL REFERENCES locations(location_id),
    warehouse_id          INT           REFERENCES warehouses(warehouse_id),
    supplier_id           INT           REFERENCES suppliers(supplier_id),
    user_id               INT           NOT NULL REFERENCES users(user_id),
    reference_no          VARCHAR(50),
    department_requestor  VARCHAR(40),
    txn_date              TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    remarks               TEXT,
    created_at            TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_txn_type       ON transactions(txn_type);
CREATE INDEX idx_txn_date       ON transactions(txn_date);
CREATE INDEX idx_txn_location   ON transactions(location_id);
CREATE INDEX idx_txn_supplier   ON transactions(supplier_id);
CREATE INDEX idx_txn_user       ON transactions(user_id);
CREATE INDEX idx_txn_department ON transactions(department_requestor);


-- ─────────────────────────────────────────────────────────────
--  10. transaction_lines — Detail Baris Transaksi
-- ─────────────────────────────────────────────────────────────
CREATE TABLE transaction_lines (
    line_id      BIGSERIAL      PRIMARY KEY,
    txn_id       BIGINT         NOT NULL REFERENCES transactions(txn_id) ON DELETE CASCADE,
    item_id      INT            NOT NULL REFERENCES items(item_id),
    quantity     INT            NOT NULL CHECK (quantity > 0),
    uom          VARCHAR(20)    NOT NULL,
    unit_price   NUMERIC(12,2)  DEFAULT 0,
    batch_no     VARCHAR(50),
    expiry_date  DATE,
    room_number  VARCHAR(10),
    remarks      TEXT
);

CREATE INDEX idx_txnlines_txn  ON transaction_lines(txn_id);
CREATE INDEX idx_txnlines_item ON transaction_lines(item_id);
CREATE INDEX idx_txnlines_room ON transaction_lines(room_number);


-- ═══════════════════════════════════════════════════════════════
--  VERIFICATION: List all tables and their row counts
-- ═══════════════════════════════════════════════════════════════
-- Run after data import:
-- SELECT schemaname, tablename
-- FROM   pg_tables
-- WHERE  schemaname = 'public'
-- ORDER  BY tablename;
