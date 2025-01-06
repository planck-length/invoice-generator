from flask import render_template, request, redirect, url_for, send_file
from constants import *
import sqlite3
import io
import invoice_generator as ig


def stock_management():
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()

        # Fetch all stock items
        # c.execute(
        #     """SELECT id, product_name, price, start_quantity, 
        #             (start_quantity - sold_quantity) AS current_quantity, 
        #             sold_quantity, 
        #             (sold_quantity * price) AS total_amount_sold, 
        #             ((start_quantity - sold_quantity) * price) AS total_amount_current 
        #             FROM stock"""
        # )
        c.execute("""SELECT * FROM stock_view""")

        products = c.fetchall()

    return render_template("stock.html", products=products)


def add_stock_item():
    product_name = request.form.get("product_name")
    price = float(request.form.get("price"))
    start_quantity = int(request.form.get("start_quantity"))

    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        max_id = c.execute("SELECT COALESCE(MAX(id),0) FROM product").fetchone()[0]
        product_id = max_id + 1
        c.execute("INSERT INTO product (name,price) VALUES (?, ?)", (product_name, price))
        c.execute(
            "INSERT INTO stock (product_id, product_name, start_quantity) VALUES (?, ?, ?)",
            (product_id, product_name, start_quantity),
        )

        conn.commit()

    return redirect(url_for("stock_management"))


def update_stock_item(product_id):
    price = float(request.form.get("price"))
    start_quantity = int(request.form.get("start_quantity"))

    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE stock SET price = ?, start_quantity = ? WHERE id = ?",
            (price, start_quantity, product_id),
        )
        conn.commit()

    return redirect(url_for("stock_management"))


def export_stock():
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT product_name, price, start_quantity, 
                    (start_quantity - sold_quantity) AS current_quantity, 
                    sold_quantity, 
                    (sold_quantity * price) AS total_amount_sold, 
                    ((start_quantity - sold_quantity) * price) AS total_amount_current 
                    FROM stock"""
        )
        products = c.fetchall()

    # Generate a CSV file
    output = io.StringIO()
    output.write(
        "Product Name,Price,Start Quantity,Current Quantity,Sold Quantity,Total Amount Sold,Total Amount Current\n"
    )
    for product in products:
        output.write(",".join(map(str, product)) + "\n")
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="stock_export.csv",
    )


# Update the database schema
def init_db():
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        # CREATE VIEW TO SHOW CURRENT PRODUCT STATUS, AMOUNT SOLD, AMOUNT CURRENT
        c.execute(
            """CREATE TABLE IF NOT EXISTS stock (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id INTEGER,
                        product_name TEXT,
                        start_quantity INTEGER,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )"""
        )
        c.execute(
            """CREATE VIEW IF NOT EXISTS stock_view AS
                SELECT p.id, p.name as product_name, 
                            p.price, st.start_quantity
                            ,SUM(s.quantity) as sold_quantity,
                            SUM(s.quantity*p.price) as total_amount_sold,
                            (st.start_quantity-SUM(s.quantity)) as current_quantity,
                            (st.start_quantity-SUM(s.quantity))*p.price as total_amount_current,
                            group_concat(i.id) as aggregated_invoices
                    FROM sales s 
                    INNER JOIN product p ON p.id=s.product_id 
                    LEFT JOIN invoice i ON i.id=s.invoice_id
                    INNER JOIN stock st ON st.product_id=p.id
                    WHERE p.is_current=TRUE
                    GROUP BY p.id
                    ORDER BY p.id"""
        )
        conn.commit()
