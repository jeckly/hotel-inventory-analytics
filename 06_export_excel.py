"""
06_export_excel.py
==================
Operational Inventory Tracking — Executive Audit & Stock Reconciliation Exporter
Automated reporting tool generating a multi-sheet, executive-ready Excel workbook
from PostgreSQL database (inventory_db) into reports/Executive_Audit_Report.xlsx.

Sheets Included:
  1. Executive Summary & KPIs (v_audit_summary + macro KPI cards)
  2. Critical Forensic Logs (Top 50 high-severity anomalies from audit_logs)
  3. Stock Opname Reconciliation (Physical count audits from physical_counts)
"""

import os
import psycopg2
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Database Configuration
DB_HOST = os.getenv("PGHOST", "localhost")
DB_PORT = int(os.getenv("PGPORT", "5432"))
DB_USER = os.getenv("PGUSER", "postgres")
DB_PASS = os.getenv("PGPASSWORD", "postgres")
TARGET_DB = "inventory_db"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
OUTPUT_PATH = os.path.join(REPORTS_DIR, "Executive_Audit_Report.xlsx")


def get_db_connection():
    """Establish connection to PostgreSQL database."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=TARGET_DB,
    )


def create_executive_report():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    conn = get_db_connection()
    cur = conn.cursor()

    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # ═════════════════════════════════════════════════════════════
    #  Global Color Palette & Fonts
    # ═════════════════════════════════════════════════════════════
    font_title = Font(name="Calibri", size=16, bold=True, color="1B365D")
    font_subtitle = Font(name="Calibri", size=10, italic=True, color="595959")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_kpi_label = Font(name="Calibri", size=9, bold=True, color="595959")
    font_kpi_val = Font(name="Calibri", size=16, bold=True, color="1B365D")
    font_data = Font(name="Calibri", size=10, color="000000")
    font_data_bold = Font(name="Calibri", size=10, bold=True, color="000000")
    font_total = Font(name="Calibri", size=11, bold=True, color="1B365D")

    # Severity Fonts & Fills
    fill_crit = PatternFill("solid", fgColor="FADBD8")
    font_crit = Font(name="Calibri", size=10, bold=True, color="78281F")
    fill_high = PatternFill("solid", fgColor="FCF3CF")
    font_high = Font(name="Calibri", size=10, bold=True, color="7D6608")
    fill_med = PatternFill("solid", fgColor="E8F8F5")
    font_med = Font(name="Calibri", size=10, bold=True, color="117864")

    # Status Fills
    fill_reconciled = PatternFill("solid", fgColor="D4EFDF")
    font_reconciled = Font(name="Calibri", size=10, bold=True, color="196F3D")

    # Fills
    fill_navy = PatternFill("solid", fgColor="1B365D")
    fill_navy_sub = PatternFill("solid", fgColor="2C5E8A")
    fill_zebra_even = PatternFill("solid", fgColor="F9FAFB")
    fill_zebra_odd = PatternFill("solid", fgColor="FFFFFF")
    fill_kpi = PatternFill("solid", fgColor="F0F4F8")
    fill_total = PatternFill("solid", fgColor="E4ECF4")

    # Borders
    border_thin = Side(border_style="thin", color="D9D9D9")
    cell_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)
    border_total = Border(
        left=border_thin, right=border_thin,
        top=Side(border_style="thin", color="1B365D"),
        bottom=Side(border_style="double", color="1B365D")
    )
    border_kpi = Border(
        left=Side(border_style="medium", color="1B365D"),
        right=border_thin, top=border_thin, bottom=border_thin
    )

    # Alignments
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    align_header = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Number Formats
    FMT_CURRENCY = '€#,##0.00'
    FMT_QTY = '#,##0'
    FMT_PERCENT = '0.0%'
    FMT_DATE = 'YYYY-MM-DD'
    FMT_DATETIME = 'YYYY-MM-DD HH:MM:SS'

    # ─────────────────────────────────────────────────────────────
    #  SHEET 1: Executive Summary & Anomaly Analytics
    # ─────────────────────────────────────────────────────────────
    ws1 = wb.create_sheet(title="1_Executive_Summary")
    ws1.views.sheetView[0].showGridLines = True

    # Title Header
    ws1["A1"] = "🏨 MULTI-FACILITY FORENSIC AUDIT & INVENTORY CONTROL REPORT"
    ws1["A1"].font = font_title
    ws1["A2"] = f"Executive Intelligence Dossier — Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Target: Grand Hotel Berlin, München, Frankfurt, Hamburg"
    ws1["A2"].font = font_subtitle

    # Fetch Summary Data
    cur.execute("""
        SELECT 
            flag_type,
            severity_level,
            total_incidents,
            total_discrepancy_units,
            estimated_financial_impact_eur,
            first_incident_date,
            latest_incident_date
        FROM v_audit_summary
        ORDER BY estimated_financial_impact_eur DESC;
    """)
    summary_rows = cur.fetchall()

    # Calculate Macro Totals for KPI Cards
    total_incidents = sum(r[2] for r in summary_rows)
    total_units = sum(r[3] for r in summary_rows)
    total_loss = sum(r[4] for r in summary_rows)
    critical_incidents = sum(r[2] for r in summary_rows if r[1] == 'CRITICAL')

    # KPI Block (Rows 4-5)
    kpis = [
        ("TOTAL VERIFIED INCIDENTS", f"{total_incidents:,}", "B4:C5"),
        ("UNITS DISCREPANCY", f"{int(total_units):,} Units", "D4:E5"),
        ("TOTAL AT-RISK CAPITAL", f"€{total_loss:,.2f}", "F4:G5"),
        ("CRITICAL THREAT CASES", f"{critical_incidents:,} Incidents", "H4:H5"),
    ]

    ws1.row_dimensions[4].height = 18
    ws1.row_dimensions[5].height = 28

    # Table Header (Row 7)
    headers_s1 = [
        "No", "Anomaly Flag Type", "Severity", "Total Incidents",
        "Discrepancy (Units)", "Fiscal Exposure (€)", "% of Total Loss",
        "Earliest Detection", "Latest Detection"
    ]
    ws1.row_dimensions[7].height = 28
    for col_idx, header in enumerate(headers_s1, start=1):
        cell = ws1.cell(row=7, column=col_idx, value=header)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_header
        cell.border = cell_border

    # Table Body
    curr_row = 8
    for idx, r in enumerate(summary_rows, start=1):
        ws1.row_dimensions[curr_row].height = 22
        pct_loss = float(r[4]) / float(total_loss) if total_loss else 0.0
        row_fill = fill_zebra_even if idx % 2 == 0 else fill_zebra_odd

        # Values
        ws1.cell(row=curr_row, column=1, value=idx).alignment = align_center
        ws1.cell(row=curr_row, column=2, value=r[0]).alignment = align_left
        
        # Severity pill
        sev_cell = ws1.cell(row=curr_row, column=3, value=r[1])
        sev_cell.alignment = align_center
        if r[1] == 'CRITICAL':
            sev_cell.fill = fill_crit
            sev_cell.font = font_crit
        elif r[1] == 'HIGH':
            sev_cell.fill = fill_high
            sev_cell.font = font_high
        else:
            sev_cell.fill = fill_med
            sev_cell.font = font_med

        # Metrics
        c_inc = ws1.cell(row=curr_row, column=4, value=r[2])
        c_inc.number_format = FMT_QTY
        c_inc.alignment = align_right

        c_qty = ws1.cell(row=curr_row, column=5, value=r[3])
        c_qty.number_format = FMT_QTY
        c_qty.alignment = align_right

        c_val = ws1.cell(row=curr_row, column=6, value=float(r[4]))
        c_val.number_format = FMT_CURRENCY
        c_val.alignment = align_right

        c_pct = ws1.cell(row=curr_row, column=7, value=pct_loss)
        c_pct.number_format = FMT_PERCENT
        c_pct.alignment = align_right

        c_d1 = ws1.cell(row=curr_row, column=8, value=r[5].strftime('%Y-%m-%d') if r[5] else "-")
        c_d1.alignment = align_center

        c_d2 = ws1.cell(row=curr_row, column=9, value=r[6].strftime('%Y-%m-%d') if r[6] else "-")
        c_d2.alignment = align_center

        for col_idx in range(1, 10):
            c = ws1.cell(row=curr_row, column=col_idx)
            c.border = cell_border
            if col_idx != 3:
                c.fill = row_fill
                c.font = font_data

        curr_row += 1

    # Total Row
    ws1.row_dimensions[curr_row].height = 24
    ws1.cell(row=curr_row, column=1, value="")
    ws1.cell(row=curr_row, column=2, value="TOTAL FORENSIC AUDIT IMPACT").alignment = align_left
    ws1.cell(row=curr_row, column=3, value="")
    
    c_tot_inc = ws1.cell(row=curr_row, column=4, value=total_incidents)
    c_tot_inc.number_format = FMT_QTY
    c_tot_inc.alignment = align_right

    c_tot_qty = ws1.cell(row=curr_row, column=5, value=total_units)
    c_tot_qty.number_format = FMT_QTY
    c_tot_qty.alignment = align_right

    c_tot_val = ws1.cell(row=curr_row, column=6, value=float(total_loss))
    c_tot_val.number_format = FMT_CURRENCY
    c_tot_val.alignment = align_right

    c_tot_pct = ws1.cell(row=curr_row, column=7, value=1.0)
    c_tot_pct.number_format = FMT_PERCENT
    c_tot_pct.alignment = align_right

    ws1.cell(row=curr_row, column=8, value="")
    ws1.cell(row=curr_row, column=9, value="")

    for col_idx in range(1, 10):
        c = ws1.cell(row=curr_row, column=col_idx)
        c.fill = fill_total
        c.font = font_total
        c.border = border_total

    # Add KPI cards in header region
    card_cols = [2, 4, 6, 8]
    card_data = [
        ("TOTAL VERIFIED INCIDENTS", f"{total_incidents:,}"),
        ("UNITS DISCREPANCY", f"{int(total_units):,}"),
        ("TOTAL MONETARY LOSS", f"€{total_loss:,.2f}"),
        ("CRITICAL ANOMALIES", f"{critical_incidents:,}"),
    ]
    for c_idx, (label, val) in zip(card_cols, card_data):
        c_lbl = ws1.cell(row=4, column=c_idx, value=label)
        c_lbl.font = font_kpi_label
        c_lbl.fill = fill_kpi
        c_lbl.alignment = align_center

        c_v = ws1.cell(row=5, column=c_idx, value=val)
        c_v.font = font_kpi_val
        c_v.fill = fill_kpi
        c_v.alignment = align_center

        # Borders
        for r_kpi in (4, 5):
            ws1.cell(row=r_kpi, column=c_idx).border = cell_border


    # ─────────────────────────────────────────────────────────────
    #  SHEET 2: Top 50 Critical Anomaly Logs
    # ─────────────────────────────────────────────────────────────
    ws2 = wb.create_sheet(title="2_Critical_Incident_Logs")
    ws2.views.sheetView[0].showGridLines = True

    ws2["A1"] = "🚨 TOP 50 CRITICAL & HIGH-SEVERITY INCIDENT AUDIT TRAIL"
    ws2["A1"].font = font_title
    ws2["A2"] = "Real-time records intercepted by database trigger trg_audit_anomaly_check & physical stock opname procedures"
    ws2["A2"].font = font_subtitle

    headers_s2 = [
        "Log ID", "Incident Timestamp", "Flag Type", "Severity", "Item Code",
        "Item Name", "Category", "Discrepancy (Units)", "Financial Loss (€)",
        "Department / Source", "Forensic Investigation Notes"
    ]
    ws2.row_dimensions[4].height = 28
    for col_idx, header in enumerate(headers_s2, start=1):
        cell = ws2.cell(row=4, column=col_idx, value=header)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_header
        cell.border = cell_border

    cur.execute("""
        SELECT 
            al.log_id,
            al.log_timestamp,
            al.flag_type,
            al.severity_level,
            COALESCE(i.item_code, 'N/A') AS item_code,
            COALESCE(i.item_name, 'General Transaction') AS item_name,
            COALESCE(c.category_name, 'Operational') AS category_name,
            al.discrepancy_amount,
            ROUND(al.discrepancy_amount * COALESCE(tl.unit_price, i.unit_cost, 0), 2) AS estimated_loss,
            COALESCE(t.department_requestor, 'Physical Stock Opname') AS department_requestor,
            al.details
        FROM audit_logs al
        LEFT JOIN items i ON al.item_id = i.item_id
        LEFT JOIN item_categories c ON i.category_id = c.category_id
        LEFT JOIN transactions t ON al.transaction_id = t.txn_id
        LEFT JOIN transaction_lines tl ON al.transaction_id = tl.txn_id AND al.item_id = tl.item_id
        ORDER BY 
            CASE al.severity_level 
                WHEN 'CRITICAL' THEN 1 
                WHEN 'HIGH' THEN 2 
                WHEN 'MEDIUM' THEN 3 
                ELSE 4 
            END,
            al.log_timestamp DESC,
            al.discrepancy_amount DESC
        LIMIT 50;
    """)
    log_rows = cur.fetchall()

    curr_row = 5
    for idx, r in enumerate(log_rows, start=1):
        ws2.row_dimensions[curr_row].height = 20
        row_fill = fill_zebra_even if idx % 2 == 0 else fill_zebra_odd

        ws2.cell(row=curr_row, column=1, value=r[0]).alignment = align_center
        
        c_ts = ws2.cell(row=curr_row, column=2, value=r[1].strftime('%Y-%m-%d %H:%M'))
        c_ts.alignment = align_center

        ws2.cell(row=curr_row, column=3, value=r[2]).alignment = align_left

        # Severity
        sev_cell = ws2.cell(row=curr_row, column=4, value=r[3])
        sev_cell.alignment = align_center
        if r[3] == 'CRITICAL':
            sev_cell.fill = fill_crit
            sev_cell.font = font_crit
        elif r[3] == 'HIGH':
            sev_cell.fill = fill_high
            sev_cell.font = font_high
        else:
            sev_cell.fill = fill_med
            sev_cell.font = font_med

        ws2.cell(row=curr_row, column=5, value=r[4]).alignment = align_center
        ws2.cell(row=curr_row, column=6, value=r[5]).alignment = align_left
        ws2.cell(row=curr_row, column=7, value=r[6]).alignment = align_left

        c_u = ws2.cell(row=curr_row, column=8, value=r[7])
        c_u.number_format = FMT_QTY
        c_u.alignment = align_right

        c_loss = ws2.cell(row=curr_row, column=9, value=float(r[8]))
        c_loss.number_format = FMT_CURRENCY
        c_loss.alignment = align_right

        ws2.cell(row=curr_row, column=10, value=r[9]).alignment = align_left
        ws2.cell(row=curr_row, column=11, value=r[10]).alignment = align_left

        for col_idx in range(1, 12):
            c = ws2.cell(row=curr_row, column=col_idx)
            c.border = cell_border
            if col_idx != 4:
                c.fill = row_fill
                c.font = font_data

        curr_row += 1


    # ─────────────────────────────────────────────────────────────
    #  SHEET 3: Physical Stock Opname Reconciliation Results
    # ─────────────────────────────────────────────────────────────
    ws3 = wb.create_sheet(title="3_Stock_Reconciliation")
    ws3.views.sheetView[0].showGridLines = True

    ws3["A1"] = "📋 MONTH-END PHYSICAL STOCK OPNAME AUDIT & RECONCILIATION"
    ws3["A1"].font = font_title
    ws3["A2"] = "Automated discrepancy verification executed via Stored Procedure sp_reconcile_physical_inventory"
    ws3["A2"].font = font_subtitle

    headers_s3 = [
        "Audit ID", "Count Date", "Warehouse Name", "Item Code", "Item Name",
        "Batch No", "System Qty", "Physical Qty", "Variance (Units)", "Unit Cost (€)",
        "Variance Value (€)", "Status", "Audited By", "Verified By", "Field Inspector Remarks"
    ]
    ws3.row_dimensions[4].height = 28
    for col_idx, header in enumerate(headers_s3, start=1):
        cell = ws3.cell(row=4, column=col_idx, value=header)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_header
        cell.border = cell_border

    cur.execute("""
        SELECT 
            pc.count_id,
            pc.count_date,
            w.warehouse_name,
            i.item_code,
            i.item_name,
            COALESCE(pc.batch_no, 'ANY') AS batch_no,
            pc.system_qty,
            pc.physical_qty,
            pc.discrepancy_qty,
            i.unit_cost,
            pc.discrepancy_value,
            pc.reconciliation_status,
            COALESCE(u1.full_name, 'Staff ID ' || pc.counted_by) AS counter_name,
            COALESCE(u2.full_name, 'Auditor ID ' || pc.verified_by) AS verifier_name,
            pc.remarks
        FROM physical_counts pc
        JOIN warehouses w ON pc.warehouse_id = w.warehouse_id
        JOIN items i ON pc.item_id = i.item_id
        LEFT JOIN users u1 ON pc.counted_by = u1.user_id
        LEFT JOIN users u2 ON pc.verified_by = u2.user_id
        ORDER BY pc.count_id;
    """)
    recon_rows = cur.fetchall()

    curr_row = 5
    tot_recon_system = 0
    tot_recon_phys = 0
    tot_recon_var_qty = 0
    tot_recon_var_val = 0.0

    for idx, r in enumerate(recon_rows, start=1):
        ws3.row_dimensions[curr_row].height = 20
        row_fill = fill_zebra_even if idx % 2 == 0 else fill_zebra_odd

        tot_recon_system += r[6]
        tot_recon_phys += r[7]
        tot_recon_var_qty += r[8]
        tot_recon_var_val += float(r[10])

        ws3.cell(row=curr_row, column=1, value=r[0]).alignment = align_center
        ws3.cell(row=curr_row, column=2, value=r[1].strftime('%Y-%m-%d')).alignment = align_center
        ws3.cell(row=curr_row, column=3, value=r[2]).alignment = align_left
        ws3.cell(row=curr_row, column=4, value=r[3]).alignment = align_center
        ws3.cell(row=curr_row, column=5, value=r[4]).alignment = align_left
        ws3.cell(row=curr_row, column=6, value=r[5]).alignment = align_center

        c_sq = ws3.cell(row=curr_row, column=7, value=r[6])
        c_sq.number_format = FMT_QTY
        c_sq.alignment = align_right

        c_pq = ws3.cell(row=curr_row, column=8, value=r[7])
        c_pq.number_format = FMT_QTY
        c_pq.alignment = align_right

        # Variance units (highlight red if negative)
        c_vq = ws3.cell(row=curr_row, column=9, value=r[8])
        c_vq.number_format = FMT_QTY
        c_vq.alignment = align_right
        if r[8] < 0:
            c_vq.font = Font(name="Calibri", size=10, bold=True, color="C0392B")

        c_uc = ws3.cell(row=curr_row, column=10, value=float(r[9]))
        c_uc.number_format = FMT_CURRENCY
        c_uc.alignment = align_right

        c_vv = ws3.cell(row=curr_row, column=11, value=float(r[10]))
        c_vv.number_format = FMT_CURRENCY
        c_vv.alignment = align_right
        if float(r[10]) > 0:
            c_vv.font = Font(name="Calibri", size=10, bold=True, color="C0392B")

        # Status
        c_st = ws3.cell(row=curr_row, column=12, value=r[11])
        c_st.alignment = align_center
        c_st.fill = fill_reconciled
        c_st.font = font_reconciled

        ws3.cell(row=curr_row, column=13, value=r[12]).alignment = align_left
        ws3.cell(row=curr_row, column=14, value=r[13]).alignment = align_left
        ws3.cell(row=curr_row, column=15, value=r[14]).alignment = align_left

        for col_idx in range(1, 16):
            c = ws3.cell(row=curr_row, column=col_idx)
            c.border = cell_border
            if col_idx != 12:
                c.fill = row_fill
                if col_idx not in (9, 11):
                    c.font = font_data

        curr_row += 1

    # Total Row for Sheet 3
    ws3.row_dimensions[curr_row].height = 24
    ws3.cell(row=curr_row, column=1, value="")
    ws3.cell(row=curr_row, column=2, value="")
    ws3.cell(row=curr_row, column=3, value="TOTAL OPNAME AUDIT").alignment = align_left
    ws3.cell(row=curr_row, column=4, value="")
    ws3.cell(row=curr_row, column=5, value="")
    ws3.cell(row=curr_row, column=6, value="")

    c_tot_sq = ws3.cell(row=curr_row, column=7, value=tot_recon_system)
    c_tot_sq.number_format = FMT_QTY
    c_tot_sq.alignment = align_right

    c_tot_pq = ws3.cell(row=curr_row, column=8, value=tot_recon_phys)
    c_tot_pq.number_format = FMT_QTY
    c_tot_pq.alignment = align_right

    c_tot_vq = ws3.cell(row=curr_row, column=9, value=tot_recon_var_qty)
    c_tot_vq.number_format = FMT_QTY
    c_tot_vq.alignment = align_right

    ws3.cell(row=curr_row, column=10, value="")

    c_tot_vv = ws3.cell(row=curr_row, column=11, value=tot_recon_var_val)
    c_tot_vv.number_format = FMT_CURRENCY
    c_tot_vv.alignment = align_right

    ws3.cell(row=curr_row, column=12, value="")
    ws3.cell(row=curr_row, column=13, value="")
    ws3.cell(row=curr_row, column=14, value="")
    ws3.cell(row=curr_row, column=15, value="")

    for col_idx in range(1, 16):
        c = ws3.cell(row=curr_row, column=col_idx)
        c.fill = fill_total
        c.font = font_total
        c.border = border_total


    # ─────────────────────────────────────────────────────────────
    #  Auto-fit column widths across all sheets
    # ─────────────────────────────────────────────────────────────
    for ws in [ws1, ws2, ws3]:
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                # Skip title rows and empty cells
                if cell.row in (1, 2, 4, 5) and ws == ws1:
                    continue
                if cell.row in (1, 2) and ws in (ws2, ws3):
                    continue
                if cell.value is not None:
                    s_val = str(cell.value)
                    if len(s_val) > max_len:
                        max_len = len(s_val)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # Specific column adjustments for readability
    ws1.column_dimensions['A'].width = 6
    ws1.column_dimensions['B'].width = 30
    ws1.column_dimensions['F'].width = 24
    ws1.column_dimensions['G'].width = 16

    ws2.column_dimensions['A'].width = 10
    ws2.column_dimensions['B'].width = 20
    ws2.column_dimensions['C'].width = 24
    ws2.column_dimensions['F'].width = 28
    ws2.column_dimensions['K'].width = 60

    ws3.column_dimensions['A'].width = 10
    ws3.column_dimensions['C'].width = 24
    ws3.column_dimensions['E'].width = 28
    ws3.column_dimensions['O'].width = 50

    wb.save(OUTPUT_PATH)
    print(f"[SUCCESS] Executive Audit Report generated successfully at:\n  {OUTPUT_PATH}")

    conn.close()


if __name__ == "__main__":
    create_executive_report()
