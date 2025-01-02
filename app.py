from flask import Flask, render_template, request, redirect, url_for, send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import sqlite3
import io

app = Flask(__name__)

# Temporary storage for current invoice items
current_invoice = []


# Initialize the database
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_description TEXT,
                    quantity INTEGER,
                    price REAL
                )"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_number TEXT
                )"""
    )
    conn.commit()
    conn.close()


# Get the next invoice number
def get_next_invoice_number():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT MAX(id) FROM invoices")
    result = c.fetchone()[0]
    next_invoice_number = f"INV-{(result + 1) if result else 1}"
    conn.close()
    return next_invoice_number


@app.route("/", methods=["GET", "POST"])
def index():
    global current_invoice
    invoice_number = get_next_invoice_number()

    if request.method == "POST":
        # Update the invoice number (if provided)
        if "update_invoice_number" in request.form:
            invoice_number = request.form.get("invoice_number")

        # Add an item to the current invoice
        if "item_description" in request.form:
            item_description = request.form.get("item_description")
            quantity = int(request.form.get("quantity"))
            price = float(request.form.get("price"))
            total = quantity * price

            current_invoice.append(
                {
                    "item_description": item_description,
                    "quantity": quantity,
                    "price": price,
                    "total": total,
                }
            )

    total_amount = sum(item["total"] for item in current_invoice)
    return render_template(
        "index.html",
        invoice=current_invoice,
        total_amount=total_amount,
        invoice_number=invoice_number,
    )


@app.route("/remove/<int:item_index>", methods=["POST"])
def remove_item(item_index):
    global current_invoice
    if 0 <= item_index < len(current_invoice):
        del current_invoice[item_index]
    return redirect(url_for("index"))


@app.route("/stock", methods=["GET", "POST"])
def stock_management():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Fetch all stock items
    c.execute('''SELECT id, product_name, price, start_quantity, 
                (start_quantity - sold_quantity) AS current_quantity, 
                sold_quantity, 
                (sold_quantity * price) AS total_amount_sold, 
                ((start_quantity - sold_quantity) * price) AS total_amount_current 
                FROM stock''')
    products = c.fetchall()
    conn.close()

    return render_template("stock.html", products=products)


@app.route("/stock/add", methods=["POST"])
def add_stock_item():
    product_name = request.form.get("product_name")
    price = float(request.form.get("price"))
    start_quantity = int(request.form.get("start_quantity"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO stock (product_name, price, start_quantity, sold_quantity) VALUES (?, ?, ?, ?)",
              (product_name, price, start_quantity, 0))
    conn.commit()
    conn.close()

    return redirect(url_for("stock_management"))


@app.route("/stock/update/<int:product_id>", methods=["POST"])
def update_stock_item(product_id):
    price = float(request.form.get("price"))
    start_quantity = int(request.form.get("start_quantity"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE stock SET price = ?, start_quantity = ? WHERE id = ?",
              (price, start_quantity, product_id))
    conn.commit()
    conn.close()

    return redirect(url_for("stock_management"))


@app.route("/stock/export", methods=["GET"])
def export_stock():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''SELECT product_name, price, start_quantity, 
                (start_quantity - sold_quantity) AS current_quantity, 
                sold_quantity, 
                (sold_quantity * price) AS total_amount_sold, 
                ((start_quantity - sold_quantity) * price) AS total_amount_current 
                FROM stock''')
    products = c.fetchall()
    conn.close()

    # Generate a CSV file
    output = io.StringIO()
    output.write("Product Name,Price,Start Quantity,Current Quantity,Sold Quantity,Total Amount Sold,Total Amount Current\n")
    for product in products:
        output.write(",".join(map(str, product)) + "\n")
    output.seek(0)

    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv",
                     as_attachment=True, download_name="stock_export.csv")


# Update the database schema
def update_db_schema():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    # Add stock table
    c.execute('''CREATE TABLE IF NOT EXISTS stock (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT,
                    price REAL,
                    start_quantity INTEGER,
                    sold_quantity INTEGER
                )''')
    conn.commit()
    conn.close()


update_db_schema()


@app.route("/export", methods=["POST"])
def export_pdf():
    global current_invoice
    invoice_number = request.form.get("invoice_number")

    # Save the invoice number to the database
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO invoices (invoice_number) VALUES (?)", (invoice_number,))
    conn.commit()

    # Save current invoice items to the database
    for item in current_invoice:
        c.execute(
            "INSERT INTO sales (item_description, quantity, price) VALUES (?, ?, ?)",
            (item["item_description"], item["quantity"], item["price"]),
        )
    conn.commit()
    conn.close()

    # Create a PDF
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # PDF Title and Invoice Number
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "Invoice")
    c.setFont("Helvetica", 12)
    c.drawString(400, 750, f"Invoice Number: {invoice_number}")

    # Header
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 720, "Item Description")
    c.drawString(300, 720, "Quantity")
    c.drawString(400, 720, "Price")
    c.drawString(500, 720, "Total")

    # Content
    c.setFont("Helvetica", 12)
    y = 700
    for item in current_invoice:
        c.drawString(50, y, item["item_description"])
        c.drawString(300, y, str(item["quantity"]))
        c.drawString(400, y, f"{item['price']:.2f}")
        c.drawString(500, y, f"{item['total']:.2f}")
        y -= 20

    # Total Amount
    total_amount = sum(item["total"] for item in current_invoice)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(400, y - 20, "Total:")
    c.drawString(500, y - 20, f"{total_amount:.2f}")

    c.save()
    buffer.seek(0)

    # Clear the current invoice after export
    current_invoice = []

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"{invoice_number}.pdf",
        mimetype="application/pdf",
    )


@app.route("/clear", methods=["POST"])
def clear():
    global current_invoice
    current_invoice = []
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
