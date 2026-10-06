"""
generate_mock_data.py
=====================
Mock Data Generator — Sistem Pelacakan Inventaris Operasional
Generates ~5,000 rows across 10 PostgreSQL tables.

Embedded Anomalies
------------------
1. PHANTOM RETURNS   : Minibar RETURN transactions exist in `transactions` /
                        `transaction_lines`, but `inventory_stock.qty_on_hand`
                        was NOT increased — simulates a data-integrity gap.
2. END-OF-MONTH SPIKE: ISSUE transactions on dates 28–31 are 3–4× higher
                        than normal days — simulates departmental hoarding.

Output: CSV files in ./mock_data/
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# ── Reproducibility ──────────────────────────────────────────
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mock_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Date range: 6 months (April – September 2026) ───────────
START_DATE = datetime(2026, 4, 1)
END_DATE   = datetime(2026, 9, 30)


def random_date(start=START_DATE, end=END_DATE):
    """Return a random date between start and end."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def random_timestamp(start=START_DATE, end=END_DATE):
    """Return a random datetime (with hour/minute) between start and end."""
    d = random_date(start, end)
    return d.replace(hour=random.randint(6, 22), minute=random.randint(0, 59))


# ═════════════════════════════════════════════════════════════
#  1. LOCATIONS  (4 rows)
# ═════════════════════════════════════════════════════════════
locations = pd.DataFrame([
    {"location_id": 1, "location_name": "Grand Hotel Berlin",     "location_type": "hotel",   "address": "Unter den Linden 15",  "city": "Berlin",    "country": "Germany"},
    {"location_id": 2, "location_name": "Riverside Hotel München", "location_type": "hotel",   "address": "Maximilianstraße 42",  "city": "München",   "country": "Germany"},
    {"location_id": 3, "location_name": "Harbor Factory Hamburg",  "location_type": "factory", "address": "Hafenstraße 88",       "city": "Hamburg",   "country": "Germany"},
    {"location_id": 4, "location_name": "City Hotel Frankfurt",    "location_type": "hotel",   "address": "Kaiserstraße 7",       "city": "Frankfurt", "country": "Germany"},
])
locations["created_at"] = START_DATE

# ═════════════════════════════════════════════════════════════
#  2. SUPPLIERS  (12 rows)
# ═════════════════════════════════════════════════════════════
_supplier_names = [
    "Müller Hygiene GmbH", "Schmidt Chemie AG", "Fischer Gastro Supplies",
    "Weber Reinigung KG", "Becker Hotel Amenities", "Hoffmann Getränke GmbH",
    "Braun Industrial Chemicals", "Wagner Supply Co.", "Krüger Minibar Services",
    "Schneider Wholesale", "Richter Logistik", "Klein Verpackung GmbH",
]
_contact_persons = [
    "Hans Müller", "Petra Schmidt", "Klaus Fischer", "Anna Weber",
    "Stefan Becker", "Julia Hoffmann", "Thomas Braun", "Maria Wagner",
    "Michael Krüger", "Sabine Schneider", "Frank Richter", "Katrin Klein",
]
_cities = [
    "Berlin", "München", "Hamburg", "Düsseldorf", "Köln", "Stuttgart",
    "Frankfurt", "Leipzig", "Bremen", "Dresden", "Hannover", "Nürnberg",
]
_streets = ["Industriestr.", "Hauptstr.", "Bahnhofstr.", "Berliner Str.", "Am Markt"]

suppliers = pd.DataFrame({
    "supplier_id":    range(1, 13),
    "supplier_name":  _supplier_names,
    "contact_person": _contact_persons,
    "phone": [f"+49 {random.randint(30, 89)} {random.randint(1_000_000, 9_999_999)}"
              for _ in range(12)],
    "email": [f"{cp.split()[0].lower()}@{sn.split()[-1].lower()}.de"
              for cp, sn in zip(_contact_persons, _supplier_names)],
    "address": [f"{random.choice(_streets)} {random.randint(1, 200)}" for _ in range(12)],
    "city":           _cities,
    "country":        ["Germany"] * 12,
    "lead_time_days": [random.randint(2, 14) for _ in range(12)],
    "is_active":      [True] * 11 + [False],      # last supplier inactive
    "created_at":     [START_DATE] * 12,
})

# ═════════════════════════════════════════════════════════════
#  3. ITEM_CATEGORIES  (3 rows)
# ═════════════════════════════════════════════════════════════
item_categories = pd.DataFrame([
    {"category_id": 1, "category_name": "Amenities",  "description": "Perlengkapan tamu: sabun, shampoo, sikat gigi, dll."},
    {"category_id": 2, "category_name": "Chemicals",  "description": "Bahan kimia: disinfektan, pembersih lantai, dll."},
    {"category_id": 3, "category_name": "Minibar",    "description": "Produk minibar: snack, minuman, bir, dll."},
])

# ═════════════════════════════════════════════════════════════
#  4. ITEMS  (40 rows — 14 Amenities, 10 Chemicals, 16 Minibar)
# ═════════════════════════════════════════════════════════════
# Columns: code, name, brand, purchase_uom, usage_uom,
#           conversion_factor, unit_cost, selling_price, reorder_point, is_hazardous

_amenities = [
    ("AMN-001", "Bath Soap 30g",       "CleanLux",    "carton", "piece", 200, 0.15, None, 500, False),
    ("AMN-002", "Shampoo Bottle 30ml", "CleanLux",    "carton", "piece", 144, 0.22, None, 400, False),
    ("AMN-003", "Conditioner 30ml",    "CleanLux",    "carton", "piece", 144, 0.22, None, 300, False),
    ("AMN-004", "Body Lotion 30ml",    "CleanLux",    "carton", "piece", 144, 0.25, None, 300, False),
    ("AMN-005", "Dental Kit",          "FreshSmile",  "carton", "piece", 100, 0.30, None, 400, False),
    ("AMN-006", "Shower Cap",          "HotelBasics", "carton", "piece", 500, 0.05, None, 600, False),
    ("AMN-007", "Sewing Kit",          "HotelBasics", "carton", "piece", 100, 0.40, None, 100, False),
    ("AMN-008", "Razor Kit",           "SharpEdge",   "carton", "piece",  50, 0.55, None, 150, False),
    ("AMN-009", "Comb",                "HotelBasics", "carton", "piece", 200, 0.08, None, 300, False),
    ("AMN-010", "Disposable Slippers", "ComfortStep", "carton", "pair",  100, 0.45, None, 300, False),
    ("AMN-011", "Cotton Buds Pack",    "SoftTouch",   "carton", "pack",  200, 0.10, None, 200, False),
    ("AMN-012", "Tissue Box",          "SoftTouch",   "carton", "box",    48, 0.60, None, 200, False),
    ("AMN-013", "Toilet Paper Roll",   "SoftTouch",   "carton", "roll",   96, 0.35, None, 500, False),
    ("AMN-014", "Vanity Kit",          "HotelBasics", "carton", "piece", 100, 0.50, None, 100, False),
]

_chemicals = [
    ("CHM-001", "Floor Cleaner 5L",            "ProClean", "drum",   "liter",  20, 2.50, None,  40, False),
    ("CHM-002", "Glass Cleaner 1L",            "ProClean", "carton", "bottle", 12, 3.20, None,  30, False),
    ("CHM-003", "Disinfectant Concentrate 5L", "BioGuard", "drum",   "liter",  20, 4.80, None,  50, True),
    ("CHM-004", "Toilet Bowl Cleaner 1L",      "ProClean", "carton", "bottle", 12, 2.10, None,  30, False),
    ("CHM-005", "Hand Sanitizer Gel 500ml",    "BioGuard", "carton", "bottle", 24, 1.90, None,  60, False),
    ("CHM-006", "Laundry Detergent 20kg",      "WashPro",  "bag",    "kg",     20, 1.80, None,  25, False),
    ("CHM-007", "Bleach Solution 5L",          "BioGuard", "drum",   "liter",  20, 1.50, None,  30, True),
    ("CHM-008", "Kitchen Degreaser 5L",        "ProClean", "drum",   "liter",  20, 3.60, None,  20, True),
    ("CHM-009", "Air Freshener Spray 500ml",   "FreshAir", "carton", "can",    24, 2.20, None,  40, False),
    ("CHM-010", "Stainless Steel Polish 1L",   "ShinyMax", "carton", "bottle", 12, 5.50, None,  15, False),
]

_minibar = [
    ("MNB-001", "Coca-Cola 330ml",       "Coca-Cola",    "crate",  "can",    24, 0.60, 3.50, 200, False),
    ("MNB-002", "Sprite 330ml",          "Coca-Cola",    "crate",  "can",    24, 0.55, 3.50, 150, False),
    ("MNB-003", "Mineral Water 500ml",   "Gerolsteiner", "crate",  "bottle", 24, 0.30, 2.50, 300, False),
    ("MNB-004", "Orange Juice 200ml",    "Hohes C",      "carton", "pack",   12, 0.80, 4.00, 100, False),
    ("MNB-005", "Pilsner Beer 330ml",    "Bitburger",    "crate",  "bottle", 24, 0.70, 4.50, 200, False),
    ("MNB-006", "Red Wine 187ml",        "Dornfelder",   "carton", "bottle",  6, 2.50, 8.00,  50, False),
    ("MNB-007", "White Wine 187ml",      "Riesling",     "carton", "bottle",  6, 2.80, 8.50,  50, False),
    ("MNB-008", "Pringles Original 40g", "Pringles",     "carton", "tube",   12, 1.20, 4.50, 100, False),
    ("MNB-009", "Chocolate Bar 50g",     "Ritter Sport", "carton", "piece",  24, 0.80, 3.50, 120, False),
    ("MNB-010", "Mixed Nuts 40g",        "Ültje",        "carton", "pack",   20, 0.90, 4.00,  80, False),
    ("MNB-011", "Gummy Bears 100g",      "Haribo",       "carton", "pack",   30, 0.50, 3.00, 100, False),
    ("MNB-012", "KitKat 45g",           "Nestlé",       "carton", "piece",  24, 0.70, 3.50, 100, False),
    ("MNB-013", "Toblerone 50g",         "Toblerone",    "carton", "piece",  24, 1.10, 5.00,  80, False),
    ("MNB-014", "Sparkling Water 330ml", "Gerolsteiner", "crate",  "bottle", 24, 0.35, 2.50, 200, False),
    ("MNB-015", "Energy Drink 250ml",    "Red Bull",     "carton", "can",    24, 1.30, 5.50, 100, False),
    ("MNB-016", "Instant Noodle Cup",    "Maggi",        "carton", "cup",    12, 0.60, 4.00,  60, False),
]

_cols = [
    "item_code", "item_name", "brand", "purchase_uom", "usage_uom",
    "conversion_factor", "unit_cost", "selling_price", "reorder_point", "is_hazardous",
]
_all_raw = _amenities + _chemicals + _minibar

items = pd.DataFrame(_all_raw, columns=_cols)
items.insert(0, "item_id", range(1, len(items) + 1))
items.insert(1, "category_id", [1] * 14 + [2] * 10 + [3] * 16)
items["is_active"]  = True
items["created_at"] = START_DATE
items["updated_at"] = START_DATE

# ═════════════════════════════════════════════════════════════
#  5. ITEM_SUPPLIERS  (many-to-many, ~75 rows)
#     Amenity  suppliers : 1, 5, 8, 10
#     Chemical suppliers : 2, 3, 4, 7
#     Minibar  suppliers : 6, 9, 10, 11
# ═════════════════════════════════════════════════════════════
_cat_supplier_pool = {
    1: [1, 5, 8, 10],   # amenities
    2: [2, 3, 4, 7],    # chemicals
    3: [6, 9, 10, 11],  # minibar
}

_is_rows = []
_is_id = 1
for _, item in items.iterrows():
    pool = _cat_supplier_pool[item["category_id"]]
    n = random.choice([1, 2, 2, 3])
    chosen = random.sample(pool, min(n, len(pool)))
    for idx, sid in enumerate(chosen):
        variation = item["unit_cost"] * random.uniform(-0.15, 0.15)
        _is_rows.append({
            "item_supplier_id": _is_id,
            "item_id":            item["item_id"],
            "supplier_id":        sid,
            "last_purchase_price": round(item["unit_cost"] + variation, 2),
            "last_supply_date":   random_date().date(),
            "is_preferred":       idx == 0,
        })
        _is_id += 1

item_suppliers = pd.DataFrame(_is_rows)

# ═════════════════════════════════════════════════════════════
#  6. WAREHOUSES  (8 rows)
# ═════════════════════════════════════════════════════════════
warehouses = pd.DataFrame([
    {"warehouse_id": 1, "location_id": 1, "warehouse_name": "Berlin Main Store",     "zone": "general"},
    {"warehouse_id": 2, "location_id": 1, "warehouse_name": "Berlin Chemical Room",   "zone": "chemical_rack"},
    {"warehouse_id": 3, "location_id": 2, "warehouse_name": "München Main Store",     "zone": "general"},
    {"warehouse_id": 4, "location_id": 2, "warehouse_name": "München Cold Storage",   "zone": "cold_storage"},
    {"warehouse_id": 5, "location_id": 3, "warehouse_name": "Hamburg Factory Store",  "zone": "general"},
    {"warehouse_id": 6, "location_id": 3, "warehouse_name": "Hamburg Hazmat Cabinet", "zone": "chemical_rack"},
    {"warehouse_id": 7, "location_id": 4, "warehouse_name": "Frankfurt Main Store",   "zone": "general"},
    {"warehouse_id": 8, "location_id": 4, "warehouse_name": "Frankfurt Minibar Hub",  "zone": "minibar_shelf"},
])
warehouses["created_at"] = START_DATE

# ═════════════════════════════════════════════════════════════
#  7. USERS  (20 rows)
# ═════════════════════════════════════════════════════════════
_user_data = [
    ("Erika Hartmann",     "admin",           1),
    ("Wolfgang Meier",     "procurement",     1),
    ("Claudia Zimmermann", "warehouse_staff", 1),
    ("Jürgen Hoffmann",    "housekeeping",    1),
    ("Sabrina Lang",       "front_desk",      1),
    ("Markus Vogt",        "manager",         2),
    ("Heike Baumann",      "procurement",     2),
    ("Ralf Schubert",      "warehouse_staff", 2),
    ("Monika Lehmann",     "housekeeping",    2),
    ("Tobias Winkler",     "front_desk",      2),
    ("Bernd Krause",       "manager",         3),
    ("Sandra Engel",       "procurement",     3),
    ("Uwe Richter",        "warehouse_staff", 3),
    ("Anja Wolff",         "housekeeping",    3),
    ("Lars Dietrich",      "warehouse_staff", 3),
    ("Karin Neumann",      "manager",         4),
    ("Florian Beck",       "procurement",     4),
    ("Petra Schreiber",    "warehouse_staff", 4),
    ("Dirk Schwarz",       "housekeeping",    4),
    ("Nina Böhm",          "front_desk",      4),
]

users = pd.DataFrame(_user_data, columns=["full_name", "role", "location_id"])
users.insert(0, "user_id", range(1, 21))
users["is_active"]  = True
users["created_at"] = START_DATE

# ═════════════════════════════════════════════════════════════
#  8. TRANSACTIONS  &  TRANSACTION_LINES
#     Target ≈ 800 transactions, ≈ 3,900 lines
# ═════════════════════════════════════════════════════════════

# ── Lookup helpers ───────────────────────────────────────────
_loc_warehouses: dict[int, list[int]] = {}
for _, w in warehouses.iterrows():
    _loc_warehouses.setdefault(w["location_id"], []).append(w["warehouse_id"])

_role_txn_map = {
    "RECEIVING":       ["procurement", "warehouse_staff"],
    "ISSUE":           ["warehouse_staff", "housekeeping"],
    "RETURN":          ["procurement", "warehouse_staff"],
    "TRANSFER":        ["warehouse_staff"],
    "ADJUSTMENT":      ["warehouse_staff", "manager"],
    "SPOILAGE_DAMAGE": ["warehouse_staff", "housekeeping", "manager"],
    "MINIBAR_SALE":    ["front_desk", "housekeeping"],
}

_departments = [
    "Housekeeping", "F&B", "Engineering", "Laundry",
    "Front Office", "Spa", "Kitchen",
]

_active_supplier_ids = suppliers[suppliers["is_active"]]["supplier_id"].tolist()

_txn_type_weights = {
    "RECEIVING":       0.20,
    "ISSUE":           0.40,
    "MINIBAR_SALE":    0.18,
    "RETURN":          0.05,
    "TRANSFER":        0.05,
    "ADJUSTMENT":      0.07,
    "SPOILAGE_DAMAGE": 0.05,
}
_txn_types   = list(_txn_type_weights.keys())
_txn_weights = list(_txn_type_weights.values())

# ── Accumulators ─────────────────────────────────────────────
txn_rows:  list[dict] = []
line_rows: list[dict] = []
txn_id  = 1
line_id = 1

# Track phantom-return transaction IDs for anomaly-1 documentation
phantom_return_txn_ids: list[int] = []

# ── NORMAL transactions (650) ────────────────────────────────
N_NORMAL = 650

for _ in range(N_NORMAL):
    txn_type = random.choices(_txn_types, weights=_txn_weights, k=1)[0]
    loc_id   = random.choice([1, 2, 3, 4])
    wh_id    = random.choice(_loc_warehouses[loc_id])
    ts       = random_timestamp()

    # Select a user whose role matches the transaction type
    valid_roles = _role_txn_map[txn_type]
    valid_users = [
        u for u in users.itertuples()
        if u.location_id == loc_id and u.role in valid_roles
    ]
    if not valid_users:                             # fallback
        valid_users = [u for u in users.itertuples() if u.location_id == loc_id]
    user = random.choice(valid_users)

    # Supplier — only for RECEIVING / RETURN
    sup_id = None
    if txn_type in ("RECEIVING", "RETURN"):
        sup_id = random.choice(_active_supplier_ids)

    # Department requestor — for ISSUE, SPOILAGE_DAMAGE, ADJUSTMENT
    dept = None
    if txn_type in ("ISSUE", "SPOILAGE_DAMAGE", "ADJUSTMENT"):
        dept = random.choice(_departments)

    # Reference number
    ref = None
    if txn_type == "RECEIVING":
        ref = f"PO-{ts.strftime('%Y%m')}-{random.randint(100, 999)}"
    elif txn_type == "ISSUE":
        ref = f"REQ-{ts.strftime('%Y%m')}-{random.randint(100, 999)}"
    elif txn_type == "MINIBAR_SALE":
        ref = f"ROOM-{random.randint(101, 520)}"
    elif txn_type == "RETURN":
        ref = f"RET-{ts.strftime('%Y%m')}-{random.randint(100, 999)}"
    elif txn_type == "SPOILAGE_DAMAGE":
        ref = f"DMG-{ts.strftime('%Y%m')}-{random.randint(100, 999)}"
    elif txn_type == "TRANSFER":
        ref = f"TRF-{ts.strftime('%Y%m')}-{random.randint(100, 999)}"
    elif txn_type == "ADJUSTMENT":
        ref = f"ADJ-{ts.strftime('%Y%m')}-{random.randint(100, 999)}"

    # ── ANOMALY 1: ~40 % of RETURN transactions are "phantom" ──
    #    Phantom = minibar items logged as returned, but stock NOT updated.
    is_phantom = False
    if txn_type == "RETURN" and random.random() < 0.40:
        is_phantom = True
        phantom_return_txn_ids.append(txn_id)

    txn_rows.append({
        "txn_id":                txn_id,
        "txn_type":              txn_type,
        "location_id":           loc_id,
        "warehouse_id":          wh_id,
        "supplier_id":           sup_id,
        "user_id":               user.user_id,
        "reference_no":          ref,
        "department_requestor":  dept,
        "txn_date":              ts,
        "remarks":               None,      # no hint in the data — analyst must find it
        "created_at":            ts,
    })

    # ── Transaction lines (2–8 per header) ───────────────────
    n_lines = random.randint(2, 8)

    if txn_type == "MINIBAR_SALE" or is_phantom:
        pool = items[items["category_id"] == 3]["item_id"].tolist()
    else:
        pool = items["item_id"].tolist()

    chosen = random.sample(pool, min(n_lines, len(pool)))

    for iid in chosen:
        row = items.loc[items["item_id"] == iid].iloc[0]

        # Quantity ranges vary by transaction type
        if txn_type == "RECEIVING":
            qty = random.randint(20, 200)
        elif txn_type == "ISSUE":
            qty = random.randint(5, 50)
        elif txn_type == "MINIBAR_SALE":
            qty = random.randint(1, 4)
        elif txn_type in ("RETURN", "SPOILAGE_DAMAGE"):
            qty = random.randint(2, 20)
        else:
            qty = random.randint(1, 30)

        # Room number — only for MINIBAR_SALE
        room = None
        if txn_type == "MINIBAR_SALE":
            room = f"{random.randint(1, 5)}{random.randint(1, 30):02d}"

        batch = f"B{ts.strftime('%y%m')}-{random.randint(1, 50):03d}"

        exp_date = None
        if row["category_id"] in (2, 3):
            exp_date = (ts + timedelta(days=random.randint(90, 365))).date()

        price = (
            row["selling_price"]
            if txn_type == "MINIBAR_SALE" and pd.notna(row["selling_price"])
            else row["unit_cost"]
        )

        line_rows.append({
            "line_id":     line_id,
            "txn_id":      txn_id,
            "item_id":     iid,
            "quantity":    qty,
            "uom":         row["usage_uom"],
            "unit_price":  price,
            "batch_no":    batch,
            "expiry_date": exp_date,
            "room_number": room,
            "remarks":     None,
        })
        line_id += 1

    txn_id += 1

# ── ANOMALY 2: END-OF-MONTH ISSUE SPIKE (150 extra transactions) ──
N_SPIKE = 150

for _ in range(N_SPIKE):
    loc_id = random.choice([1, 2, 3, 4])
    wh_id  = random.choice(_loc_warehouses[loc_id])
    month  = random.randint(4, 9)
    day    = random.randint(28, 31)

    # Safely clamp to valid calendar day
    try:
        ts = datetime(2026, month, day,
                      random.randint(6, 22), random.randint(0, 59))
    except ValueError:
        ts = datetime(2026, month, 28,
                      random.randint(6, 22), random.randint(0, 59))

    valid_roles = _role_txn_map["ISSUE"]
    valid_users = [
        u for u in users.itertuples()
        if u.location_id == loc_id and u.role in valid_roles
    ]
    if not valid_users:
        valid_users = [u for u in users.itertuples() if u.location_id == loc_id]
    user = random.choice(valid_users)

    dept = random.choice(_departments)
    ref  = f"REQ-{ts.strftime('%Y%m')}-{random.randint(100, 999)}"

    txn_rows.append({
        "txn_id":                txn_id,
        "txn_type":              "ISSUE",
        "location_id":           loc_id,
        "warehouse_id":          wh_id,
        "supplier_id":           None,
        "user_id":               user.user_id,
        "reference_no":          ref,
        "department_requestor":  dept,
        "txn_date":              ts,
        "remarks":               None,
        "created_at":            ts,
    })

    # ── Spike lines: more items (4–10) & larger quantities (20–100)
    n_lines = random.randint(4, 10)
    chosen  = random.sample(items["item_id"].tolist(), min(n_lines, len(items)))

    for iid in chosen:
        row = items.loc[items["item_id"] == iid].iloc[0]

        qty = random.randint(20, 100)       # ← abnormally high

        batch = f"B{ts.strftime('%y%m')}-{random.randint(1, 50):03d}"
        exp_date = None
        if row["category_id"] in (2, 3):
            exp_date = (ts + timedelta(days=random.randint(90, 365))).date()

        line_rows.append({
            "line_id":     line_id,
            "txn_id":      txn_id,
            "item_id":     iid,
            "quantity":    qty,
            "uom":         row["usage_uom"],
            "unit_price":  row["unit_cost"],
            "batch_no":    batch,
            "expiry_date": exp_date,
            "room_number": None,
            "remarks":     None,
        })
        line_id += 1

    txn_id += 1

transactions      = pd.DataFrame(txn_rows)
transactions["supplier_id"] = transactions["supplier_id"].astype("Int64")
transaction_lines = pd.DataFrame(line_rows)

# ═════════════════════════════════════════════════════════════
#  9. INVENTORY_STOCK  (~160 rows)
#     NOTE: Phantom-return quantities are deliberately NOT
#           added to qty_on_hand — this IS the anomaly.
# ═════════════════════════════════════════════════════════════
_stock_rows = []
_stock_id   = 1

for _, wh in warehouses.iterrows():
    wh_id = wh["warehouse_id"]
    zone  = wh["zone"]

    # Each warehouse stocks items relevant to its zone
    if zone == "chemical_rack":
        pool = items[items["category_id"] == 2]
    elif zone in ("cold_storage", "minibar_shelf"):
        pool = items[items["category_id"] == 3]
    else:
        pool = items.sample(frac=0.5, random_state=SEED + wh_id)

    for _, item in pool.iterrows():
        n_batches = random.choices([1, 2], weights=[0.75, 0.25], k=1)[0]

        for _ in range(n_batches):
            qty      = random.randint(10, 500)
            reserved = random.randint(0, min(20, qty))

            exp_date = None
            if item["category_id"] in (2, 3):
                if random.random() < 0.15:          # ~15 % near-expiry
                    exp_date = (datetime.now() + timedelta(days=random.randint(5, 25))).date()
                else:
                    exp_date = (datetime.now() + timedelta(days=random.randint(60, 300))).date()

            batch = f"B26{random.randint(4, 9):02d}-{random.randint(1, 50):03d}"
            wh_prefix = wh["warehouse_name"][:3].upper()
            rack = (
                f"{wh_prefix}-{random.choice('ABCDEF')}"
                f"{random.randint(1, 5):02d}-{random.randint(1, 8):02d}"
            )

            _stock_rows.append({
                "stock_id":      _stock_id,
                "item_id":       item["item_id"],
                "warehouse_id":  wh_id,
                "batch_no":      batch,
                "qty_on_hand":   qty,
                "qty_reserved":  reserved,
                "expiry_date":   exp_date,
                "rack_location": rack,
                "last_counted":  random_date().date(),
                "updated_at":    random_timestamp(),
            })
            _stock_id += 1

inventory_stock = pd.DataFrame(_stock_rows)


# ═════════════════════════════════════════════════════════════
#  EXPORT ALL TABLES TO CSV
# ═════════════════════════════════════════════════════════════
datasets = {
    "01_locations":          locations,
    "02_suppliers":          suppliers,
    "03_item_categories":    item_categories,
    "04_items":              items,
    "05_item_suppliers":     item_suppliers,
    "06_warehouses":         warehouses,
    "07_users":              users,
    "08_inventory_stock":    inventory_stock,
    "09_transactions":       transactions,
    "10_transaction_lines":  transaction_lines,
}

total_rows = 0
print()
print("=" * 65)
print("  MOCK DATA GENERATION - INVENTORY TRACKING SYSTEM")
print("=" * 65)

for name, df in datasets.items():
    path = os.path.join(OUTPUT_DIR, f"{name}.csv")
    df.to_csv(path, index=False)
    total_rows += len(df)
    print(f"  [OK] {name:<30s}  ->  {len(df):>6,} rows")

print(f"  {'-' * 45}")
print(f"    {'TOTAL':<28s}  ->  {total_rows:>6,} rows")
print()
print("  +--- ANOMALY 1: PHANTOM RETURNS --------------------------+")
print(f"  |  {len(phantom_return_txn_ids)} RETURN transactions with minibar items     |")
print(f"  |  where inventory_stock qty_on_hand was NOT increased.    |")
print(f"  |  txn_ids: {phantom_return_txn_ids}  |")
print("  +---------------------------------------------------------+")
print()
print("  +--- ANOMALY 2: END-OF-MONTH ISSUE SPIKE -----------------+")
print(f"  |  {N_SPIKE} extra ISSUE transactions forced to dates 28-31.  |")
print(f"  |  Quantities 20-100 (vs normal 5-50).                    |")
print(f"  |  Simulates departmental hoarding at month-end.          |")
print("  +---------------------------------------------------------+")
print()
print(f"  All files saved to: {os.path.abspath(OUTPUT_DIR)}")
print("=" * 65)
