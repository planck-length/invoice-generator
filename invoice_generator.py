from flask import render_template, request, redirect, url_for, send_file
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
        c.execute("SELECT MAX(id) FROM invoices")
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


def remove_item(item_index):
    global current_invoice
    if 0 <= item_index < len(current_invoice):
        del current_invoice[item_index]
    return redirect(url_for("index"))


def _update_db_with_current_invoice(
    invoice_number,
):
    global current_invoice
    with sqlite3.connect("database.db", autocommit=False) as conn:
        c = conn.cursor()
        # Save the invoice number to the database
        c.execute("INSERT INTO invoices (invoice_number) VALUES (?)", (invoice_number,))

        # Save current invoice items to the database
        for item in current_invoice:
            c.execute(
                "INSERT INTO sales (item_description, quantity, price) VALUES (?, ?, ?)",
                (item["item_description"], item["quantity"], item["price"]),
            )
        conn.commit()


def _export_pdf(invoice_number):
    global current_invoice

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


def export_complete_invoice():
    global current_invoice
    invoice_number = request.form.get("invoice_number")
    _update_db_with_current_invoice(invoice_number)
    _export_pdf(invoice_number)


def clear():
    global current_invoice
    current_invoice = []
    return redirect(url_for("index"))
