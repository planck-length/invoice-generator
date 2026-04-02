from flask import render_template, request, redirect, url_for, send_file
from constants import *
import sqlite3
import io
import invoice_generator as ig


def stock_management():
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        c.execute("""SELECT * FROM stock_view""")

        products = c.fetchall()
        (
            total_quantity_sold,
            total_amount_sold,
            total_quantity_current,
            total_amount_current,
        ) = c.execute(
            """SELECT SUM(sold_quantity) total_quantity_sold,
                        SUM(total_amount_sold) total_amount_sold,
                        SUM(current_quantity) total_quantity_current,
                        SUM(total_amount_current) total_amount_current 
                  FROM stock_view"""
        ).fetchall()[
            0
        ]

    return render_template(
        "stock.html",
        products=products,
        total_quantity_sold=total_quantity_sold,
        total_amount_sold=total_amount_sold,
        total_quantity_current=total_quantity_current,
        total_amount_current=total_amount_current,
    )


def add_stock_item():
    product_id = request.form.get("product_id")
    product_name = request.form.get("product_name")
    price = float(request.form.get("price"))
    start_quantity = int(request.form.get("start_quantity"))

    with sqlite3.connect(DATABASE_NAME) as conn:
        conn.set_trace_callback(print)
        c = conn.cursor()
        
        # Check if product_id exists
        c.execute("SELECT id FROM product WHERE id = ?", (product_id,))
        if c.fetchone():
            return "Error: Product ID already exists. Please choose a different one.", 400

        c.execute(
            "INSERT INTO product (id, name, price) VALUES (?, ?, ?)", (product_id, product_name, price)
        )
        c.execute(
            "INSERT INTO stock (product_id, product_name, start_quantity) VALUES (?, ?, ?)",
            (product_id, product_name, start_quantity),
        )

        conn.commit()

    return redirect(url_for("stock_management"))


def update_stock_item(product_id):
    new_product_id = request.form.get("new_product_id")
    product_name = request.form.get("product_name")
    price = float(request.form.get("price"))
    start_quantity = int(request.form.get("start_quantity"))

    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        
        # If product_id changes, check if the new one exists
        if new_product_id and new_product_id != str(product_id):
            c.execute("SELECT id FROM product WHERE id = ?", (new_product_id,))
            if c.fetchone():
                return f"Error: Product ID {new_product_id} already exists.", 400

        target_id = new_product_id if new_product_id else product_id

        # To avoid foreign key issues or simple updates, update in all tables
        # Since we might be changing the PK, update sales, stock, then product
        c.execute(
            "UPDATE sales SET product_id = ? WHERE product_id = ?",
            (target_id, product_id)
        )
        c.execute(
            "UPDATE stock SET product_id = ?, product_name = ?, start_quantity = ?, updated_date = CURRENT_TIMESTAMP WHERE product_id = ?",
            (target_id, product_name, start_quantity, product_id),
        )
        c.execute(
            "UPDATE product SET id = ?, name = ?, price = ? WHERE id = ?",
            (target_id, product_name, price, product_id),
        )
        conn.commit()

    return redirect(url_for("stock_management"))


def delete_stock_item(product_id):
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM product WHERE id = ?",
            (product_id,),
        )
        c.execute(
            "DELETE FROM stock WHERE product_id = ?",
            (product_id,),
        )
        conn.commit()

    return redirect(url_for("stock_management"))


def export_stock():
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        c.execute(
            """SELECT product_name, price, start_quantity, 
                    current_quantity, 
                    sold_quantity, 
                    total_amount_sold, 
                    total_amount_current 
                    FROM stock_view"""
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


def search_stock(query):
    """Return list of products matching query from stock_view as dicts."""
    if not query:
        return []
    product_name_pattern = f"%{query}%"
    product_id = query
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, product_name, price, start_quantity, current_quantity FROM stock_view WHERE product_name LIKE ? OR id = ? LIMIT 50",
            (product_name_pattern, product_id),
        )
        rows = c.fetchall()
    results = [
        {
            "id": row[0],
            "product_name": row[1],
            "price": row[2],
            "start_quantity": row[3],
            "current_quantity": row[4],
        }
        for row in rows
    ]
    return results


# Update the database schema
def init_db():
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        # CREATE VIEW TO SHOW CURRENT PRODUCT STATUS, AMOUNT SOLD, AMOUNT CURRENT
        c.execute(
            """CREATE TABLE IF NOT EXISTS stock (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id TEXT,
                        product_name TEXT,
                        start_quantity INTEGER,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_date TIMESTAMP 
                    )"""
        )
        c.execute(
            """CREATE VIEW IF NOT EXISTS stock_view AS
                SELECT  p.id, 
                        p.name as product_name, 
                        p.price, 
                        st.start_quantity,
                        COALESCE(SUM(s.quantity),0) as sold_quantity,
                        ROUND(COALESCE(SUM(s.quantity*p.price),0),2) as total_amount_sold,
                        (st.start_quantity-COALESCE(SUM(s.quantity),0)) as current_quantity,
                        ROUND((st.start_quantity-COALESCE(SUM(s.quantity),0))*p.price,2) as total_amount_current,
                        COALESCE(group_concat(i.id),'') as aggregated_invoices
                    FROM product p
                    INNER JOIN stock st ON st.product_id=p.id
                    LEFT JOIN sales s ON p.id=s.product_id 
                    LEFT JOIN invoice i ON i.id=s.invoice_id
                    WHERE p.is_current=1
                    GROUP BY p.id
                    ORDER BY p.id"""
        )
        conn.commit()
