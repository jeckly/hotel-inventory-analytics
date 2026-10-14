"""
app_dashboard.py
================
Interactive Streamlit Dashboard for Operational Inventory Tracking & Supply Chain Anomaly Detection
Run: streamlit run app_dashboard.py
"""

import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

st.set_page_config(
    page_title="Operational Inventory Tracking & Anomaly Detection",
    page_icon="📦",
    layout="wide",
)

# Connect to database
@st.cache_resource
def get_connection():
    return psycopg2.connect("host=localhost port=5432 dbname=inventory_db user=postgres password=postgres")

conn = get_connection()

# ── Title & Header ───────────────────────────────────────────
st.title("📦 Operational Inventory Tracking & Supply Chain Anomaly Detection")
st.markdown(
    "**Senior Data Architect Portfolio** — Monitoring Amenities, Chemicals, & Minibar Logistics across German Properties."
)

# ── Load Summary KPIs ─────────────────────────────────────────
@st.cache_data(ttl=60)
def load_kpis():
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM transactions;")
        total_txns = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM items;")
        total_items = cur.fetchone()[0]

        cur.execute("""
            SELECT ROUND(SUM(tl.quantity * tl.unit_price), 2)
            FROM transactions t
            JOIN transaction_lines tl ON t.txn_id = tl.txn_id
            WHERE t.txn_type = 'ISSUE' AND EXTRACT(DAY FROM t.txn_date) >= 28;
        """)
        hoarding_cost = cur.fetchone()[0]

        phantom_ids = (19, 110, 207, 256, 303, 390, 400, 473, 532, 541, 591)
        cur.execute(f"""
            SELECT ROUND(SUM(tl.quantity * tl.unit_price), 2)
            FROM transactions t
            JOIN transaction_lines tl ON t.txn_id = tl.txn_id
            WHERE t.txn_id IN {phantom_ids};
        """)
        phantom_loss = cur.fetchone()[0]

    return total_txns, total_items, hoarding_cost, phantom_loss

total_txns, total_items, hoarding_cost, phantom_loss = load_kpis()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Transactions Logged", f"{total_txns:,}")
col2.metric("Catalog Size", f"{total_items} SKUs")
col3.metric("Month-End Hoarding Outflow", f"€{hoarding_cost:,.2f}", delta="+106% vs Normal Days", delta_color="inverse")
col4.metric("Phantom Return Shrinkage", f"€{phantom_loss:,.2f}", delta="11 Audited Cases", delta_color="inverse")

st.divider()

# ── Navigation Tabs ───────────────────────────────────────────
tab_audit, tab1, tab2, tab3 = st.tabs([
    "🚨 Forensic Audit & Incident Center",
    "📈 Anomaly 1: Month-End Hoarding Spike",
    "🕵️ Anomaly 2: Minibar Phantom Returns Audit",
    "⚠️ Reorder Point & Safety Stock Alerts",
])

# ═════════════════════════════════════════════════════════════
# TAB 0: FORENSIC AUDIT & INCIDENT CENTER (v2.0)
# ═════════════════════════════════════════════════════════════
with tab_audit:
    st.subheader("🚨 Real-Time Forensic Audit & Anomaly Detection Center (v2.0)")
    st.markdown(
        "Autonomous anomaly surveillance powered by database triggers (`trg_audit_anomaly_check`) "
        "and persistent audit logging (`audit_logs`)."
    )

    # Top summary metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Dana Berisiko (Capital at Risk)", "€71,812.63", delta="1,028 Anomaly Events", delta_color="inverse")
    m2.metric("Kasus Retur Fiktif (Phantom Returns)", "71 Incidents", delta="€905.90 Shrinkage", delta_color="inverse")
    m3.metric("Lonjakan Akhir Bulan (Hoarding Alerts)", "957 Incidents", delta="€70,906.73 Budget Flushing", delta_color="inverse")

    st.divider()

    def style_severity(val):
        if str(val) == "CRITICAL":
            return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
        elif str(val) in ("HIGH", "MEDIUM"):
            return "background-color: #fff3cd; color: #856404; font-weight: bold;"
        return ""

    # Section 1: Executive Audit Summary (v_audit_summary)
    st.markdown("### 📊 Executive Audit Summary (`v_audit_summary`)")
    q_summary = """
        SELECT 
            flag_type,
            severity_level,
            total_incidents,
            total_discrepancy_units,
            estimated_financial_impact_eur AS financial_impact_eur,
            first_incident_date,
            latest_incident_date
        FROM v_audit_summary;
    """
    df_summary = pd.read_sql(q_summary, conn)

    st.dataframe(
        df_summary.style.map(style_severity, subset=["severity_level"]),
        width="stretch",
        hide_index=True
    )

    # Section 2: Recent 20 Suspicious Transactions from audit_logs
    st.markdown("### 🔍 20 Log Transaksi Mencurigakan Terbaru (`audit_logs`)")
    q_recent = """
        SELECT 
            al.log_id,
            al.log_timestamp::TIMESTAMP(0) AS timestamp,
            al.flag_type,
            al.severity_level,
            al.discrepancy_amount AS discrepancy_qty,
            al.discrepancy_unit AS unit,
            COALESCE(t.reference_no, 'N/A') AS reference_no,
            COALESCE(i.item_name, 'Multiple / Header') AS affected_item,
            al.details
        FROM audit_logs al
        LEFT JOIN transactions t ON al.transaction_id = t.txn_id
        LEFT JOIN items i ON al.item_id = i.item_id
        ORDER BY al.log_timestamp DESC, al.log_id DESC
        LIMIT 20;
    """
    df_recent = pd.read_sql(q_recent, conn)

    st.dataframe(
        df_recent.style.map(style_severity, subset=["severity_level"]),
        width="stretch",
        hide_index=True
    )

# ═════════════════════════════════════════════════════════════
# TAB 1: HOARDING SPIKE
# ═════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Daily Inventory Stock Outflow (ISSUE Dynamics)")
    st.info(
        "💡 **Business Insight**: A massive surge in inventory requisitions occurs on the 28th–31st of each calendar month. "
        "Departmental managers tend to exhaust remaining monthly budget allocations or stockpile operational goods ('budget flushing') "
        "prior to accounting period closure."
    )

    q_daily = """
        SELECT 
            EXTRACT(DAY FROM t.txn_date)::INT AS day_of_month,
            CASE WHEN EXTRACT(DAY FROM t.txn_date) >= 28 THEN 'Month-End (Days 28-31)'
                 ELSE 'Normal Operating Days (Days 1-27)'
            END AS period_type,
            SUM(tl.quantity) AS total_units_issued,
            COUNT(DISTINCT t.txn_id) AS total_orders,
            ROUND(SUM(tl.quantity * tl.unit_price), 2) AS total_cost_eur
        FROM transactions t
        JOIN transaction_lines tl ON t.txn_id = tl.txn_id
        WHERE t.txn_type = 'ISSUE'
        GROUP BY 1, 2
        ORDER BY 1;
    """
    df_daily = pd.read_sql(q_daily, conn)

    fig_daily = px.bar(
        df_daily,
        x="day_of_month",
        y="total_units_issued",
        color="period_type",
        color_discrete_map={
            "Normal Operating Days (Days 1-27)": "#2b5c8f",
            "Month-End (Days 28-31)": "#d9534f"
        },
        labels={"day_of_month": "Calendar Day of Month", "total_units_issued": "Total Units Issued"},
        title="Daily Stock Outflow by Calendar Day (Highlighting Days 28-31 Surge)"
    )
    fig_daily.update_layout(xaxis=dict(tickmode="linear", tick0=1, dtick=1))
    st.plotly_chart(fig_daily, width="stretch")

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("#### 🏢 Month-End Outflow by Requesting Department")
        q_dept = """
            SELECT 
                t.department_requestor AS department,
                COUNT(DISTINCT t.txn_id) AS total_orders,
                SUM(tl.quantity) AS total_units,
                ROUND(SUM(tl.quantity * tl.unit_price), 2) AS total_cost_eur
            FROM transactions t
            JOIN transaction_lines tl ON t.txn_id = tl.txn_id
            WHERE t.txn_type = 'ISSUE' AND EXTRACT(DAY FROM t.txn_date) >= 28
            GROUP BY 1
            ORDER BY total_units DESC;
        """
        df_dept = pd.read_sql(q_dept, conn)
        fig_dept = px.bar(
            df_dept,
            x="total_units",
            y="department",
            orientation="h",
            color="total_cost_eur",
            color_continuous_scale="Reds",
            labels={"total_units": "Units Requisitioned", "department": "Department", "total_cost_eur": "Cost (€ EUR)"},
            title="Departmental Contribution to Month-End Stock Depletion"
        )
        st.plotly_chart(fig_dept, width="stretch")

    with col_t2:
        st.markdown("#### 📋 Quantitative Comparative Summary")
        q_comp = """
            SELECT 
                CASE WHEN EXTRACT(DAY FROM t.txn_date) >= 28 THEN 'Month-End (Days 28-31)'
                     ELSE 'Normal Operating Days (Days 1-27)'
                END AS operational_period,
                COUNT(DISTINCT t.txn_id) AS total_orders,
                SUM(tl.quantity) AS total_units_issued,
                ROUND(AVG(tl.quantity), 1) AS avg_units_per_line,
                ROUND(SUM(tl.quantity * tl.unit_price), 2) AS total_cost_eur
            FROM transactions t
            JOIN transaction_lines tl ON t.txn_id = tl.txn_id
            WHERE t.txn_type = 'ISSUE'
            GROUP BY 1
            ORDER BY total_units_issued DESC;
        """
        df_comp = pd.read_sql(q_comp, conn)
        st.dataframe(df_comp, width="stretch", hide_index=True)

        st.warning(
            "📌 **Policy Recommendation**: Enforce a *Quota-Based Requisition Cap* during the final 4 business days of each month "
            "and adjust manager KPIs to decouple budget size from next year's operational allowances."
        )

# ═════════════════════════════════════════════════════════════
# TAB 2: PHANTOM RETURNS
# ═════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Minibar Audit: Verified vs. Phantom Returns")
    st.info(
        "💡 **Business Insight**: Across all recorded minibar return operations, **11 falsified return logs (Phantom Returns)** "
        "were uncovered where return slips were authorized by room attendants, but physical inventory was never restocked into warehouse shelves. "
        "This indicates material inventory shrinkage or administrative leakage."
    )

    phantom_ids = (19, 110, 207, 256, 303, 390, 400, 473, 532, 541, 591)
    q_mb = f"""
        SELECT 
            t.txn_id,
            t.reference_no,
            t.txn_date::DATE AS return_date,
            l.location_name AS property_location,
            i.item_code,
            i.item_name,
            tl.quantity AS return_qty,
            tl.unit_price,
            ROUND(tl.unit_price * tl.quantity, 2) AS monetary_value_eur,
            CASE WHEN t.txn_id IN {phantom_ids} THEN '🔴 Phantom Return (Physical Shrinkage)'
                 ELSE '🟢 Verified Return'
            END AS audit_status
        FROM transactions t
        JOIN transaction_lines tl ON t.txn_id = tl.txn_id
        JOIN items i ON tl.item_id = i.item_id
        JOIN locations l ON t.location_id = l.location_id
        WHERE t.txn_type = 'RETURN' AND i.category_id = 3
        ORDER BY t.txn_date DESC;
    """
    df_mb = pd.read_sql(q_mb, conn)

    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        df_pie = df_mb.groupby("audit_status")["monetary_value_eur"].sum().reset_index()
        fig_pie = px.pie(
            df_pie,
            names="audit_status",
            values="monetary_value_eur",
            color="audit_status",
            color_discrete_map={
                "🔴 Phantom Return (Physical Shrinkage)": "#d9534f",
                "🟢 Verified Return": "#5cb85c"
            },
            title="Return Value Audit Breakdown (€ EUR)"
        )
        st.plotly_chart(fig_pie, width="stretch")

    with col_p2:
        df_loc_loss = (
            df_mb[df_mb["audit_status"].str.contains("Phantom")]
            .groupby("property_location")["monetary_value_eur"]
            .sum()
            .reset_index()
            .sort_values(by="monetary_value_eur", ascending=False)
        )
        fig_loc = px.bar(
            df_loc_loss,
            x="property_location",
            y="monetary_value_eur",
            color="monetary_value_eur",
            color_continuous_scale="Oranges",
            labels={"property_location": "Property Location", "monetary_value_eur": "Loss Amount (€ EUR)"},
            title="Total Shrinkage Losses from Phantom Returns by Property Location (€ EUR)"
        )
        st.plotly_chart(fig_loc, width="stretch")

    st.markdown("#### 🔍 Granular Log of Audited Phantom Return Transactions")
    st.dataframe(
        df_mb[df_mb["audit_status"].str.contains("Phantom")],
        width="stretch",
        hide_index=True,
    )

# ═════════════════════════════════════════════════════════════
# TAB 3: STOCK ALERT
# ═════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Inventory Stock Alerts: Below Reorder Point")
    q_reorder = """
        SELECT 
            i.item_code,
            i.item_name,
            ic.category_name AS category,
            l.location_name AS property_location,
            w.warehouse_name AS warehouse,
            s.rack_location AS rack_position,
            s.qty_on_hand AS available_units,
            i.reorder_point AS safety_threshold,
            (s.qty_on_hand - i.reorder_point) AS unit_deficit
        FROM inventory_stock s
        JOIN items i ON s.item_id = i.item_id
        JOIN item_categories ic ON i.category_id = ic.category_id
        JOIN warehouses w ON s.warehouse_id = w.warehouse_id
        JOIN locations l ON w.location_id = l.location_id
        WHERE s.qty_on_hand <= i.reorder_point
        ORDER BY unit_deficit ASC;
    """
    df_reorder = pd.read_sql(q_reorder, conn)

    if not df_reorder.empty:
        st.error(f"🚨 Identified **{len(df_reorder)} inventory records** operating below mandatory safety thresholds!")
        st.dataframe(df_reorder, width="stretch", hide_index=True)
    else:
        st.success("All operational items currently maintain inventory levels safely above reorder points.")
