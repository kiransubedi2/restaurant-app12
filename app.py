from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3, os
from datetime import datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "restaurant.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Food',
            price REAL NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS restaurant_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            notes TEXT DEFAULT '',
            FOREIGN KEY(table_id) REFERENCES restaurant_tables(id)
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            qty INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            sent_kitchen INTEGER NOT NULL DEFAULT 0,
            sent_bar INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY(product_id) REFERENCES products(id)
        );
        """)
        if con.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            con.executemany("INSERT INTO products(name,category,price) VALUES(?,?,?)", [
                ("Hamburger","Food",9.50),("Pizza Margherita","Food",8.90),
                ("Caesar Salad","Food",7.50),("Espresso","Drink",1.20),
                ("Coca-Cola","Drink",2.00),("Water","Drink",1.50)
            ])
        if con.execute("SELECT COUNT(*) FROM restaurant_tables").fetchone()[0] == 0:
            con.executemany("INSERT INTO restaurant_tables(name) VALUES(?)",
                            [(f"Table {i}",) for i in range(1,13)])

@app.route("/")
def index():
    with db() as con:
        tables = con.execute("""
          SELECT t.*, o.id order_id, o.created_at
          FROM restaurant_tables t
          LEFT JOIN orders o ON o.table_id=t.id AND o.status='open'
          WHERE t.active=1 ORDER BY t.id
        """).fetchall()
        products = con.execute("SELECT * FROM products WHERE active=1 ORDER BY category,name").fetchall()
    return render_template("index.html", tables=tables, products=products)

@app.route("/table/<int:table_id>")
def table_order(table_id):
    with db() as con:
        table = con.execute("SELECT * FROM restaurant_tables WHERE id=? AND active=1",(table_id,)).fetchone()
        if not table: return "Table not found",404
        order = con.execute("SELECT * FROM orders WHERE table_id=? AND status='open'",(table_id,)).fetchone()
        if not order:
            cur=con.execute("INSERT INTO orders(table_id,status,created_at) VALUES(?,?,?)",
                            (table_id,"open",datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            order_id=cur.lastrowid
            con.commit()
            order=con.execute("SELECT * FROM orders WHERE id=?",(order_id,)).fetchone()
        items=con.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id",(order["id"],)).fetchall()
        products=con.execute("SELECT * FROM products WHERE active=1 ORDER BY category,name").fetchall()
    return render_template("order.html", table=table, order=order, items=items, products=products)

@app.post("/order/<int:order_id>/add")
def add_item(order_id):
    product_id=request.form.get("product_id", type=int)
    qty=request.form.get("qty", type=int, default=1)
    if not product_id or not qty or qty < 1:
        flash("Choose a product and quantity of at least 1.", "error")
        return redirect(request.referrer or url_for("index"))
    with db() as con:
        p=con.execute("SELECT * FROM products WHERE id=? AND active=1",(product_id,)).fetchone()
        o=con.execute("SELECT * FROM orders WHERE id=? AND status='open'",(order_id,)).fetchone()
        if not p or not o:
            flash("Product or open order not found.", "error")
        else:
            existing=con.execute("SELECT * FROM order_items WHERE order_id=? AND product_id=? AND sent_kitchen=0 AND sent_bar=0",
                                 (order_id,product_id)).fetchone()
            if existing:
                con.execute("UPDATE order_items SET qty=qty+? WHERE id=?",(qty,existing["id"]))
            else:
                con.execute("""INSERT INTO order_items(order_id,product_id,product_name,category,qty,unit_price)
                               VALUES(?,?,?,?,?,?)""",
                            (order_id,p["id"],p["name"],p["category"],qty,p["price"]))
            con.commit()
    return redirect(url_for("table_order",table_id=get_table_id(order_id)))

def get_table_id(order_id):
    with db() as con:
        row=con.execute("SELECT table_id FROM orders WHERE id=?",(order_id,)).fetchone()
        return row["table_id"] if row else 1

@app.post("/item/<int:item_id>/update")
def update_item(item_id):
    qty=request.form.get("qty",type=int,default=1)
    with db() as con:
        item=con.execute("SELECT * FROM order_items WHERE id=?",(item_id,)).fetchone()
        if item:
            if qty <= 0:
                con.execute("DELETE FROM order_items WHERE id=?",(item_id,))
            else:
                con.execute("UPDATE order_items SET qty=? WHERE id=?",(qty,item_id))
            con.commit()
            oid=item["order_id"]
        else: return "Item not found",404
    return redirect(url_for("table_order",table_id=get_table_id(oid)))

@app.route("/ticket/<int:order_id>/<station>")
def ticket(order_id, station):
    if station not in ("kitchen","bar","customer"): return "Invalid ticket",400
    with db() as con:
        order=con.execute("""SELECT o.*, t.name table_name FROM orders o
                            LEFT JOIN restaurant_tables t ON t.id=o.table_id WHERE o.id=?""",(order_id,)).fetchone()
        if not order: return "Order not found",404
        if station=="kitchen":
            items=con.execute("SELECT * FROM order_items WHERE order_id=? AND lower(category) NOT IN ('drink','drinks','beverage','beverages','bar')",(order_id,)).fetchall()
        elif station=="bar":
            items=con.execute("SELECT * FROM order_items WHERE order_id=? AND lower(category) IN ('drink','drinks','beverage','beverages','bar')",(order_id,)).fetchall()
        else:
            items=con.execute("SELECT * FROM order_items WHERE order_id=?",(order_id,)).fetchall()
    return render_template("ticket.html", order=order, items=items, station=station)

@app.post("/order/<int:order_id>/send")
def send_order(order_id):
    station=request.form.get("station")
    if station not in ("kitchen","bar"): return "Invalid station",400
    with db() as con:
        if station=="kitchen":
            con.execute("""UPDATE order_items SET sent_kitchen=1 WHERE order_id=?
                AND lower(category) NOT IN ('drink','drinks','beverage','beverages','bar') AND sent_kitchen=0""",(order_id,))
        else:
            con.execute("""UPDATE order_items SET sent_bar=1 WHERE order_id=?
                AND lower(category) IN ('drink','drinks','beverage','beverages','bar') AND sent_bar=0""",(order_id,))
        con.commit()
    return redirect(url_for("ticket", order_id=order_id, station=station))

@app.post("/order/<int:order_id>/close")
def close_order(order_id):
    with db() as con:
        con.execute("UPDATE orders SET status='closed' WHERE id=?",(order_id,))
        con.commit()
    flash("Order closed.", "success")
    return redirect(url_for("index"))

@app.route("/menu", methods=["GET","POST"])
def menu():
    if request.method=="POST":
        name=request.form.get("name","").strip()
        category=request.form.get("category","Food").strip()
        price=request.form.get("price",type=float)
        if name and price is not None and price>=0:
            with db() as con:
                con.execute("INSERT INTO products(name,category,price) VALUES(?,?,?)",(name,category,price))
                con.commit()
            flash("Product added.", "success")
        else: flash("Enter a product name and valid price.", "error")
        return redirect(url_for("menu"))
    with db() as con:
        products=con.execute("SELECT * FROM products ORDER BY active DESC,category,name").fetchall()
    return render_template("menu.html",products=products)

@app.post("/product/<int:product_id>/toggle")
def toggle_product(product_id):
    with db() as con:
        con.execute("UPDATE products SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(product_id,))
        con.commit()
    return redirect(url_for("menu"))

@app.route("/settings", methods=["GET","POST"])
def settings():
    if request.method=="POST":
        name=request.form.get("name","").strip()
        if name:
            try:
                with db() as con:
                    con.execute("INSERT INTO restaurant_tables(name) VALUES(?)",(name,))
                    con.commit()
                flash("Table added.", "success")
            except sqlite3.IntegrityError: flash("That table name already exists.", "error")
        return redirect(url_for("settings"))
    with db() as con:
        tables=con.execute("SELECT * FROM restaurant_tables ORDER BY id").fetchall()
    return render_template("settings.html",tables=tables)

@app.post("/table/<int:table_id>/toggle")
def toggle_table(table_id):
    with db() as con:
        con.execute("UPDATE restaurant_tables SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?",(table_id,))
        con.commit()
    return redirect(url_for("settings"))

@app.route("/reports")
def reports():
    with db() as con:
        daily=con.execute("""SELECT substr(created_at,1,10) day, COUNT(*) orders,
            COALESCE(SUM((SELECT SUM(qty*unit_price) FROM order_items i WHERE i.order_id=o.id)),0) total
            FROM orders o WHERE status='closed' GROUP BY substr(created_at,1,10) ORDER BY day DESC LIMIT 30""").fetchall()
        totals=con.execute("""SELECT COUNT(*) count, COALESCE(SUM(qty*unit_price),0) total
            FROM order_items i JOIN orders o ON o.id=i.order_id WHERE o.status='closed'""").fetchone()
    return render_template("reports.html",daily=daily,totals=totals)

@app.get("/health")
def health():
    return jsonify(status="ok", app="Restaurant Order Management")

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
