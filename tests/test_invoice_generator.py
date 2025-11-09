import pytest
import sqlite3
import invoice_generator as ig
import constants


def test_init_db(test_db):
    """Test database initialization."""
    # Initialize using the function
    import invoice_generator as ig
    ig.init_db()
    
    # Verify tables exist
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        
        # Check sales table
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sales'")
        assert c.fetchone() is not None
        
        # Check invoice table
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invoice'")
        assert c.fetchone() is not None
        
        # Check product table
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='product'")
        assert c.fetchone() is not None


def test_get_next_invoice_number(test_db):
    """Test invoice number generation."""
    # First invoice should be INV-1
    invoice_number = ig.get_next_invoice_number()
    assert invoice_number == "INV-1"
    
    # Create an invoice
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO invoice (invoice_number, customer_name, total_amount) VALUES (?, ?, ?)",
            ("INV-1", "Test", 100.0)
        )
        conn.commit()
    
    # Next invoice should be INV-2
    invoice_number = ig.get_next_invoice_number()
    assert invoice_number == "INV-2"


def test_add_item_to_invoice(client):
    """Test adding items to invoice via session."""
    # Initially no items
    with client.session_transaction() as sess:
        assert 'current_invoice' not in sess or len(sess.get('current_invoice', [])) == 0
    
    # Add an item by simulating form submission
    response = client.post('/add_item', data={
        'product_id': '1',
        'product_name': 'Test Product',
        'quantity': 2,
        'price': 10.50
    }, follow_redirects=True)
    
    assert response.status_code == 200
    # Check that item was added to session in a new transaction
    with client.session_transaction() as sess:
        assert len(sess.get('current_invoice', [])) == 1
        item = sess['current_invoice'][0]
        assert item['product_id'] == '1'
        assert item['product_name'] == 'Test Product'
        assert item['quantity'] == 2
        assert item['price'] == 10.50
        assert item['total'] == 21.0


def test_index(client):
    """Test index function returns correct invoice data."""
    with client.session_transaction() as sess:
        # Add items to session
        sess['current_invoice'] = [
            {
                'product_id': '1',
                'product_name': 'Product 1',
                'quantity': 2,
                'price': 10.0,
                'total': 20.0
            },
            {
                'product_id': '2',
                'product_name': 'Product 2',
                'quantity': 1,
                'price': 15.0,
                'total': 15.0
            }
        ]
    
    # Call index through the route
    response = client.get('/')
    assert response.status_code == 200
    
    # Test the index function directly
    with client.session_transaction() as sess:
        result = ig.index()
        assert 'invoice' in result
        assert 'total_amount' in result
        assert 'invoice_number' in result
        assert len(result['invoice']) == 2
        assert result['total_amount'] == 35.0
        assert result['invoice_number'].startswith('INV-')


def test_remove_item(client):
    """Test removing items from invoice."""
    with client.session_transaction() as sess:
        sess['current_invoice'] = [
            {
                'product_id': '1',
                'product_name': 'Product 1',
                'quantity': 2,
                'price': 10.0,
                'total': 20.0
            },
            {
                'product_id': '2',
                'product_name': 'Product 2',
                'quantity': 1,
                'price': 15.0,
                'total': 15.0
            }
        ]
    
    # Remove first item (index 0)
    response = client.post('/remove/0', follow_redirects=True)
    assert response.status_code == 200
    
    with client.session_transaction() as sess:
        current_invoice = sess.get('current_invoice', [])
        assert len(current_invoice) == 1
        assert current_invoice[0]['product_id'] == '2'


def test_update_db_with_current_invoice(test_db, client):
    """Test updating database with invoice."""
    # Set up session and make a request to trigger the update
    with client.session_transaction() as sess:
        sess['current_invoice'] = [
            {
                'product_id': '1',
                'product_name': 'Product 1',
                'quantity': 2,
                'price': 10.0,
                'total': 20.0
            }
        ]
    
    # Use the export route which calls _update_db_with_current_invoice
    response = client.post('/export', data={
        'invoice-number': 'INV-TEST',
        'customer-name': 'Test Customer'
    })
    
    # The export route will call _update_db_with_current_invoice internally
    assert response.status_code == 200
    
    # Verify invoice was saved
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM invoice WHERE invoice_number = ?", ("INV-TEST",))
        invoice = c.fetchone()
        assert invoice is not None
        assert invoice[2] == "Test Customer"  # customer_name
        assert invoice[3] == 20.0  # total_amount
        
        # Verify sales were saved
        # Sales table columns: id, product_id, quantity, invoice_id, price, created_date
        c.execute("SELECT * FROM sales WHERE invoice_id = ?", (invoice[0],))
        sales = c.fetchall()
        assert len(sales) == 1
        assert sales[0][1] == 1  # product_id (index 1)
        assert sales[0][2] == 2  # quantity (index 2)
        assert sales[0][4] == 10.0  # price (index 4, not 3 - invoice_id is at index 3)


def test_export_pdf(client):
    """Test PDF export functionality."""
    # Set up session and use the export route which calls _export_pdf
    with client.session_transaction() as sess:
        sess['current_invoice'] = [
            {
                'product_id': '1',
                'product_name': 'Test Product',
                'quantity': 1,
                'price': 10.0,
                'total': 10.0
            }
        ]
    
    # Use the export route which internally calls _export_pdf
    response = client.post('/export', data={
        'invoice-number': 'INV-TEST',
        'customer-name': 'Test Customer'
    })
    
    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'


def test_export_complete_invoice(test_db, client):
    """Test complete invoice export."""
    with client.session_transaction() as sess:
        sess['current_invoice'] = [
            {
                'product_id': '1',
                'product_name': 'Test Product',
                'quantity': 1,
                'price': 10.0,
                'total': 10.0
            }
        ]
    
    # Export invoice
    response = client.post('/export', data={
        'invoice-number': 'INV-EXPORT',
        'customer-name': 'Export Customer'
    })
    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
    
    # Verify invoice was cleared from session
    with client.session_transaction() as sess:
        current_invoice = sess.get('current_invoice', [])
        assert len(current_invoice) == 0


def test_clear_invoice(client):
    """Test clearing invoice."""
    with client.session_transaction() as sess:
        sess['current_invoice'] = [
            {
                'product_id': '1',
                'product_name': 'Test Product',
                'quantity': 1,
                'price': 10.0,
                'total': 10.0
            }
        ]
    
    # Clear invoice
    response = client.post('/clear', follow_redirects=True)
    assert response.status_code == 200
    
    with client.session_transaction() as sess:
        current_invoice = sess.get('current_invoice', [])
        assert len(current_invoice) == 0

