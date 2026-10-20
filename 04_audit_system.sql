-- ═══════════════════════════════════════════════════════════════
--  04_audit_system.sql
--  Operational Inventory Tracking — Forensic Audit Logging System
--
--  Defines:
--    1. Table: audit_logs (tracks anomalies, shrinkages, and hoarding)
--    2. Indexes: Performance optimization for audit queries
--    3. Population Procedure: Ingest historical anomaly flags
--    4. Trigger: Real-time anomaly detection for future transactions
--    5. Reporting View: Executive audit summary view
-- ═══════════════════════════════════════════════════════════════

-- Safety cleanup
DROP VIEW IF EXISTS v_audit_summary CASCADE;
DROP TRIGGER IF EXISTS trg_audit_anomaly_check ON transactions CASCADE;
DROP FUNCTION IF EXISTS fn_audit_anomaly_detector() CASCADE;
DROP TABLE IF EXISTS audit_logs CASCADE;


-- ─────────────────────────────────────────────────────────────
--  1. Table: audit_logs
-- ─────────────────────────────────────────────────────────────
CREATE TABLE audit_logs (
    log_id              BIGSERIAL      PRIMARY KEY,
    transaction_id      BIGINT         REFERENCES transactions(txn_id) ON DELETE SET NULL,
    item_id             INT            REFERENCES items(item_id) ON DELETE SET NULL,
    flag_type           VARCHAR(30)    NOT NULL 
                                       CHECK (flag_type IN (
                                           'PHANTOM_RETURN',      -- Return logged but inventory missing
                                           'HOARDING_ALERT',      -- Month-end unusual bulk requisitions
                                           'STOCK_DISCREPANCY',   -- Variance during physical count opname
                                           'SAFETY_STOCK_BREACH'  -- Stock plummeted past critical threshold
                                       )),
    discrepancy_amount  NUMERIC(12,2)  NOT NULL, -- Discrepancy volume or financial exposure
    discrepancy_unit    VARCHAR(20)    DEFAULT 'UNITS', -- 'UNITS' or 'EUR'
    severity_level      VARCHAR(15)    DEFAULT 'HIGH'
                                       CHECK (severity_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    details             TEXT,          -- Forensic investigation notes
    log_timestamp       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX idx_audit_flag_type    ON audit_logs(flag_type);
CREATE INDEX idx_audit_txn_id       ON audit_logs(transaction_id);
CREATE INDEX idx_audit_item_id      ON audit_logs(item_id);
CREATE INDEX idx_audit_timestamp    ON audit_logs(log_timestamp);
CREATE INDEX idx_audit_severity     ON audit_logs(severity_level);


-- ─────────────────────────────────────────────────────────────
--  2. Populate Historical Audit Logs from Database
-- ─────────────────────────────────────────────────────────────

-- 2A. Ingest PHANTOM_RETURN Anomalies (11 Verified Minibar Shrinkage Cases)
INSERT INTO audit_logs (transaction_id, item_id, flag_type, discrepancy_amount, discrepancy_unit, severity_level, details, log_timestamp)
SELECT 
    t.txn_id,
    tl.item_id,
    'PHANTOM_RETURN',
    tl.quantity,
    'UNITS',
    'CRITICAL',
    FORMAT('Minibar return claimed under ref %s at %s. Physical restock verification failed: stock missing.', 
           t.reference_no, l.location_name),
    t.txn_date
FROM transactions t
JOIN transaction_lines tl ON t.txn_id = tl.txn_id
JOIN items i ON tl.item_id = i.item_id
JOIN locations l ON t.location_id = l.location_id
WHERE t.txn_type = 'RETURN' 
  AND i.category_id = 3 -- Minibar
  AND t.txn_id IN (19, 110, 207, 256, 303, 390, 400, 473, 532, 541, 591);


-- 2B. Ingest HOARDING_ALERT Anomalies (Requisitions on Days 28-31 with high quantity)
INSERT INTO audit_logs (transaction_id, item_id, flag_type, discrepancy_amount, discrepancy_unit, severity_level, details, log_timestamp)
SELECT 
    t.txn_id,
    tl.item_id,
    'HOARDING_ALERT',
    tl.quantity,
    'UNITS',
    CASE 
        WHEN tl.quantity >= 60 THEN 'HIGH'
        ELSE 'MEDIUM'
    END,
    FORMAT('End-of-month budget flush detected. Department: %s requested %s units (line value €%s) on day %s.', 
           t.department_requestor, tl.quantity, ROUND(tl.quantity * tl.unit_price, 2), EXTRACT(DAY FROM t.txn_date)::INT),
    t.txn_date
FROM transactions t
JOIN transaction_lines tl ON t.txn_id = tl.txn_id
WHERE t.txn_type = 'ISSUE' 
  AND EXTRACT(DAY FROM t.txn_date) >= 28
  AND tl.quantity >= 30; -- Threshold for abnormal bulk extraction


-- ─────────────────────────────────────────────────────────────
--  3. Automated Real-Time Anomaly Detection Trigger
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION fn_audit_anomaly_detector()
RETURNS TRIGGER AS $$
BEGIN
    -- Real-time Detection 1: Flag month-end hoarding during INSERT
    IF NEW.txn_type = 'ISSUE' AND EXTRACT(DAY FROM NEW.txn_date) >= 28 THEN
        INSERT INTO audit_logs (transaction_id, flag_type, discrepancy_amount, discrepancy_unit, severity_level, details, log_timestamp)
        VALUES (
            NEW.txn_id,
            'HOARDING_ALERT',
            0, -- Will be updated or itemized via line triggers
            'UNITS',
            'HIGH',
            FORMAT('Real-time alert: Department %s initiated month-end requisition ref %s.', NEW.department_requestor, NEW.reference_no),
            NEW.txn_date
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_anomaly_check
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION fn_audit_anomaly_detector();


-- ─────────────────────────────────────────────────────────────
--  4. Reporting View: Executive Audit Summary
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW v_audit_summary AS
SELECT 
    al.flag_type,
    al.severity_level,
    COUNT(*) AS total_incidents,
    SUM(al.discrepancy_amount) AS total_discrepancy_units,
    ROUND(SUM(al.discrepancy_amount * COALESCE(tl.unit_price, i.unit_cost, 0)), 2) AS estimated_financial_impact_eur,
    MIN(al.log_timestamp)::DATE AS first_incident_date,
    MAX(al.log_timestamp)::DATE AS latest_incident_date
FROM audit_logs al
LEFT JOIN transaction_lines tl ON al.transaction_id = tl.txn_id AND al.item_id = tl.item_id
LEFT JOIN items i ON al.item_id = i.item_id
GROUP BY al.flag_type, al.severity_level
ORDER BY total_incidents DESC;


-- ─────────────────────────────────────────────────────────────
--  5. Automated Inventory Stock Deduction Trigger (v2.1)
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION fn_auto_deduct_stock_header()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.txn_type = 'ISSUE' AND NEW.warehouse_id IS NULL THEN
        RAISE EXCEPTION 'Constraint Violation: Warehouse ID cannot be null for ISSUE transactions (Ref: %).', 
            COALESCE(NEW.reference_no, 'N/A');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_auto_deduct_stock ON transactions CASCADE;
CREATE TRIGGER trg_auto_deduct_stock
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION fn_auto_deduct_stock_header();


CREATE OR REPLACE FUNCTION fn_auto_deduct_stock()
RETURNS TRIGGER AS $$
DECLARE
    v_txn_type        VARCHAR(20);
    v_warehouse_id    INT;
    v_target_stock_id BIGINT;
    v_current_stock   INT;
BEGIN
    SELECT txn_type, warehouse_id 
    INTO v_txn_type, v_warehouse_id
    FROM transactions 
    WHERE txn_id = NEW.txn_id;

    IF v_txn_type = 'ISSUE' THEN
        SELECT stock_id, qty_on_hand
        INTO v_target_stock_id, v_current_stock
        FROM inventory_stock
        WHERE item_id = NEW.item_id 
          AND warehouse_id = v_warehouse_id
          AND (NEW.batch_no IS NULL OR batch_no = NEW.batch_no OR batch_no IS NULL)
        ORDER BY 
          CASE WHEN NEW.batch_no IS NOT NULL AND batch_no = NEW.batch_no THEN 0 ELSE 1 END,
          expiry_date ASC NULLS LAST,
          stock_id ASC
        LIMIT 1
        FOR UPDATE;

        IF v_target_stock_id IS NULL THEN
            RAISE EXCEPTION 'Inventory Error: Item ID % is not registered or stocked in Warehouse ID % (Batch: %).', 
                NEW.item_id, v_warehouse_id, COALESCE(NEW.batch_no, 'ANY');
        END IF;

        IF v_current_stock < NEW.quantity THEN
            RAISE EXCEPTION 'Stock Depletion Breach: Insufficient stock for Item ID % in Warehouse ID %. Available: %, Requested: %.',
                NEW.item_id, v_warehouse_id, v_current_stock, NEW.quantity;
        END IF;

        UPDATE inventory_stock
        SET qty_on_hand = qty_on_hand - NEW.quantity,
            updated_at = CURRENT_TIMESTAMP
        WHERE stock_id = v_target_stock_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_auto_deduct_stock ON transaction_lines CASCADE;
CREATE TRIGGER trg_auto_deduct_stock
AFTER INSERT ON transaction_lines
FOR EACH ROW
EXECUTE FUNCTION fn_auto_deduct_stock();


-- ─────────────────────────────────────────────────────────────
--  Verification Query
-- ─────────────────────────────────────────────────────────────
-- Run after execution:
-- SELECT * FROM v_audit_summary;
-- SELECT trigger_name, event_object_table FROM information_schema.triggers WHERE trigger_name = 'trg_auto_deduct_stock';
