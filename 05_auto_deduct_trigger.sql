-- ═══════════════════════════════════════════════════════════════
--  05_auto_deduct_trigger.sql
--  Operational Inventory Tracking — Real-Time Stock Deduction Engine
--
--  Business Context:
--    Whenever operational goods are issued to departments (e.g.,
--    Housekeeping requisitions for Amenities or Chemicals), the system
--    must automatically decrement `qty_on_hand` in `inventory_stock`
--    to maintain real-time physical-to-digital inventory parity and
--    prevent negative stock conditions.
--
--  Components:
--    1. Function & Trigger on transactions (Header validation & audit)
--    2. Function & Trigger on transaction_lines (Line-item stock deduction & batch tracking)
--    3. Strict stock level validations (Negative stock prevention)
-- ═══════════════════════════════════════════════════════════════

-- Safety cleanup
DROP TRIGGER IF EXISTS trg_auto_deduct_stock ON transactions CASCADE;
DROP TRIGGER IF EXISTS trg_auto_deduct_stock ON transaction_lines CASCADE;
DROP FUNCTION IF EXISTS fn_auto_deduct_stock() CASCADE;
DROP FUNCTION IF EXISTS fn_auto_deduct_stock_header() CASCADE;


-- ─────────────────────────────────────────────────────────────
--  1. Header Validation Trigger on `transactions`
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION fn_auto_deduct_stock_header()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure warehouse_id is specified for all stock-out ISSUE operations
    IF NEW.txn_type = 'ISSUE' THEN
        IF NEW.warehouse_id IS NULL THEN
            RAISE EXCEPTION 'Constraint Violation: Warehouse ID cannot be null for ISSUE transactions (Ref: %).', 
                COALESCE(NEW.reference_no, 'N/A');
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auto_deduct_stock
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION fn_auto_deduct_stock_header();


-- ─────────────────────────────────────────────────────────────
--  2. Line Item Auto-Deduction Trigger on `transaction_lines`
-- ─────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION fn_auto_deduct_stock()
RETURNS TRIGGER AS $$
DECLARE
    v_txn_type        VARCHAR(20);
    v_warehouse_id    INT;
    v_target_stock_id BIGINT;
    v_current_stock   INT;
BEGIN
    -- Retrieve parent transaction metadata (txn_type and warehouse_id)
    SELECT txn_type, warehouse_id 
    INTO v_txn_type, v_warehouse_id
    FROM transactions 
    WHERE txn_id = NEW.txn_id;

    -- Only deduct stock for department ISSUE transactions
    IF v_txn_type = 'ISSUE' THEN
        -- Locate the exact inventory stock row:
        -- 1. Match specific batch_no if specified by requisition
        -- 2. Otherwise apply FEFO/FIFO (earliest expiry date, lowest stock_id)
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
        FOR UPDATE; -- Lock stock row during deduction to prevent race conditions

        -- Validation 1: Ensure inventory item exists in the specified warehouse
        IF v_target_stock_id IS NULL THEN
            RAISE EXCEPTION 'Inventory Error: Item ID % is not registered or stocked in Warehouse ID % (Batch: %).', 
                NEW.item_id, v_warehouse_id, COALESCE(NEW.batch_no, 'ANY');
        END IF;

        -- Validation 2: Prevent negative stock (CHECK constraint compliance)
        IF v_current_stock < NEW.quantity THEN
            RAISE EXCEPTION 'Stock Depletion Breach: Insufficient stock for Item ID % in Warehouse ID %. Available: %, Requested: %.',
                NEW.item_id, v_warehouse_id, v_current_stock, NEW.quantity;
        END IF;

        -- Decrement physical stock on hand
        UPDATE inventory_stock
        SET qty_on_hand = qty_on_hand - NEW.quantity,
            updated_at = CURRENT_TIMESTAMP
        WHERE stock_id = v_target_stock_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_auto_deduct_stock
AFTER INSERT ON transaction_lines
FOR EACH ROW
EXECUTE FUNCTION fn_auto_deduct_stock();


-- ─────────────────────────────────────────────────────────────
--  Verification Query
-- ─────────────────────────────────────────────────────────────
-- Verify registered triggers:
-- SELECT trigger_name, event_object_table, action_timing, event_manipulation 
-- FROM information_schema.triggers 
-- WHERE trigger_name = 'trg_auto_deduct_stock'
-- ORDER BY event_object_table;
