#!/usr/bin/env python3
"""Export the large test invoice PDF for visual inspection."""

import sqlite3
from constants import DATABASE_NAME
from flask import Flask
import app as flask_app
import invoice_generator as ig

app = flask_app.app
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False
app.config['SECRET_KEY'] = 'test-secret-key'

# Get the large invoice from database
with sqlite3.connect(DATABASE_NAME) as conn:
    c = conn.cursor()
    c.execute(
        "SELECT id, invoice_number, customer_name, total_amount FROM invoice WHERE invoice_number = 'INV-LARGE-TEST' ORDER BY id DESC LIMIT 1"
    )
    invoice = c.fetchone()
    
    if not invoice:
        print("Invoice not found")
        exit(1)
    
    invoice_id = invoice[0]
    invoice_number = invoice[1]
    customer_name = invoice[2]
    
    # Get all sales for this invoice
    c.execute(
        "SELECT product_id, quantity, price FROM sales WHERE invoice_id = ?",
        (invoice_id,)
    )
    sales = c.fetchall()
    
    print(f"Invoice: {invoice_number}")
    print(f"Customer: {customer_name}")
    print(f"Total: {invoice[3]}")
    print(f"Items: {len(sales)}")

# Recreate the invoice in session and export
with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['current_invoice'] = []
        
        # Get product names
        with sqlite3.connect(DATABASE_NAME) as conn:
            c = conn.cursor()
            for sale in sales:
                product_id, quantity, price = sale
                c.execute("SELECT name FROM product WHERE id = ?", (product_id,))
                product_name = c.fetchone()[0]
                
                sess['current_invoice'].append({
                    "product_id": str(product_id),
                    "product_name": product_name,
                    "quantity": quantity,
                    "price": price,
                    "total": quantity * price
                })
    
    # Export PDF
    response = client.post('/export', data={
        'invoice-number': invoice_number,
        'customer-name': customer_name
    })
    
    if response.status_code == 200:
        # Save PDF
        filename = f"{invoice_number}.pdf"
        with open(filename, 'wb') as f:
            f.write(response.data)
        print(f"\n✓ PDF exported to: {filename}")
        print(f"  Size: {len(response.data)} bytes")
    else:
        print(f"ERROR: Export failed with status {response.status_code}")

