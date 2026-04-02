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
* **`pyproject.toml`:** Poetry configuration file with project dependencies.
* **`tests/`:** Test suite using pytest with unit and integration tests.


## Installation

### Prerequisites

- Python 3.8 or higher
- Poetry (for dependency management)

### Install Poetry

If you don't have Poetry installed, follow the [official Poetry installation guide](https://python-poetry.org/docs/#installation).

### Setup Steps

1.  Clone the repository.
2.  Install dependencies using Poetry:
    ```bash
    poetry install
    ```
    This will create a virtual environment and install all dependencies (including development dependencies for testing).
3.  Activate the Poetry shell:
    ```bash
    poetry shell
    ```
    Or run commands using `poetry run`:
    ```bash
    poetry run python app.py
    ```
4.  Initialize the database (if not already created): The database is automatically initialized when you run the app for the first time. The `init_db()` functions from `invoice_generator.py` and `stock_manager.py` are called automatically.
5.  Set environment variables (optional):
    ```bash
    export SECRET_KEY="your-secret-key-here"  # Linux/macOS
    # or
    set SECRET_KEY=your-secret-key-here  # Windows
    ```
    If not set, a default development key will be used.
6.  Run the Flask app:
    ```bash
    poetry run python app.py
    ```
    Or if you're in the Poetry shell:
    ```bash
    python app.py
    ```

## Usage

1.  Access the invoice generator at `http://127.0.0.1:5000/` (or the appropriate address).
2.  Access the stock manager at `http://127.0.0.1:5000/stock`

## Testing

The project includes comprehensive test coverage using pytest. Tests are located in the `tests/` directory.

### Running Tests

To run all tests:
```bash
poetry run pytest
```

To run tests with coverage report:
```bash
poetry run pytest --cov
```

To run specific test files:
```bash
poetry run pytest tests/test_invoice_generator.py
poetry run pytest tests/test_stock_manager.py
poetry run pytest tests/test_app.py
```

To run tests with verbose output:
```bash
poetry run pytest -v
```

### Test Structure

- **`tests/conftest.py`**: Pytest fixtures for test database and Flask test client
- **`tests/test_invoice_generator.py`**: Unit tests for invoice generation functions
- **`tests/test_stock_manager.py`**: Unit tests for stock management functions
- **`tests/test_app.py`**: Integration tests for Flask routes and endpoints

### Test Coverage

The test suite covers:
- Database initialization and schema
- Invoice creation, item management, and PDF export
- Stock management operations (add, update, delete, export)
- Flask route handlers and form submissions
- JSON API endpoints
- Error handling and edge cases

## Further Development

* **Improved User Interface:**  The current UI is very basic.  A modern JavaScript framework (e.g., React, Vue) could greatly enhance the user experience.
* **More Robust Invoice Features:**  Add features like discounts, taxes, and more detailed product information.
* **User Authentication:**  Implement user authentication to restrict access to the application.
* **Enhanced Reporting:** More comprehensive reports for sales and stock data.
* **CI/CD Integration:** Set up continuous integration to run tests automatically on commits and pull requests.
