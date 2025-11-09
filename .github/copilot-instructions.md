## Quick orientation for AI code assistants

This repository is a small Flask web app (invoice + stock manager) with SQLite-backed persistence and PDF export. The goal of these notes is to make an AI assistant productive immediately by pointing to the project's architecture, conventions, and common developer workflows.

### Big picture
- Entry point: `app.py` — registers routes and delegates most logic to `invoice_generator.py` and `stock_manager.py`.
- Invoice flow: session key `current_invoice` (list of items) → `invoice_generator._update_db_with_current_invoice()` saves to `invoice` and `sales` tables → `_export_pdf()` uses ReportLab to render the PDF.
- Stock flow: `stock_manager` exposes CRUD handlers and creates a SQL view `stock_view` that aggregates sold/current quantities.
- i18n: Flask-Babel is used; translations live under `translations/bs/LC_MESSAGES/`.

### Important files to inspect (use these as source of truth)
- `app.py` — route wiring, language setter, autocomplete and `/product_details` JSON endpoint.
- `invoice_generator.py` — invoice session model, DB writes, PDF export code (pagination/headers) and `get_next_invoice_number()`.
- `stock_manager.py` — stock DB schema, `stock_view` SQL view, CSV export logic.
- `export_large_invoice_pdf.py` — helper script that uses Flask test client to recreate a large invoice and export a PDF (useful for visual tests).
- `tests/` and `tests/conftest.py` — pytest fixtures show how the test DB is created and how the app is configured for tests.

### Repo-specific conventions and patterns
- Database: raw `sqlite3` usage everywhere. Pattern to follow: `with sqlite3.connect(DATABASE_NAME) as conn:` then `c = conn.cursor()` and `c.execute(...)`.
- Tests patch the DB by monkeypatching `constants.DATABASE_NAME` and also patching the imported name in modules (`invoice_generator`, `stock_manager`) — see `tests/conftest.py`. When modifying DB-using modules, ensure tests still patch OK.
- Session model: invoice items are kept in Flask `session['current_invoice']` and items may store `product_id` as strings — follow existing shape: {product_id, product_name, quantity, price, total}.
- PDF: ReportLab canvas is used; the generator relies on page counts and manual layout. Tests assert `response.mimetype == 'application/pdf'`.
- SQL view: `stock_view` exposes columns used by templates/tests: (id, product_name, price, start_quantity, sold_quantity, total_amount_sold, current_quantity, total_amount_current, aggregated_invoices).

### Developer workflows & commands (exact)
- Install dependencies (Poetry):
  - `poetry install`
  - Use `poetry shell` or `poetry run <cmd>`.
- Run the app (dev): `poetry run python app.py` (app will call `ig.init_db()` and `sm.init_db()` on direct run which initializes DB schema).
- Run tests: `poetry run pytest` (pyproject.toml defines `addopts` that enable coverage and HTML report).
- Export large test PDF (visual): `poetry run python export_large_invoice_pdf.py` (this script expects a pre-populated invoice 'INV-LARGE-TEST').

### Testing gotchas (important to retain)
- Tests disable CSRF and set `app.config['TESTING']=True` and `SECRET_KEY` in `tests/conftest.py` or fixtures — keep this when creating test clients.
- Fixtures create a temporary SQLite DB and monkeypatch `constants.DATABASE_NAME` and the module-level name in `invoice_generator` & `stock_manager` so code that did `from constants import DATABASE_NAME` still uses the test DB.
- Tests rely on exact mimetypes and CSV filename for exports (e.g. `attachment; filename=stock_export.csv`) — don't change these APIs without updating tests.

### Suggested prompts / immediate tasks an AI can do here
- Small bugfix: if touching DB-using modules, run tests and ensure `tests/conftest.py` monkeypatching still applies.
- Add type hints / small refactors: limit to internal functions (e.g., split `_export_pdf()` into smaller helpers) and keep public route signatures unchanged.
- When modifying templates, prefer to preserve form field names (`product_id`, `product_name`, `quantity`, `price`) because tests and routes depend on them.

If anything here is unclear or you want me to expand a section (for example, include a brief mapping of route → handler lines or to surface more example queries from `stock_view`), tell me which part to expand and I will iterate. 
