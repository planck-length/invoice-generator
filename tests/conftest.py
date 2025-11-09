import pytest
import sqlite3
import tempfile
import os
from flask import Flask
import app
import invoice_generator as ig
import stock_manager as sm
import constants


@pytest.fixture
def test_db(monkeypatch):
    """Create a temporary database for testing."""
    # Create a temporary file for the test database
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Store original database name
    original_db = constants.DATABASE_NAME
    
    # Temporarily replace DATABASE_NAME using monkeypatch
    # This patches the constants module
    monkeypatch.setattr(constants, 'DATABASE_NAME', db_path)
    # Also patch the imported name in modules that use it
    # Since modules do "from constants import DATABASE_NAME", we need to patch
    # the attribute in the module namespace
    import sys
    if 'invoice_generator' in sys.modules:
        monkeypatch.setattr(sys.modules['invoice_generator'], 'DATABASE_NAME', db_path)
    if 'stock_manager' in sys.modules:
        monkeypatch.setattr(sys.modules['stock_manager'], 'DATABASE_NAME', db_path)
    
    # Initialize the database directly
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        # Create invoice tables
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
        # Create stock tables
        c.execute(
            """CREATE TABLE IF NOT EXISTS stock (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id INTEGER,
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
    
    yield db_path
    
    # Cleanup: restore original database name and remove test database
    monkeypatch.setattr(constants, 'DATABASE_NAME', original_db)
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def client(test_db, monkeypatch):
    """Create a Flask test client."""
    # Ensure app routes use test database
    monkeypatch.setattr('constants.DATABASE_NAME', test_db)
    
    app.app.config['TESTING'] = True
    app.app.config['WTF_CSRF_ENABLED'] = False
    app.app.config['SECRET_KEY'] = 'test-secret-key'
    
    with app.app.test_client() as client:
        with app.app.app_context():
            yield client


@pytest.fixture
def sample_product(test_db):
    """Create a sample product in the test database."""
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO product (name, price, is_current) VALUES (?, ?, ?)",
            ("Test Product", 10.50, True)
        )
        product_id = c.lastrowid
        c.execute(
            "INSERT INTO stock (product_id, product_name, start_quantity) VALUES (?, ?, ?)",
            (product_id, "Test Product", 100)
        )
        conn.commit()
    return product_id


@pytest.fixture
def sample_invoice(test_db):
    """Create a sample invoice in the test database."""
    with sqlite3.connect(test_db) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO invoice (invoice_number, customer_name, total_amount) VALUES (?, ?, ?)",
            ("INV-1", "Test Customer", 50.00)
        )
        invoice_id = c.lastrowid
        conn.commit()
    return invoice_id

