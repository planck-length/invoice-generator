# Simple Invoice Manager

This Python-based invoice manager provides a basic web interface for creating invoices, managing stock, and exporting data.  It uses Flask for the web framework, SQLite for the database, and ReportLab for generating PDF invoices.

## Features

* **Invoice Generation:** Create invoices by adding items, specifying quantities and prices.  Calculates total amounts automatically.  Allows custom invoice numbers and customer names.  Exports invoices to PDF.
* **Stock Management:** Add new products with initial quantities and prices. Update existing product information. Track sold and remaining quantities. Export stock data to CSV.
* **Autocomplete:** Provides autocomplete suggestions for product IDs and names when adding items to an invoice.
* **Internationalization:** Supports multiple languages (currently Bosnian is implemented as an example).

## Technical Details

* **Backend:** Python with Flask framework.
* **Database:** SQLite (database.db).
* **PDF Generation:** ReportLab.
* **Frontend:** HTML, CSS, and JavaScript (minimal usage).
* **Internationalization:** Flask-Babel.

## File Breakdown

* **`app.py`:**  Main Flask application file. Handles routing, database interactions for product details and autocomplete, and language setting.
* **`constants.py`:** Stores constant values, like the database name.
* **`invoice_generator.py`:** Contains functions for managing invoices, including creating new invoices, adding items, calculating totals, and generating PDF output. Also includes database initialization and invoice number generation.
* **`invoice_generator.css`:** Styles for the invoice generation page.
* **`stock_manager.py`:**  Manages stock operations like adding new products, updating existing ones, and exporting stock data.
* **`stock_manager.css`:** Styles for the stock management page.
* **`database.db`:** SQLite database file.
* **`messages.pot`, `messages.po`, `messages.mo`:** Files related to internationalization and translation using gettext.
* **`requirements.txt`:** Lists project dependencies.


## Installation

1.  Clone the repository.
2.  Create a virtual environment: `python3 -m venv venv`
3.  Activate the virtual environment: `source venv/bin/activate` (Linux/macOS) or `venv\Scripts\activate` (Windows)
4.  Install dependencies: `pip install -r requirements.txt`
5.  Initialize the database (if not already created): run `init_db()` function from `invoice_generator.py` and `init_db` from `stock_manager.py`.  Consider adding a separate script or CLI command for this.
6.  Run the Flask app: `python app.py`

## Usage

1.  Access the invoice generator at `http://127.0.0.1:5000/` (or the appropriate address).
2.  Access the stock manager at `http://127.0.0.1:5000/stock`


## Further Development

* **Improved User Interface:**  The current UI is very basic.  A modern JavaScript framework (e.g., React, Vue) could greatly enhance the user experience.
* **More Robust Invoice Features:**  Add features like discounts, taxes, and more detailed product information.
* **User Authentication:**  Implement user authentication to restrict access to the application.
* **Enhanced Reporting:** More comprehensive reports for sales and stock data.
* **Testing:** Add unit tests to ensure code quality and prevent regressions.



