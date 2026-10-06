"""
generate_visualizations.py
==========================
Generates presentation-ready analytical charts directly from PostgreSQL `inventory_db`.
Outputs:
1. 'hoarding_spike_analysis.png' -> End-of-month inventory hoarding patterns.
2. 'minibar_audit_analysis.png'  -> Minibar phantom returns and stock discrepancies.
"""

import os
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set style
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({
    "font.family": "sans-serif",
    "figure.titlesize": 16,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Connect to PostgreSQL
conn = psycopg2.connect("host=localhost port=5432 dbname=inventory_db user=postgres password=postgres")

# ═════════════════════════════════════════════════════════════
#  CHART 1: HOARDING SPIKE ANALYSIS
# ═════════════════════════════════════════════════════════════
print("Generating Hoarding Spike Analysis chart (English)...")

# Query 1A: Daily timeline of ISSUE quantities
q_daily = """
SELECT 
    EXTRACT(DAY FROM t.txn_date)::INT AS day_of_month,
    SUM(tl.quantity) AS total_qty,
    COUNT(DISTINCT t.txn_id) AS total_txns
FROM transactions t
JOIN transaction_lines tl ON t.txn_id = tl.txn_id
WHERE t.txn_type = 'ISSUE'
GROUP BY 1
ORDER BY 1;
"""
df_daily = pd.read_sql(q_daily, conn)

# Query 1B: Department breakdown at month-end
q_dept = """
SELECT 
    t.department_requestor,
    SUM(tl.quantity) AS total_qty_month_end,
    ROUND(SUM(tl.quantity * tl.unit_price), 2) AS total_cost_eur
FROM transactions t
JOIN transaction_lines tl ON t.txn_id = tl.txn_id
WHERE t.txn_type = 'ISSUE' AND EXTRACT(DAY FROM t.txn_date) >= 28
GROUP BY 1
ORDER BY total_qty_month_end DESC;
"""
df_dept = pd.read_sql(q_dept, conn)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Plot 1A: Daily Distribution
colors = ['#d9534f' if d >= 28 else '#337ab7' for d in df_daily["day_of_month"]]
bars = ax1.bar(df_daily["day_of_month"], df_daily["total_qty"], color=colors, edgecolor="black", alpha=0.85)
ax1.axvline(27.5, color="#d9534f", linestyle="--", linewidth=1.5, label="Month-End Threshold (Days 28-31)")
ax1.set_title("Daily Stock Outflow Pattern (ISSUE Quantity)\nMassive Surge on Days 28-31 (Departmental Hoarding)")
ax1.set_xlabel("Day of Month")
ax1.set_ylabel("Total Units Issued")
ax1.set_xticks(range(1, 32))
ax1.legend(loc="upper left")

# Plot 1B: Department month-end breakdown
sns.barplot(
    data=df_dept,
    x="total_qty_month_end",
    y="department_requestor",
    hue="department_requestor",
    palette="Reds_r",
    ax=ax2,
    edgecolor="black",
    legend=False
)
ax2.set_title("Month-End Stock Outflow by Requesting Department (Days 28-31)\nBreakdown of Volume Requested")
ax2.set_xlabel("Total Units Requested")
ax2.set_ylabel("Department")

for i, v in enumerate(df_dept["total_qty_month_end"]):
    cost = df_dept.iloc[i]["total_cost_eur"]
    ax2.text(v + 150, i, f"{v:,} units (€{cost:,.0f})", va="center", fontsize=9, fontweight="bold")

plt.tight_layout()
chart1_path = os.path.join(OUTPUT_DIR, "hoarding_spike_analysis.png")
plt.savefig(chart1_path, dpi=300)
plt.close()
print(f"  [OK] Saved: {chart1_path}")


# ═════════════════════════════════════════════════════════════
#  CHART 2: MINIBAR PHANTOM RETURNS AUDIT
# ═════════════════════════════════════════════════════════════
print("Generating Minibar Audit Analysis chart (English)...")

# Phantom transaction IDs identified during generation
phantom_txn_ids = (19, 110, 207, 256, 303, 390, 400, 473, 532, 541, 591)

q_minibar = f"""
SELECT 
    t.txn_id,
    l.location_name,
    i.item_name,
    tl.quantity,
    tl.unit_price * tl.quantity AS total_value_eur,
    CASE WHEN t.txn_id IN {phantom_txn_ids} THEN 'Phantom Return (Physical Shrinkage)'
         ELSE 'Verified Return (Restocked)'
    END AS return_status
FROM transactions t
JOIN transaction_lines tl ON t.txn_id = tl.txn_id
JOIN items i ON tl.item_id = i.item_id
JOIN locations l ON t.location_id = l.location_id
WHERE t.txn_type = 'RETURN' AND i.category_id = 3;
"""
df_minibar = pd.read_sql(q_minibar, conn)

fig, (ax3, ax4) = plt.subplots(1, 2, figsize=(16, 6))

# Plot 2A: Return Value by Status
df_status = df_minibar.groupby("return_status")["total_value_eur"].sum().reset_index()
colors_status = ["#d9534f", "#5cb85c"]
ax3.pie(
    df_status["total_value_eur"],
    labels=df_status["return_status"],
    autopct="%1.1f%%",
    startangle=140,
    colors=colors_status,
    explode=(0.08, 0),
    wedgeprops={"edgecolor": "black", "linewidth": 1.2}
)
ax3.set_title("Minibar Returns Audit by Monetary Value (€ EUR)\nProportion of Physical Shrinkage vs. Verified Returns")

# Plot 2B: Phantom Loss per Location
df_phantom_loc = (
    df_minibar[df_minibar["return_status"].str.contains("Phantom")]
    .groupby("location_name")["total_value_eur"]
    .sum()
    .reset_index()
    .sort_values(by="total_value_eur", ascending=False)
)

sns.barplot(
    data=df_phantom_loc,
    x="location_name",
    y="total_value_eur",
    hue="location_name",
    palette="Oranges_r",
    ax=ax4,
    edgecolor="black",
    legend=False
)
ax4.set_title("Estimated Financial Loss from Phantom Returns by Property (€ EUR)\nLogged as Returned but Missing in Warehouse")
ax4.set_xlabel("Facility / Property Location")
ax4.set_ylabel("Total Financial Loss (€ EUR)")

for i, v in enumerate(df_phantom_loc["total_value_eur"]):
    ax4.text(i, v + 8, f"€{v:,.2f}", ha="center", fontsize=10, fontweight="bold")

plt.tight_layout()
chart2_path = os.path.join(OUTPUT_DIR, "minibar_audit_analysis.png")
plt.savefig(chart2_path, dpi=300)
plt.close()
print(f"  [OK] Saved: {chart2_path}")

conn.close()
print("\n[SUCCESS] All analytical charts generated in English in 'reports/'!")
