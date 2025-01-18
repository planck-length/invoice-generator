import datetime
from flask import render_template, request, redirect, url_for, send_file
from flask_wtf import FlaskForm
from flask_babel import gettext as _
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import sqlite3
import io

from wtforms import IntegerField, StringField,FloatField
from wtforms.validators import DataRequired


# Temporary storage for current invoice items
current_invoice = []


# Form for adding a new product
class ProductForm(FlaskForm):
    product_id=StringField(_("Product ID"), validators=[DataRequired()])
    product_name=StringField(_("Product Name"), validators=[DataRequired()])
    quantity=IntegerField(_("Quantity"), validators=[DataRequired()])
    price = FloatField(_("Price"), validators=[DataRequired()])


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

def add_item_to_invoice():
    global current_invoice

    form=ProductForm(meta={'csrf': False})
    if form.validate_on_submit():
        # breakpoint()
        product_id = form.product_id.data
        product_name = form.product_name.data
        quantity = form.quantity.data
        price = form.price.data
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
        return redirect(url_for("index"))

def index():
    global current_invoice
    invoice_number = get_next_invoice_number()
    total_amount = sum(item["total"] for item in current_invoice)
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
    resp=_export_pdf(invoice_number, customer_name)
    # Clear the current invoice after export
    current_invoice = []
    return resp


def clear():
    global current_invoice
    current_invoice = []
    return redirect(url_for("index"))
