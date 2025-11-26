from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_babel import gettext as _, Babel
import logging
import sqlite3
import os
import invoice_generator as ig
import main_invoice_generator as mig
import stock_manager as sm
from flask import jsonify  # Import jsonify

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

babel = Babel(app, locale_selector=lambda: app.config.get("LANGUAGE", "bs"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# set language
@app.route("/language/set", methods=["POST"])
def set_language():
    language = request.form.get("language")
    app.config["LANGUAGE"] = language
    return redirect(request.referrer)


@app.route("/add_item", methods=["POST"])
def add_item_to_invoice():
    ig.add_item_to_invoice()
    return redirect(url_for("index"))


# Invoice Generator Routes
@app.route("/", methods=["GET", "POST"])
def index():
    return render_template(
        "index.html", **ig.index(), language=app.config.get("LANGUAGE", "bs")
    )


@app.route("/remove/<int:item_index>", methods=["POST"])
def remove_item(item_index):
    return ig.remove_item(item_index)


@app.route("/export", methods=["POST"])
def export_pdf():
    return ig.export_complete_invoice()



@app.route("/clear", methods=["POST"])
def clear():
    return ig.clear()


@app.route("/main_invoice", methods=["GET"])
def main_invoice():
    return render_template("main_invoice.html")


@app.route("/main_invoice/export", methods=["POST"])
def export_main_invoice():
    data = {
        'invoice_number': request.form.get('invoice_number'),
        'entries': []
    }
    
    for i in range(1, 200): # Support up to 200 rows
        name = request.form.get(f'name_{i}')
        # If we are past row 25 and name is empty, we can probably stop, 
        # but let's just check if any field is present to be safe, or just rely on name.
        # The user might skip rows? Unlikely.
        # If name is empty but we are within the first 25 rows, we should keep it (as empty row).
        # If name is empty and i > 25, we can likely stop.
        
        if i > 25 and not name:
             # Check if other fields are present just in case
             if not any([request.form.get(f'total_{i}'), request.form.get(f'mb_{i}')]):
                 continue # Or break? Let's continue to be safe against gaps, but break if many consecutive empty?
                 # For simplicity, let's just include it if it has a name, OR if i <= 25.
                 pass
        
        if i <= 25 or name:
            entry = {
                'name': name if name else '',
                'phone': request.form.get(f'phone_{i}', ''),
                'total': request.form.get(f'total_{i}', ''),
                'mb': request.form.get(f'mb_{i}', ''),
                'broj_rata': request.form.get(f'broj_rata_{i}', ''),
            }
            data['entries'].append(entry)
            
    pdf_buffer = mig.generate_main_invoice_pdf(data)
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"Glavni_Racun_{data['invoice_number']}.pdf",
        mimetype="application/pdf",
    )


# Stock Management Routes
@app.route("/stock", methods=["GET", "POST"])
def stock_management():
    return sm.stock_management()


@app.route("/stock/search", methods=["GET"])
def stock_search():
    query = request.args.get("query", "").strip()
    results = sm.search_stock(query)
    return jsonify(results)


@app.route("/stock/add", methods=["POST"])
def add_stock_item():
    return sm.add_stock_item()


@app.route("/stock/update/<int:product_id>", methods=["POST"])
def update_stock_item(product_id):
    return sm.update_stock_item(product_id)


@app.route("/stock/delete/<int:product_id>", methods=["POST"])
def delete_stock_item(product_id):
    return sm.delete_stock_item(product_id)


@app.route("/stock/export", methods=["GET"])
def export_stock():
    return sm.export_stock()


@app.route("/product_details", methods=["GET"])
def product_details():
    product_id = request.args.get("product_id")
    if not product_id:
        return jsonify({})  # Return empty object if no ID provided

    try:
        from constants import DATABASE_NAME
        with sqlite3.connect(DATABASE_NAME) as conn:
            conn.set_trace_callback(print)
            c = conn.cursor()
            c.execute(
                "SELECT name,price FROM product WHERE id = ?",
                (int(product_id),),  # Important: Cast product_id to integer
            )
            product = c.fetchone()

            if product:
                return jsonify({"product_name": product[0], "price": product[1]})
            else:
                return jsonify({})  # Return empty object if product not found
    except ValueError:  # Handle non-integer input
        return jsonify({})


@app.route("/autocomplete", methods=["GET"])
def autocomplete():
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify([])

    from constants import DATABASE_NAME
    with sqlite3.connect(DATABASE_NAME) as conn:
        c = conn.cursor()
        # Search by both ID and name
        product_name_pattern = f"%{query}%"
        product_id = int(query) if query.isdigit() else 0
        c.execute("""
            SELECT id, product_name, price 
            FROM stock_view 
            WHERE product_name LIKE ? OR id = ?
            LIMIT 10
        """, (product_name_pattern, product_id))
        
        results = [{
            'id': row[0],
            'product_name': row[1],
            'price': row[2]
        } for row in c.fetchall()]

    return jsonify(results)


if __name__ == "__main__":
    ig.init_db()
    sm.init_db()
    app.run(debug=True, port=5001)
