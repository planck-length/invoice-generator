import sqlite3
import shutil
from constants import DATABASE_NAME

def migrate():
    print(f"Migrating {DATABASE_NAME}...")
    shutil.copy2(DATABASE_NAME, DATABASE_NAME + ".bak")
    
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        
        # 1. Product table
        c.execute("""CREATE TABLE IF NOT EXISTS product_new(
                        id TEXT PRIMARY KEY,
                        name TEXT,
                        price REAL,
                        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_date TIMESTAMP,
                        is_current BOOLEAN DEFAULT TRUE)""")
        c.execute("INSERT INTO product_new SELECT CAST(id AS TEXT), name, price, start_date, end_date, is_current FROM product")
        c.execute("DROP TABLE product")
        c.execute("ALTER TABLE product_new RENAME TO product")
        
        # 2. Stock table
        c.execute("""CREATE TABLE IF NOT EXISTS stock_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id TEXT,
                        product_name TEXT,
                        start_quantity INTEGER,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_date TIMESTAMP 
                    )""")
        c.execute("INSERT INTO stock_new SELECT id, CAST(product_id AS TEXT), product_name, start_quantity, created_date, updated_date FROM stock")
        c.execute("DROP TABLE stock")
        c.execute("ALTER TABLE stock_new RENAME TO stock")
        
        # 3. Sales table
        c.execute("""CREATE TABLE IF NOT EXISTS sales_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id TEXT,
                        quantity INTEGER,
                        invoice_id INTEGER,
                        price REAL,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )""")
        c.execute("INSERT INTO sales_new SELECT id, CAST(product_id AS TEXT), quantity, invoice_id, price, created_date FROM sales")
        c.execute("DROP TABLE sales")
        c.execute("ALTER TABLE sales_new RENAME TO sales")
        
        # 4. stock_view
        c.execute("DROP VIEW IF EXISTS stock_view")
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
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
