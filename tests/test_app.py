import pytest
import sqlite3
import json
import constants


def test_index_route(client):
    """Test the main index route."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Invoice' in response.data or b'invoice' in response.data.lower()


def test_add_item_route(client):
    """Test adding item to invoice via route."""
    response = client.post('/add_item', data={
        'product_id': '1',
        'product_name': 'Test Product',
        'quantity': 2,
        'price': 10.50
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify item was added to session
    with client.session_transaction() as sess:
        current_invoice = sess.get('current_invoice', [])
        assert len(current_invoice) == 1
        assert current_invoice[0]['product_id'] == '1'


def test_remove_item_route(client):
    """Test removing item from invoice via route."""
    # First add items
    with client.session_transaction() as sess:
        sess['current_invoice'] = [
            {
                'product_id': '1',
                'product_name': 'Product 1',
                'quantity': 1,
                'price': 10.0,
                'total': 10.0
            },
            {
                'product_id': '2',
                'product_name': 'Product 2',
                'quantity': 1,
                'price': 15.0,
                'total': 15.0
            }
        ]
    
    # Remove first item
    response = client.post('/remove/0', follow_redirects=True)
    assert response.status_code == 200
    
    with client.session_transaction() as sess:
        current_invoice = sess.get('current_invoice', [])
        assert len(current_invoice) == 1
        assert current_invoice[0]['product_id'] == '2'


def test_export_pdf_route(test_db, client):
    """Test PDF export route."""
    # Add items to invoice
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
        'invoice-number': 'INV-TEST',
        'customer-name': 'Test Customer'
    })
    
    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
    assert b'%PDF' in response.data  # PDF file signature


def test_clear_route(client):
    """Test clearing invoice route."""
    # Add items first
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


def test_stock_management_route(client):
    """Test stock management route."""
    response = client.get('/stock')
    assert response.status_code == 200
    assert b'Stock' in response.data or b'stock' in response.data.lower()


def test_add_stock_item_route(test_db, client):
    """Test adding stock item via route."""
    response = client.post('/stock/add', data={
        'product_name': 'New Stock Item',
        'price': 20.00,
        'start_quantity': 100
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify item was added
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM product WHERE name = ?", ("New Stock Item",))
        product = c.fetchone()
        assert product is not None


def test_update_stock_item_route(test_db, client, sample_product):
    """Test updating stock item via route."""
    response = client.post(f'/stock/update/{sample_product}', data={
        'price': 12.00,
        'start_quantity': 150
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify update
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM product WHERE id = ?", (sample_product,))
        product = c.fetchone()
        assert product[2] == 12.00  # price


def test_delete_stock_item_route(test_db, client, sample_product):
    """Test deleting stock item via route."""
    response = client.post(f'/stock/delete/{sample_product}', follow_redirects=True)
    assert response.status_code == 200
    
    # Verify deletion
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM product WHERE id = ?", (sample_product,))
        product = c.fetchone()
        assert product is None


def test_export_stock_route(test_db, client, sample_product):
    """Test stock export route."""
    response = client.get('/stock/export')
    
    assert response.status_code == 200
    assert response.mimetype == 'text/csv'
    assert 'stock_export.csv' in response.headers['Content-Disposition']


def test_product_details_route(test_db, client, sample_product):
    """Test product details JSON endpoint."""
    response = client.get(f'/product_details?product_id={sample_product}')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'product_name' in data
    assert 'price' in data
    assert data['product_name'] == 'Test Product'
    assert data['price'] == 10.50


def test_product_details_route_invalid_id(test_db, client):
    """Test product details with invalid ID."""
    # Ensure database is initialized
    response = client.get('/product_details?product_id=99999')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == {}  # Empty object for invalid ID


def test_product_details_route_no_id(client):
    """Test product details without ID."""
    response = client.get('/product_details')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == {}  # Empty object when no ID provided


def test_autocomplete_route(test_db, client, sample_product):
    """Test autocomplete JSON endpoint."""
    response = client.get('/autocomplete?product_name=Test')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)


def test_autocomplete_route_no_query(client):
    """Test autocomplete without query."""
    response = client.get('/autocomplete')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data == []  # Empty list when no query


def test_language_set_route(client):
    """Test language setting route."""
    # Set a referrer header
    response = client.post('/language/set', 
                          data={'language': 'en'},
                          headers={'Referer': '/'},
                          follow_redirects=True)
    
    assert response.status_code == 200


def test_add_item_form_validation(client):
    """Test form validation when adding items."""
    # Try to submit without required fields
    response = client.post('/add_item', data={}, follow_redirects=True)
    # Should still redirect (form validation happens in the function)
    assert response.status_code == 200


def test_export_without_items(client):
    """Test exporting invoice without items."""
    # Try to export with empty invoice
    response = client.post('/export', data={
        'invoice-number': 'INV-EMPTY',
        'customer-name': 'Test Customer'
    })
    
    # Should still work (creates empty invoice)
    assert response.status_code == 200


def test_remove_item_invalid_index(client):
    """Test removing item with invalid index."""
    # Try to remove item when invoice is empty
    response = client.post('/remove/0', follow_redirects=True)
    assert response.status_code == 200  # Should handle gracefully


def test_stock_view_totals(test_db, client, sample_product):
    """Test stock view totals calculation."""
    # Create a sale
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO invoice (invoice_number, customer_name, total_amount) VALUES (?, ?, ?)",
            ("INV-1", "Test", 50.0)
        )
        invoice_id = c.lastrowid
        c.execute(
            "INSERT INTO sales (product_id, quantity, price, invoice_id) VALUES (?, ?, ?, ?)",
            (sample_product, 10, 10.50, invoice_id)
        )
        conn.commit()
    
    # Check stock management page shows correct totals
    response = client.get('/stock')
    assert response.status_code == 200

