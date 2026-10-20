-- ═══════════════════════════════════════════════════════════════
--  05_reconciliation.sql
--  Operational Inventory Tracking — Monthly Physical Stock Opname & Reconciliation
--
--  Business Context:
--    At the end of every calendar month, hotel warehouse personnel conduct
--    a mandatory physical inventory count (stock opname). Discrepancies between
--    physical stock and the digital ledger indicate operational shrinkage,
--    unrecorded breakages, or administrative theft.
--
--  Components:
--    1. Table: physical_counts (Audit trail for physical inventory audits)
--    2. Sample Data: Realistic month-end physical counts (exact matches & variances)
--    3. Stored Procedure: sp_reconcile_physical_inventory(p_audit_date DATE)
--       - Reconciles physical count vs digital inventory_stock
--       - Quantifies monetary discrepancy based on items.unit_cost
--       - Automatically logs variances into audit_logs (flag: 'STOCK_DISCREPANCY')
--       - Synchronizes inventory_stock.qty_on_hand to physical reality
-- ═══════════════════════════════════════════════════════════════

-- Safety cleanup
DROP PROCEDURE IF EXISTS sp_reconcile_physical_inventory(DATE);
DROP TABLE IF EXISTS physical_counts CASCADE;


-- ─────────────────────────────────────────────────────────────
--  1. Table: physical_counts
-- ─────────────────────────────────────────────────────────────
CREATE TABLE physical_counts (
    count_id              BIGSERIAL      PRIMARY KEY,
    count_date            DATE           NOT NULL,
    warehouse_id          INT            NOT NULL REFERENCES warehouses(warehouse_id),
    item_id               INT            NOT NULL REFERENCES items(item_id),
    batch_no              VARCHAR(50),
    system_qty            INT            DEFAULT 0,
    physical_qty          INT            NOT NULL CHECK (physical_qty >= 0),
    discrepancy_qty       INT            DEFAULT 0,
    discrepancy_value     NUMERIC(12,2)  DEFAULT 0.00,
    reconciliation_status VARCHAR(20)    DEFAULT 'PENDING'
                                         CHECK (reconciliation_status IN ('PENDING', 'RECONCILED', 'FLAGGED')),
    counted_by            INT            REFERENCES users(user_id),
    verified_by           INT            REFERENCES users(user_id),
    remarks               TEXT,
    created_at            TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    reconciled_at         TIMESTAMP
);

-- Performance Indexes
CREATE INDEX idx_phys_count_date   ON physical_counts(count_date);
CREATE INDEX idx_phys_warehouse    ON physical_counts(warehouse_id);
CREATE INDEX idx_phys_item         ON physical_counts(item_id);
CREATE INDEX idx_phys_status       ON physical_counts(reconciliation_status);


-- ─────────────────────────────────────────────────────────────
--  2. Ingest Sample Physical Count Data (End-of-Month Audit)
-- ─────────────────────────────────────────────────────────────
-- Audit Date: 2026-09-30
-- Counter: Claudia Zimmermann (User ID: 3, warehouse_staff)
-- Verifier: Erika Hartmann (User ID: 1, admin / internal auditor)

INSERT INTO physical_counts (
    count_date, warehouse_id, item_id, batch_no, physical_qty, counted_by, verified_by, remarks
) VALUES
    -- Berlin Main Store (Warehouse 1)
    ('2026-09-30', 1, 20, 'B2604-050',  56, 3, 1, 'Observed 8 leaking cartons in lower rack A-02'),
    ('2026-09-30', 1, 14, 'B2608-001',  92, 3, 1, '11 vanity kits unverified shrinkage during housekeeping dispatch'),
    ('2026-09-30', 1, 25, 'B2607-039', 407, 3, 1, '25 cans dented / damaged during restock transport'),
    ('2026-09-30', 1, 32, 'B2604-028', 209, 3, 1, 'Perfect count parity with shelf tag'),
    ('2026-09-30', 1,  8, 'B2607-020', 386, 3, 1, 'Zero variance - razor kits sealed pallet'),
    ('2026-09-30', 1, 36, 'B2606-033', 110, 3, 1, '13 units missing from open snack bin'),
    ('2026-09-30', 1,  7, 'B2608-050',  33, 3, 1, 'Verified full physical match'),

    -- Berlin Chemical Room (Warehouse 2)
    ('2026-09-30', 2, 17, 'B2607-032', 362, 3, 1, '25 canisters punctured / hazardous waste disposal initiated'),
    ('2026-09-30', 2, 16, 'B2607-017', 473, 3, 1, 'Glass cleaners perfectly verified'),
    ('2026-09-30', 2, 22, 'B2604-005', 245, 3, 1, '18 units unaccounted spillage in chemical decanting zone'),
    ('2026-09-30', 2, 19, 'B2609-010', 102, 3, 1, 'Sanitizer lot verified against manufacturer pack'),

    -- München Main Store (Warehouse 3)
    ('2026-09-30', 3, 14, 'B2608-021', 350, 3, 1, '33 vanity packs missing from unmonitored floor cart'),
    ('2026-09-30', 3, 38, 'B2606-014', 425, 3, 1, '26 bottles broken during pallet unloading'),
    ('2026-09-30', 3,  6, 'B2608-003', 286, 3, 1, 'Exact count match on shower caps');


-- ─────────────────────────────────────────────────────────────
--  3. Stored Procedure: sp_reconcile_physical_inventory
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE PROCEDURE sp_reconcile_physical_inventory(p_audit_date DATE)
LANGUAGE plpgsql
AS $$
DECLARE
    r RECORD;
    v_current_qty       INT;
    v_diff_qty          INT;
    v_unit_cost         NUMERIC(12,2);
    v_exposure          NUMERIC(12,2);
    v_severity          VARCHAR(15);
    v_wh_name           VARCHAR(80);
    v_item_name         VARCHAR(120);
    v_target_stock_id   BIGINT;
    v_processed_count   INT := 0;
    v_discrepancy_count INT := 0;
    v_total_exposure    NUMERIC(12,2) := 0.00;
BEGIN
    RAISE NOTICE '═══════════════════════════════════════════════════════════════';
    RAISE NOTICE 'Initiating Stock Opname Reconciliation for Audit Date: %', p_audit_date;
    RAISE NOTICE '═══════════════════════════════════════════════════════════════';

    -- Iterate over pending physical counts matching target audit date
    FOR r IN 
        SELECT 
            pc.count_id,
            pc.warehouse_id,
            pc.item_id,
            pc.batch_no,
            pc.physical_qty,
            pc.counted_by,
            pc.verified_by,
            pc.remarks,
            w.warehouse_name,
            i.item_code,
            i.item_name,
            COALESCE(i.unit_cost, 0.00) AS unit_cost
        FROM physical_counts pc
        JOIN warehouses w ON pc.warehouse_id = w.warehouse_id
        JOIN items i ON pc.item_id = i.item_id
        WHERE pc.count_date = p_audit_date
          AND pc.reconciliation_status = 'PENDING'
        ORDER BY pc.warehouse_id, pc.item_id
    LOOP
        -- Retrieve the exact stock record from inventory_stock
        SELECT s.stock_id, s.qty_on_hand
        INTO v_target_stock_id, v_current_qty
        FROM inventory_stock s
        WHERE s.warehouse_id = r.warehouse_id
          AND s.item_id = r.item_id
          AND (r.batch_no IS NULL OR s.batch_no = r.batch_no OR s.batch_no IS NULL)
        ORDER BY 
          CASE WHEN r.batch_no IS NOT NULL AND s.batch_no = r.batch_no THEN 0 ELSE 1 END,
          s.expiry_date ASC NULLS LAST,
          s.stock_id ASC
        LIMIT 1
        FOR UPDATE;

        IF v_target_stock_id IS NULL THEN
            RAISE WARNING 'Stock record missing for Item % (%) in Warehouse %', 
                r.item_code, r.item_name, r.warehouse_name;
            CONTINUE;
        END IF;

        -- Variance Calculation: physical minus digital system
        -- Negative variance indicates physical inventory shrinkage / damage
        v_diff_qty := r.physical_qty - v_current_qty;
        v_exposure := ROUND(ABS(v_diff_qty) * r.unit_cost, 2);

        -- Determine Forensic Severity Level based on fiscal impact and volume
        IF v_exposure >= 100.00 OR ABS(v_diff_qty) >= 50 THEN
            v_severity := 'CRITICAL';
        ELSIF v_exposure >= 50.00 OR ABS(v_diff_qty) >= 20 THEN
            v_severity := 'HIGH';
        ELSIF v_exposure >= 15.00 OR ABS(v_diff_qty) >= 5 THEN
            v_severity := 'MEDIUM';
        ELSE
            v_severity := 'LOW';
        END IF;

        -- If variance detected, log forensic incident into audit_logs
        IF v_diff_qty <> 0 THEN
            INSERT INTO audit_logs (
                transaction_id,
                item_id,
                flag_type,
                discrepancy_amount,
                discrepancy_unit,
                severity_level,
                details,
                log_timestamp
            ) VALUES (
                NULL,
                r.item_id,
                'STOCK_DISCREPANCY',
                ABS(v_diff_qty),
                'UNITS',
                v_severity,
                FORMAT('Stock Opname Reconciliation (%s) at %s. Item: %s (%s, Batch %s). System: %s, Physical: %s, Variance: %s units (Loss: €%s). Inspector: User %s, Verifier: User %s. Notes: %s',
                       p_audit_date, r.warehouse_name, r.item_code, r.item_name, COALESCE(r.batch_no, 'N/A'),
                       v_current_qty, r.physical_qty, v_diff_qty, v_exposure, r.counted_by, r.verified_by, r.remarks),
                CURRENT_TIMESTAMP
            );

            v_discrepancy_count := v_discrepancy_count + 1;
            v_total_exposure    := v_total_exposure + v_exposure;

            RAISE NOTICE '  [VARIANCE FLAGGED] % | System: % -> Physical: % | Diff: % units (€%) | Severity: %', 
                RPAD(r.item_name, 25), v_current_qty, r.physical_qty, v_diff_qty, v_exposure, v_severity;
        ELSE
            RAISE NOTICE '  [COUNT MATCHED]    % | Qty: % | Zero Variance', 
                RPAD(r.item_name, 25), r.physical_qty;
        END IF;

        -- Synchronize digital inventory_stock to true physical reality
        UPDATE inventory_stock
        SET qty_on_hand = r.physical_qty,
            last_counted = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE stock_id = v_target_stock_id;

        -- Finalize physical_counts audit entry
        UPDATE physical_counts
        SET system_qty            = v_current_qty,
            discrepancy_qty       = v_diff_qty,
            discrepancy_value     = v_exposure,
            reconciliation_status = 'RECONCILED',
            reconciled_at         = CURRENT_TIMESTAMP
        WHERE count_id = r.count_id;

        v_processed_count := v_processed_count + 1;
    END LOOP;

    RAISE NOTICE '═══════════════════════════════════════════════════════════════';
    RAISE NOTICE 'Reconciliation Completed Successfully:';
    RAISE NOTICE '  - Total Items Audited     : %', v_processed_count;
    RAISE NOTICE '  - Variances Intercepted   : %', v_discrepancy_count;
    RAISE NOTICE '  - Total Capital Exposure  : €%', v_total_exposure;
    RAISE NOTICE '═══════════════════════════════════════════════════════════════';
END;
$$;


-- ─────────────────────────────────────────────────────────────
--  4. Execute Month-End Reconciliation Procedure
-- ─────────────────────────────────────────────────────────────
CALL sp_reconcile_physical_inventory('2026-09-30');


-- ─────────────────────────────────────────────────────────────
--  5. Verification Queries
-- ─────────────────────────────────────────────────────────────
-- SELECT * FROM physical_counts ORDER BY count_id;
-- SELECT * FROM v_audit_summary WHERE flag_type = 'STOCK_DISCREPANCY';
