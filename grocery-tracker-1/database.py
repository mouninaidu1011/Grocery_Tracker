import sqlite3

def get_connection():
    return sqlite3.connect("grocery.db")

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            unit TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            purchase_date TEXT NOT NULL,
            expiry_date TEXT,
            store TEXT,
            FOREIGN KEY (item_id) REFERENCES items (id)
        )
    """)
    conn.commit()
    conn.close()

# ---------- Items ----------
def add_item(name, category, unit):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO items (name, category, unit) VALUES (?, ?, ?)",
        (name, category, unit)
    )
    conn.commit()
    conn.close()

def get_all_items():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, category, unit FROM items")
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_item(item_id, name, category, unit):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE items SET name = ?, category = ?, unit = ? WHERE id = ?",
        (name, category, unit, item_id)
    )
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = get_connection()
    cursor = conn.cursor()
    # Remove this item's purchases too, so nothing is left orphaned
    cursor.execute("DELETE FROM purchases WHERE item_id = ?", (item_id,))
    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

# ---------- Purchases ----------
def add_purchase(item_id, quantity, price, purchase_date, expiry_date, store):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO purchases
           (item_id, quantity, price, purchase_date, expiry_date, store)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (item_id, quantity, price, purchase_date, expiry_date, store)
    )
    conn.commit()
    conn.close()

def get_all_purchases():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT purchases.id, items.name, items.unit, purchases.quantity,
               purchases.price, purchases.purchase_date,
               purchases.expiry_date, purchases.store
        FROM purchases
        JOIN items ON purchases.item_id = items.id
        ORDER BY purchases.purchase_date DESC, purchases.id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_monthly_expenditure():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT substr(purchase_date, 1, 7) AS month,
               SUM(quantity * price) AS total
        FROM purchases
        GROUP BY month
        ORDER BY month
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_frequent_items(limit=10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT items.name, items.category,
               COUNT(purchases.id) AS times_bought,
               SUM(purchases.quantity * purchases.price) AS total_spent
        FROM purchases
        JOIN items ON purchases.item_id = items.id
        GROUP BY items.id
        ORDER BY times_bought DESC, total_spent DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_expiring_purchases(within_days=7):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT items.name, items.category, purchases.quantity, items.unit,
               purchases.expiry_date,
               CAST(julianday(purchases.expiry_date) - julianday('now', 'localtime') + 1 AS INTEGER)
        FROM purchases
        JOIN items ON purchases.item_id = items.id
        WHERE purchases.expiry_date IS NOT NULL
          AND date(purchases.expiry_date) <= date('now', 'localtime', '+' || ? || ' days')
        ORDER BY purchases.expiry_date
    """, (within_days,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_available_months():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT substr(purchase_date, 1, 7) AS month
        FROM purchases
        ORDER BY month DESC
    """)
    rows = [r[0] for r in cursor.fetchall()]
    conn.close()
    return rows

def get_month_purchases(month):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT items.name, items.category, purchases.quantity, items.unit,
               purchases.price, purchases.purchase_date,
               purchases.expiry_date, purchases.store
        FROM purchases
        JOIN items ON purchases.item_id = items.id
        WHERE substr(purchases.purchase_date, 1, 7) = ?
        ORDER BY purchases.purchase_date
    """, (month,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_image_column():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE items ADD COLUMN image_url TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already undi
    conn.close()

def get_items_with_images():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, category, unit, image_url FROM items")
    rows = cursor.fetchall()
    conn.close()
    return rows

def set_item_image(item_id, image_url):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE items SET image_url = ? WHERE id = ?", (image_url, item_id))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_tables()
    print("Database tables created!")

def search_purchases(name="", category="All", start_date=None, end_date=None,
                     min_price=None, max_price=None):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT purchases.id, items.name, items.category, items.unit,
               purchases.quantity, purchases.price, purchases.purchase_date,
               purchases.expiry_date, purchases.store
        FROM purchases
        JOIN items ON purchases.item_id = items.id
        WHERE 1 = 1
    """
    params = []

    if name:
        query += " AND items.name LIKE ?"
        params.append(f"%{name}%")
    if category != "All":
        query += " AND items.category = ?"
        params.append(category)
    if start_date:
        query += " AND purchases.purchase_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND purchases.purchase_date <= ?"
        params.append(end_date)
    if min_price is not None:
        query += " AND purchases.price >= ?"
        params.append(min_price)
    if max_price is not None:
        query += " AND purchases.price <= ?"
        params.append(max_price)

    query += " ORDER BY purchases.purchase_date DESC, purchases.id DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_purchase(purchase_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))
    conn.commit()
    conn.close()

def update_purchase(purchase_id, quantity, price, purchase_date, expiry_date, store):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE purchases
           SET quantity = ?, price = ?, purchase_date = ?,
               expiry_date = ?, store = ?
           WHERE id = ?""",
        (quantity, price, purchase_date, expiry_date, store, purchase_id)
    )
    conn.commit()
    conn.close()