import datetime
from flask import render_template, request, redirect, url_for, send_file
from flask_babel import gettext as _
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import sqlite3
import io


# Temporary storage for current invoice items
current_invoice = []


# Initialize the database
def init_db():
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute(
            """CREATE TABLE IF NOT EXISTS sales (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id INTEGER,
                        quantity INTEGER,
                        invoice_id INTEGER,
                        price REAL,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS invoice (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        invoice_number TEXT,
                        customer_name TEXT,
                        total_amount REAL,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS product(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        price REAL,
                        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_date TIMESTAMP,
                        is_current BOOLEAN DEFAULT TRUE) """
        )


# Get the next invoice number
def get_next_invoice_number():
    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        c.execute("SELECT MAX(id) FROM invoice")
        result = c.fetchone()[0]
        next_invoice_number = f"INV-{(result + 1) if result else 1}"
        return next_invoice_number


def index():
    global current_invoice
    invoice_number = get_next_invoice_number()

    if request.method == "POST":
        # Update the invoice number (if provided)
        if "update_invoice_number" in request.form:
            invoice_number = request.form.get("invoice_number")

        # Add an item to the current invoice
        if "quantity" in request.form:
            product_id = request.form.get("product_id")
            product_name = request.form.get("product_name")
            quantity = int(request.form.get("quantity"))
            price = float(request.form.get("price"))
            total = quantity * price

            current_invoice.append(
                {
                    "product_id": product_id,
                    "product_name": product_name,
                    "quantity": quantity,
                    "price": price,
                    "total": total,
                }
            )

    total_amount = sum(item["total"] for item in current_invoice)

    # return render_template(
    #     "index.html",
    #     invoice=current_invoice,
    #     total_amount=total_amount,
    #     invoice_number=invoice_number,
    #     language=app.config["LANGUAGE"],
    # )
    return {
        "invoice": current_invoice,
        "total_amount": total_amount,
        "invoice_number": invoice_number,
    }


def remove_item(item_index):
    global current_invoice
    if 0 <= item_index < len(current_invoice):
        del current_invoice[item_index]
    return redirect(url_for("index"))


def _update_db_with_current_invoice(invoice_number, customer_name):
    global current_invoice
    total_amount = sum(item["total"] for item in current_invoice)
    with sqlite3.connect("database.db", autocommit=False) as conn:
        c = conn.cursor()
        # max invoice number
        c.execute("SELECT MAX(id) FROM invoice")
        max_invoice_id = c.fetchone()[0] or 0
        max_invoice_id += 1

        # Save the invoice number to the database
        c.execute(
            "INSERT INTO invoice (invoice_number,customer_name,total_amount) VALUES (?, ?, ?)",
            (invoice_number, customer_name, float(total_amount)),
        )

        # Save current invoice items to the database
        for item in current_invoice:
            c.execute(
                "INSERT INTO sales (product_id, quantity, price, invoice_id) VALUES (?, ?, ?, ?)",
                (item["product_id"], item["quantity"], item["price"], max_invoice_id),
            )
        conn.commit()


def _export_pdf(invoice_number, customer_name):
    global current_invoice

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # PDF Title and Invoice Number
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, _("Invoice "))
    c.setFont("Helvetica", 12)
    c.drawString(400, 750, _("Invoice Number: ") + invoice_number)
    # Customer Name
    c.drawString(100, 730, _("Customer Name: ") + customer_name)
    # Date and Time
    now = datetime.datetime.now()
    formatted_date_time = now.strftime("%Y-%m-%d %H:%M:%S")
    c.drawString(100, 710, _("Date and Time: ") + formatted_date_time)
    # Header
    c.setFont("Helvetica-Bold", 12)
    y = 690
    c.drawString(50, y, _("Product Id"))
    c.drawString(150, y, _("Product Name"))
    c.drawString(300, y, _("Quantity"))
    c.drawString(400, y, _("Price"))
    c.drawString(500, y, _("Total"))

    # Content
    c.setFont("Helvetica", 12)
    y = 650
    for item in current_invoice:
        c.drawString(50, y, item["product_id"])
        c.drawString(150, y, item["product_name"])
        c.drawString(300, y, str(item["quantity"]))
        c.drawString(400, y, f"{item['price']:.2f}")
        c.drawString(500, y, f"{item['total']:.2f}")
        y -= 20

    # Total Amount
    total_amount = sum(item["total"] for item in current_invoice)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(400, y - 20, _("Total:"))
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


def export_complete_invoice():
    global current_invoice
    invoice_number = request.form.get("invoice-number")
    customer_name = request.form.get("customer-name")
    _update_db_with_current_invoice(invoice_number, customer_name)
    return _export_pdf(invoice_number, customer_name)


def clear():
    global current_invoice
    current_invoice = []
    return redirect(url_for("index"))
