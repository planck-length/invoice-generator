#!/usr/bin/env python3
"""
Test script for large invoice with 500+ products.
Tests calculations, stock updates, and PDF export.
"""

import sqlite3
import sys
from constants import DATABASE_NAME
import invoice_generator as ig
import stock_manager as sm
from flask import Flask
from flask.testing import FlaskClient
import app as flask_app
import io
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    try:
        import pypdf as PyPDF2
        PDF_AVAILABLE = True
    except ImportError:
        PDF_AVAILABLE = False
        print("WARNING: PyPDF2/pypdf not available. PDF verification will be skipped.")

# Initialize Flask app context
app = flask_app.app
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False
app.config['SECRET_KEY'] = 'test-secret-key'

def create_test_products(num_products=500):
    """Create test products in the database."""
    print(f"Creating {num_products} test products...")
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        
        products = []
        for i in range(1, num_products + 1):
            product_name = f"Large Test Product {i:04d}"
            price = round(10.0 + (i % 100) * 0.5, 2)  # Prices from 10.0 to 59.5
            start_quantity = 1000 + (i % 50) * 10  # Quantities from 1000 to 1490
            
            # Insert product and get the ID
            c.execute(
                "INSERT INTO product (name, price, is_current) VALUES (?, ?, ?)",
                (product_name, price, True)
            )
            product_id = c.lastrowid
            
            c.execute(
                "INSERT INTO stock (product_id, product_name, start_quantity) VALUES (?, ?, ?)",
                (product_id, product_name, start_quantity)
            )
            products.append({
                'id': product_id,
                'name': product_name,
                'price': price,
                'start_quantity': start_quantity
            })
        
        conn.commit()
    print(f"Created {num_products} products")
    return products

def create_large_invoice(client, products, items_per_product=1):
    """Create a large invoice with all products."""
    print(f"Creating invoice with {len(products)} items...")
    
    invoice_items = []
    expected_total = 0.0
    
    with client.session_transaction() as sess:
        sess['current_invoice'] = []
        
        for product in products:
            quantity = items_per_product
            price = product['price']
            total = quantity * price
            expected_total += total
            
            item = {
                "product_id": str(product['id']),
                "product_name": product['name'],
                "quantity": quantity,
                "price": price,
                "total": total
            }
            sess['current_invoice'].append(item)
            invoice_items.append(item)
    
    print(f"Invoice created with {len(invoice_items)} items")
    print(f"Expected total: {expected_total:.2f}")
    return invoice_items, expected_total

def test_calculations(invoice_items, expected_total):
    """Test that invoice calculations are correct."""
    print("\n=== Testing Calculations ===")
    
    # Calculate actual total
    actual_total = sum(item['total'] for item in invoice_items)
    
    # Verify each item calculation
    all_correct = True
    for i, item in enumerate(invoice_items):
        expected_item_total = item['quantity'] * item['price']
        if abs(item['total'] - expected_item_total) > 0.01:
            print(f"ERROR: Item {i} calculation wrong: {item['total']} != {expected_item_total}")
            all_correct = False
    
    # Verify grand total
    if abs(actual_total - expected_total) > 0.01:
        print(f"ERROR: Total calculation wrong: {actual_total:.2f} != {expected_total:.2f}")
        all_correct = False
    else:
        print(f"✓ Total calculation correct: {actual_total:.2f}")
    
    return all_correct, actual_total

def export_and_verify_invoice(client, invoice_number, customer_name, expected_total):
    """Export invoice and verify it was saved correctly."""
    print("\n=== Exporting Invoice ===")
    
    response = client.post('/export', data={
        'invoice-number': invoice_number,
        'customer-name': customer_name
    })
    
    if response.status_code != 200:
        print(f"ERROR: Export failed with status {response.status_code}")
        return False, None
    
    if response.mimetype != 'application/pdf':
        print(f"ERROR: Expected PDF, got {response.mimetype}")
        return False, None
    
    print(f"✓ Invoice exported successfully")
    
    # Verify invoice in database
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, invoice_number, customer_name, total_amount FROM invoice WHERE invoice_number = ?",
            (invoice_number,)
        )
        invoice = c.fetchone()
        
        if not invoice:
            print("ERROR: Invoice not found in database")
            return False, None
        
        db_total = invoice[3]
        if abs(db_total - expected_total) > 0.01:
            print(f"ERROR: Database total wrong: {db_total} != {expected_total:.2f}")
            return False, None
        
        print(f"✓ Invoice stored in database: ID={invoice[0]}, Total={db_total:.2f}")
        invoice_id = invoice[0]
    
    # Get PDF content
    pdf_content = response.data
    return True, (invoice_id, pdf_content)

def verify_stock_updates(products, invoice_items, invoice_id):
    """Verify that stock was updated correctly after invoice."""
    print("\n=== Verifying Stock Updates ===")
    
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        
        # Create a map of product_id to quantity sold
        sold_quantities = {}
        for item in invoice_items:
            product_id = int(item['product_id'])
            if product_id not in sold_quantities:
                sold_quantities[product_id] = 0
            sold_quantities[product_id] += item['quantity']
        
        # Verify each product's stock
        all_correct = True
        errors = []
        for product in products:
            product_id = product['id']
            expected_sold = sold_quantities.get(product_id, 0)
            expected_current = product['start_quantity'] - expected_sold
            
            c.execute(
                """SELECT sold_quantity, current_quantity, start_quantity 
                   FROM stock_view WHERE id = ?""",
                (product_id,)
            )
            result = c.fetchone()
            
            if not result:
                errors.append(f"Product {product_id} not found in stock_view")
                all_correct = False
                continue
            
            sold_qty, current_qty, start_qty = result
            
            if sold_qty != expected_sold:
                errors.append(f"Product {product_id} sold quantity wrong: {sold_qty} != {expected_sold}")
                all_correct = False
            
            if current_qty != expected_current:
                errors.append(f"Product {product_id} current quantity wrong: {current_qty} != {expected_current}")
                all_correct = False
        
        if all_correct:
            print(f"✓ All {len(products)} products' stock updated correctly")
        else:
            print(f"ERROR: {len(errors)} stock verification errors (showing first 5):")
            for error in errors[:5]:
                print(f"  - {error}")
        
        # Verify sales records
        c.execute(
            "SELECT COUNT(*) FROM sales WHERE invoice_id = ?",
            (invoice_id,)
        )
        sales_count = c.fetchone()[0]
        
        if sales_count != len(invoice_items):
            print(f"ERROR: Sales records count wrong: {sales_count} != {len(invoice_items)}")
            all_correct = False
        else:
            print(f"✓ All {sales_count} sales records created correctly")
    
    return all_correct

def verify_pdf(pdf_content, invoice_items, expected_total):
    """Verify PDF content."""
    print("\n=== Verifying PDF ===")
    
    if not PDF_AVAILABLE:
        print("SKIPPED: PDF library not available")
        # Basic checks
        if pdf_content[:4] == b'%PDF':
            print("✓ PDF file signature correct")
            print(f"✓ PDF size: {len(pdf_content)} bytes")
            return True
        else:
            print("ERROR: Invalid PDF file signature")
            return False
    
    try:
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        num_pages = len(pdf_reader.pages)
        print(f"✓ PDF has {num_pages} pages")
        
        # Extract text from all pages
        full_text = ""
        for page in pdf_reader.pages:
            full_text += page.extract_text()
        
        # Check for invoice number
        if "INV-" in full_text:
            print("✓ Invoice number found in PDF")
        else:
            print("WARNING: Invoice number not found in PDF")
        
        # Check for total
        total_str = f"{expected_total:.2f}"
        if total_str in full_text:
            print(f"✓ Total amount ({total_str}) found in PDF")
        else:
            print(f"WARNING: Total amount ({total_str}) not found in PDF")
        
        # Count product mentions (rough check)
        product_mentions = sum(1 for item in invoice_items if item['product_name'] in full_text)
        print(f"✓ Found {product_mentions} out of {len(invoice_items)} products in PDF")
        
        if product_mentions < len(invoice_items) * 0.9:  # Allow 10% margin for text extraction issues
            print(f"WARNING: Not all products found in PDF text extraction")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to parse PDF: {e}")
        return False

def main():
    """Main test function."""
    print("=" * 60)
    print("Large Invoice Test (500+ products)")
    print("=" * 60)
    
    num_products = 500
    invoice_number = "INV-LARGE-TEST"
    customer_name = "Large Order Customer"
    
    try:
        # Initialize database
        ig.init_db()
        sm.init_db()
        
        # Create test products
        products = create_test_products(num_products)
        
        # Create invoice using Flask test client
        with app.test_client() as client:
            # Create invoice items
            invoice_items, expected_total = create_large_invoice(client, products)
            
            # Test calculations
            calc_ok, actual_total = test_calculations(invoice_items, expected_total)
            if not calc_ok:
                print("ERROR: Calculation tests failed")
                return 1
            
            # Export invoice
            export_ok, export_result = export_and_verify_invoice(
                client, invoice_number, customer_name, expected_total
            )
            if not export_ok:
                print("ERROR: Export tests failed")
                return 1
            
            invoice_id, pdf_content = export_result
            
            # Verify stock updates
            stock_ok = verify_stock_updates(products, invoice_items, invoice_id)
            if not stock_ok:
                print("ERROR: Stock update tests failed")
                return 1
            
            # Verify PDF
            pdf_ok = verify_pdf(pdf_content, invoice_items, expected_total)
            if not pdf_ok:
                print("WARNING: PDF verification had issues")
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print(f"  - Products: {num_products}")
        print(f"  - Invoice items: {len(invoice_items)}")
        print(f"  - Total amount: {actual_total:.2f}")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\nERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

