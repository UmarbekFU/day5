import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supermarket.db")

_conn = None


def _make_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def get_connection():
    try:
        from flask import g
        if "db" not in g:
            g.db = _make_connection()
        return g.db
    except (ImportError, RuntimeError):
        global _conn
        if _conn is None:
            _conn = _make_connection()
        return _conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            barcode TEXT UNIQUE,
            category_id INTEGER,
            price REAL NOT NULL CHECK(price >= 0),
            cost_price REAL NOT NULL DEFAULT 0 CHECK(cost_price >= 0),
            stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
            low_stock_threshold INTEGER NOT NULL DEFAULT 10,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT
        );

        CREATE TABLE IF NOT EXISTS supplier_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            supply_price REAL,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
            UNIQUE(supplier_id, product_id)
        );

        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total REAL NOT NULL,
            payment_method TEXT DEFAULT 'Cash',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    """)
    conn.commit()


# ── Categories ──────────────────────────────────────────────────────

def get_all_categories():
    conn = get_connection()
    return conn.execute("SELECT * FROM categories ORDER BY name").fetchall()


def add_category(name):
    conn = get_connection()
    cur = conn.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid


def delete_category(category_id):
    conn = get_connection()
    conn.execute("UPDATE products SET category_id = NULL WHERE category_id = ?", (category_id,))
    conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()


# ── Products ────────────────────────────────────────────────────────

def get_all_products():
    conn = get_connection()
    return conn.execute("""
        SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        ORDER BY p.name
    """).fetchall()


def search_products(keyword="", category_id=None):
    conn = get_connection()
    query = """
        SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE 1=1
    """
    params = []
    if keyword:
        query += " AND (p.name LIKE ? OR p.barcode LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if category_id:
        query += " AND p.category_id = ?"
        params.append(category_id)
    query += " ORDER BY p.name"
    return conn.execute(query, params).fetchall()


def get_product_by_id(product_id):
    conn = get_connection()
    return conn.execute("""
        SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.id = ?
    """, (product_id,)).fetchone()


def get_product_by_barcode(barcode):
    conn = get_connection()
    return conn.execute("""
        SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.barcode = ?
    """, (barcode,)).fetchone()


def add_product(name, barcode, category_id, price, cost_price, stock, low_stock_threshold):
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO products (name, barcode, category_id, price, cost_price, stock, low_stock_threshold)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, barcode or None, category_id or None, price, cost_price, stock, low_stock_threshold))
    conn.commit()
    return cur.lastrowid


def update_product(product_id, **fields):
    conn = get_connection()
    allowed = {"name", "barcode", "category_id", "price", "cost_price", "stock", "low_stock_threshold"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [product_id]
    conn.execute(f"UPDATE products SET {set_clause} WHERE id = ?", values)
    conn.commit()


def delete_product(product_id):
    conn = get_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()


def get_low_stock_products():
    conn = get_connection()
    return conn.execute("""
        SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.stock <= p.low_stock_threshold
        ORDER BY p.stock ASC
    """).fetchall()


# ── Suppliers ───────────────────────────────────────────────────────

def get_all_suppliers():
    conn = get_connection()
    return conn.execute("SELECT * FROM suppliers ORDER BY name").fetchall()


def get_supplier_by_id(supplier_id):
    conn = get_connection()
    return conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()


def add_supplier(name, phone, email, address):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO suppliers (name, phone, email, address) VALUES (?, ?, ?, ?)",
        (name, phone, email, address)
    )
    conn.commit()
    return cur.lastrowid


def update_supplier(supplier_id, **fields):
    conn = get_connection()
    allowed = {"name", "phone", "email", "address"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [supplier_id]
    conn.execute(f"UPDATE suppliers SET {set_clause} WHERE id = ?", values)
    conn.commit()


def delete_supplier(supplier_id):
    conn = get_connection()
    conn.execute("DELETE FROM suppliers WHERE id = ?", (supplier_id,))
    conn.commit()


def link_supplier_product(supplier_id, product_id, supply_price):
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO supplier_products (supplier_id, product_id, supply_price)
        VALUES (?, ?, ?)
    """, (supplier_id, product_id, supply_price))
    conn.commit()


def unlink_supplier_product(supplier_id, product_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM supplier_products WHERE supplier_id = ? AND product_id = ?",
        (supplier_id, product_id)
    )
    conn.commit()


def get_supplier_products(supplier_id):
    conn = get_connection()
    return conn.execute("""
        SELECT p.id, p.name, p.barcode, p.price, sp.supply_price
        FROM supplier_products sp
        JOIN products p ON sp.product_id = p.id
        WHERE sp.supplier_id = ?
        ORDER BY p.name
    """, (supplier_id,)).fetchall()


# ── Sales ───────────────────────────────────────────────────────────

def create_sale(items, payment_method="Cash"):
    """
    items: list of dicts with keys: product_id, quantity
    Creates a sale in a single transaction. Decrements stock.
    Returns the new sale ID.
    """
    conn = get_connection()
    try:
        total = 0.0
        sale_rows = []

        for item in items:
            product = get_product_by_id(item["product_id"])
            if product is None:
                raise ValueError(f"Product ID {item['product_id']} not found")
            if product["stock"] < item["quantity"]:
                raise ValueError(
                    f"Insufficient stock for '{product['name']}': "
                    f"requested {item['quantity']}, available {product['stock']}"
                )
            subtotal = product["price"] * item["quantity"]
            total += subtotal
            sale_rows.append({
                "product_id": product["id"],
                "product_name": product["name"],
                "quantity": item["quantity"],
                "unit_price": product["price"],
                "subtotal": subtotal,
            })

        cur = conn.execute(
            "INSERT INTO sales (total, payment_method) VALUES (?, ?)",
            (round(total, 2), payment_method)
        )
        sale_id = cur.lastrowid

        for row in sale_rows:
            conn.execute("""
                INSERT INTO sale_items (sale_id, product_id, product_name, quantity, unit_price, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (sale_id, row["product_id"], row["product_name"],
                  row["quantity"], row["unit_price"], round(row["subtotal"], 2)))

            conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ?",
                (row["quantity"], row["product_id"])
            )

        conn.commit()
        return sale_id

    except Exception:
        conn.rollback()
        raise


def get_recent_sales(limit=20):
    conn = get_connection()
    return conn.execute("""
        SELECT s.*, COUNT(si.id) as item_count
        FROM sales s
        LEFT JOIN sale_items si ON s.id = si.sale_id
        GROUP BY s.id
        ORDER BY s.created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()


def get_sale_details(sale_id):
    conn = get_connection()
    sale = conn.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
    items = conn.execute(
        "SELECT * FROM sale_items WHERE sale_id = ? ORDER BY id", (sale_id,)
    ).fetchall()
    return sale, items


# ── Dashboard Stats ─────────────────────────────────────────────────

def get_dashboard_stats():
    conn = get_connection()
    total_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_categories = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    low_stock_count = conn.execute(
        "SELECT COUNT(*) FROM products WHERE stock <= low_stock_threshold"
    ).fetchone()[0]
    today_sales = conn.execute("""
        SELECT COUNT(*), COALESCE(SUM(total), 0)
        FROM sales WHERE DATE(created_at) = DATE('now')
    """).fetchone()
    total_revenue = conn.execute(
        "SELECT COALESCE(SUM(total), 0) FROM sales"
    ).fetchone()[0]

    return {
        "total_products": total_products,
        "total_categories": total_categories,
        "low_stock_count": low_stock_count,
        "today_sales_count": today_sales[0],
        "today_revenue": today_sales[1],
        "total_revenue": total_revenue,
    }


# ── Seed Data ───────────────────────────────────────────────────────

def seed_sample_data():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count > 0:
        return

    categories = ["Dairy", "Bakery", "Beverages", "Snacks", "Fruits & Vegetables",
                   "Meat & Poultry", "Frozen Foods", "Household"]
    for cat in categories:
        add_category(cat)

    cats = {row["name"]: row["id"] for row in get_all_categories()}

    products = [
        ("Whole Milk 1L", "1001", cats["Dairy"], 3.49, 2.10, 45, 10),
        ("Cheddar Cheese 200g", "1002", cats["Dairy"], 4.99, 3.20, 30, 8),
        ("Greek Yogurt 500g", "1003", cats["Dairy"], 5.49, 3.50, 25, 8),
        ("White Bread Loaf", "2001", cats["Bakery"], 2.49, 1.20, 50, 15),
        ("Croissants 4-pack", "2002", cats["Bakery"], 3.99, 2.40, 20, 10),
        ("Orange Juice 1L", "3001", cats["Beverages"], 4.29, 2.80, 35, 10),
        ("Sparkling Water 6-pack", "3002", cats["Beverages"], 5.99, 3.60, 40, 12),
        ("Cola 2L", "3003", cats["Beverages"], 2.99, 1.50, 60, 15),
        ("Potato Chips 150g", "4001", cats["Snacks"], 3.29, 1.80, 55, 15),
        ("Chocolate Bar", "4002", cats["Snacks"], 1.99, 0.90, 80, 20),
        ("Bananas 1kg", "5001", cats["Fruits & Vegetables"], 1.49, 0.70, 5, 10),
        ("Tomatoes 500g", "5002", cats["Fruits & Vegetables"], 2.99, 1.60, 3, 8),
        ("Chicken Breast 500g", "6001", cats["Meat & Poultry"], 7.99, 5.20, 20, 8),
        ("Frozen Pizza", "7001", cats["Frozen Foods"], 6.49, 3.80, 15, 5),
        ("Dish Soap 500ml", "8001", cats["Household"], 3.99, 2.00, 25, 10),
    ]
    for p in products:
        add_product(*p)

    suppliers_data = [
        ("Fresh Farms Co.", "555-0101", "orders@freshfarms.com", "123 Farm Road"),
        ("Metro Distributors", "555-0202", "sales@metrodist.com", "456 Industrial Ave"),
        ("Quick Supply Ltd.", "555-0303", "info@quicksupply.com", "789 Commerce St"),
    ]
    for s in suppliers_data:
        add_supplier(*s)
