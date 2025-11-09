import pytest
import sqlite3
import io
import stock_manager as sm
import constants


def test_init_db(test_db):
    """Test stock database initialization."""
    # Initialize using the function
    import stock_manager as sm
    sm.init_db()
    
    # Verify stock table exists
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        
        # Check stock table
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stock'")
        assert c.fetchone() is not None
        
        # Check stock_view view
        c.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='stock_view'")
        assert c.fetchone() is not None


def test_add_stock_item(test_db, client):
    """Test adding a stock item."""
    response = client.post('/stock/add', data={
        'product_name': 'New Product',
        'price': 25.50,
        'start_quantity': 50
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify product was added
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM product WHERE name = ?", ("New Product",))
        product = c.fetchone()
        assert product is not None
        assert product[2] == 25.50  # price
        
        # Verify stock was added
        c.execute("SELECT * FROM stock WHERE product_name = ?", ("New Product",))
        stock = c.fetchone()
        assert stock is not None
        assert stock[3] == 50  # start_quantity


def test_update_stock_item(test_db, client, sample_product):
    """Test updating a stock item."""
    response = client.post(f'/stock/update/{sample_product}', data={
        'price': 15.75,
        'start_quantity': 200
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify product was updated
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM product WHERE id = ?", (sample_product,))
        product = c.fetchone()
        assert product[2] == 15.75  # price
        
        # Verify stock was updated
        c.execute("SELECT * FROM stock WHERE product_id = ?", (sample_product,))
        stock = c.fetchone()
        assert stock[3] == 200  # start_quantity
        assert stock[5] is not None  # updated_date should be set


def test_delete_stock_item(test_db, client, sample_product):
    """Test deleting a stock item."""
    response = client.post(f'/stock/delete/{sample_product}', follow_redirects=True)
    
    assert response.status_code == 200
    
    # Verify product was deleted
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM product WHERE id = ?", (sample_product,))
        product = c.fetchone()
        assert product is None
        
        # Verify stock was deleted
        c.execute("SELECT * FROM stock WHERE product_id = ?", (sample_product,))
        stock = c.fetchone()
        assert stock is None


def test_export_stock(test_db, client, sample_product):
    """Test exporting stock to CSV."""
    response = client.get('/stock/export')
    
    assert response.status_code == 200
    assert response.mimetype == 'text/csv'
    assert response.headers['Content-Disposition'] == 'attachment; filename=stock_export.csv'
    
    # Verify CSV content
    csv_data = response.data.decode('utf-8')
    assert 'Product Name' in csv_data
    assert 'Price' in csv_data
    assert 'Test Product' in csv_data


def test_stock_management(test_db, client, sample_product):
    """Test stock management view."""
    response = client.get('/stock')
    
    assert response.status_code == 200
    # Verify the template is rendered with products
    assert b'Stock Management' in response.data or b'stock' in response.data.lower()


def test_stock_view_query(test_db, sample_product):
    """Test stock_view query returns correct data."""
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM stock_view WHERE id = ?", (sample_product,))
        result = c.fetchone()
        
        assert result is not None
        assert result[0] == sample_product  # id
        assert result[1] == "Test Product"  # product_name
        assert result[2] == 10.50  # price
        assert result[3] == 100  # start_quantity
        assert result[4] == 0  # sold_quantity (no sales yet)
        assert result[5] == 0.0  # total_amount_sold
        assert result[6] == 100  # current_quantity


def test_stock_view_with_sales(test_db, sample_product):
    """Test stock_view with sales data."""
    # Create an invoice and sale
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO invoice (invoice_number, customer_name, total_amount) VALUES (?, ?, ?)",
            ("INV-1", "Test", 50.0)
        )
        invoice_id = c.lastrowid
        c.execute(
            "INSERT INTO sales (product_id, quantity, price, invoice_id) VALUES (?, ?, ?, ?)",
            (sample_product, 5, 10.50, invoice_id)
        )
        conn.commit()
    
    # Check stock_view
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM stock_view WHERE id = ?", (sample_product,))
        result = c.fetchone()
        
        assert result[4] == 5  # sold_quantity
        assert result[5] == 52.50  # total_amount_sold (5 * 10.50)
        assert result[6] == 95  # current_quantity (100 - 5)

