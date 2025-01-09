from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_babel import gettext as _,Babel
import logging
import sqlite3
import invoice_generator as ig
import stock_manager as sm
from flask import jsonify  # Import jsonify

app = Flask(__name__)


babel = Babel(app, locale_selector=lambda :app.config.get("LANGUAGE", "bs"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)



# set language
@app.route("/language/set", methods=["POST"])
def set_language():
    language = request.form.get("language")
    app.config["LANGUAGE"] = language
    return redirect(request.referrer)


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
    return ig.export_complete_invoice(request)


@app.route("/clear", methods=["POST"])
def clear():
    global current_invoice
    current_invoice = []
    return redirect(url_for("index"))


# Stock Management Routes
@app.route("/stock", methods=["GET", "POST"])
def stock_management():
    return sm.stock_management()


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
        with sqlite3.connect("database.db") as conn:
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
    print("something")
    product_id = request.args.get("product_id")  # Get the query string
    product_name = request.args.get("product_name")  # Get the query string
    if not (product_id or product_name):
        return jsonify([])  # Return empty list if no query

    with sqlite3.connect("database.db") as conn:
        c = conn.cursor()
        conn.set_trace_callback(print)
        c.execute(
            "SELECT id,product_name,price FROM stock WHERE product_name LIKE ? OR id = ? LIMIT 10",
            (
                f"%{product_name}%",
                f"{product_id}",
            ),  # Use wildcard for partial matching
        )
        logger.debug(f"Query: {product_id}, {product_name}")  # Log the query
        results = [row[0] for row in c.fetchall()]

    return jsonify(results)  # Return results as JSON


if __name__ == "__main__":
    ig.init_db()
    sm.init_db()
    app.run(debug=True)
