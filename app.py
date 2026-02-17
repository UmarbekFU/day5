from flask import (
    Flask, render_template, request, jsonify, session,
    redirect, url_for, flash, g
)
import database

app = Flask(__name__)
app.secret_key = "supermarket-dev-key"

TAX_RATE = 0.05


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.before_request
def ensure_cart():
    if "cart" not in session:
        session["cart"] = []


# ── Helper ──────────────────────────────────────────────────────────

def cart_response():
    cart = session.get("cart", [])
    subtotal = sum(item["subtotal"] for item in cart)
    tax = round(subtotal * TAX_RATE, 2)
    return {
        "success": True,
        "cart": cart,
        "totals": {
            "item_count": sum(item["quantity"] for item in cart),
            "subtotal": round(subtotal, 2),
            "tax": tax,
            "total": round(subtotal + tax, 2),
        },
    }


# ── Page Routes ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    stats = database.get_dashboard_stats()
    low_stock = database.get_low_stock_products()
    recent_sales = database.get_recent_sales(10)
    return render_template("dashboard.html", stats=stats,
                           low_stock=low_stock, recent_sales=recent_sales)


@app.route("/inventory")
def inventory():
    q = request.args.get("q", "")
    category_id = request.args.get("category", None, type=int)
    if q or category_id:
        products = database.search_products(q, category_id)
    else:
        products = database.get_all_products()
    categories = database.get_all_categories()
    return render_template("inventory.html", products=products,
                           categories=categories, q=q,
                           selected_category=category_id)


@app.route("/sales")
def sales():
    cart = session.get("cart", [])
    subtotal = sum(item["subtotal"] for item in cart)
    tax = round(subtotal * TAX_RATE, 2)
    totals = {
        "item_count": sum(item["quantity"] for item in cart),
        "subtotal": round(subtotal, 2),
        "tax": tax,
        "total": round(subtotal + tax, 2),
    }
    recent = database.get_recent_sales(20)
    return render_template("sales.html", cart=cart, totals=totals,
                           recent_sales=recent)


@app.route("/suppliers")
@app.route("/suppliers/<int:supplier_id>")
def suppliers(supplier_id=None):
    all_suppliers = database.get_all_suppliers()
    selected = None
    linked_products = []
    if supplier_id:
        selected = database.get_supplier_by_id(supplier_id)
        if selected:
            linked_products = database.get_supplier_products(supplier_id)
    products = database.get_all_products()
    return render_template("suppliers.html", suppliers=all_suppliers,
                           selected=selected, linked_products=linked_products,
                           products=products)


@app.route("/receipt/<int:sale_id>")
def receipt(sale_id):
    sale, items = database.get_sale_details(sale_id)
    if not sale:
        flash("Sale not found.", "danger")
        return redirect(url_for("sales"))
    subtotal = sum(item["subtotal"] for item in items)
    tax = round(subtotal * TAX_RATE, 2)
    total = round(subtotal + tax, 2)
    return render_template("receipt.html", sale=sale, items=items,
                           subtotal=subtotal, tax=tax, total=total)


# ── Product API ─────────────────────────────────────────────────────

@app.route("/api/products/search")
def api_search_products():
    q = request.args.get("q", "")
    results = database.search_products(keyword=q)
    return jsonify([
        {"id": p["id"], "name": p["name"], "barcode": p["barcode"],
         "price": p["price"], "stock": p["stock"],
         "category_name": p["category_name"]}
        for p in results
    ])


@app.route("/api/products", methods=["POST"])
def api_add_product():
    data = request.get_json()
    try:
        pid = database.add_product(
            name=data["name"],
            barcode=data.get("barcode") or None,
            category_id=data.get("category_id") or None,
            price=float(data["price"]),
            cost_price=float(data.get("cost_price", 0)),
            stock=int(data.get("stock", 0)),
            low_stock_threshold=int(data.get("low_stock_threshold", 10)),
        )
        return jsonify({"success": True, "id": pid})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/products/<int:product_id>")
def api_get_product(product_id):
    p = database.get_product_by_id(product_id)
    if not p:
        return jsonify({"success": False, "error": "Not found"}), 404
    return jsonify({
        "id": p["id"], "name": p["name"], "barcode": p["barcode"],
        "category_id": p["category_id"], "category_name": p["category_name"],
        "price": p["price"], "cost_price": p["cost_price"],
        "stock": p["stock"], "low_stock_threshold": p["low_stock_threshold"],
    })


@app.route("/api/products/<int:product_id>", methods=["PUT"])
def api_update_product(product_id):
    data = request.get_json()
    try:
        database.update_product(
            product_id,
            name=data.get("name"),
            barcode=data.get("barcode") or None,
            category_id=data.get("category_id") or None,
            price=float(data["price"]) if "price" in data else None,
            cost_price=float(data["cost_price"]) if "cost_price" in data else None,
            stock=int(data["stock"]) if "stock" in data else None,
            low_stock_threshold=int(data["low_stock_threshold"]) if "low_stock_threshold" in data else None,
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def api_delete_product(product_id):
    try:
        database.delete_product(product_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ── Category API ────────────────────────────────────────────────────

@app.route("/api/categories")
def api_get_categories():
    cats = database.get_all_categories()
    return jsonify([{"id": c["id"], "name": c["name"]} for c in cats])


@app.route("/api/categories", methods=["POST"])
def api_add_category():
    data = request.get_json()
    try:
        cid = database.add_category(data["name"])
        return jsonify({"success": True, "id": cid})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/categories/<int:category_id>", methods=["DELETE"])
def api_delete_category(category_id):
    try:
        database.delete_category(category_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ── Cart API ────────────────────────────────────────────────────────

@app.route("/api/cart")
def api_get_cart():
    return jsonify(cart_response())


@app.route("/api/cart/add", methods=["POST"])
def api_cart_add():
    data = request.get_json()
    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 1))

    product = database.get_product_by_id(product_id)
    if not product:
        return jsonify({"success": False, "error": "Product not found"}), 404

    cart = session.get("cart", [])

    for item in cart:
        if item["product_id"] == product_id:
            new_qty = item["quantity"] + quantity
            if new_qty > product["stock"]:
                return jsonify({"success": False,
                                "error": f"Only {product['stock']} available"}), 400
            item["quantity"] = new_qty
            item["subtotal"] = round(product["price"] * new_qty, 2)
            session["cart"] = cart
            session.modified = True
            return jsonify(cart_response())

    if quantity > product["stock"]:
        return jsonify({"success": False,
                        "error": f"Only {product['stock']} available"}), 400

    cart.append({
        "product_id": product["id"],
        "name": product["name"],
        "price": product["price"],
        "quantity": quantity,
        "subtotal": round(product["price"] * quantity, 2),
    })
    session["cart"] = cart
    session.modified = True
    return jsonify(cart_response())


@app.route("/api/cart/remove", methods=["POST"])
def api_cart_remove():
    data = request.get_json()
    idx = int(data.get("index", -1))
    cart = session.get("cart", [])
    if 0 <= idx < len(cart):
        cart.pop(idx)
        session["cart"] = cart
        session.modified = True
    return jsonify(cart_response())


@app.route("/api/cart/clear", methods=["POST"])
def api_cart_clear():
    session["cart"] = []
    session.modified = True
    return jsonify(cart_response())


# ── Checkout API ────────────────────────────────────────────────────

@app.route("/api/checkout", methods=["POST"])
def api_checkout():
    cart = session.get("cart", [])
    if not cart:
        return jsonify({"success": False, "error": "Cart is empty"}), 400

    data = request.get_json() or {}
    payment_method = data.get("payment_method", "Cash")

    items = [{"product_id": item["product_id"], "quantity": item["quantity"]}
             for item in cart]

    try:
        sale_id = database.create_sale(items, payment_method)
        session["cart"] = []
        session.modified = True
        return jsonify({"success": True, "sale_id": sale_id})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ── Supplier API ────────────────────────────────────────────────────

@app.route("/api/suppliers", methods=["POST"])
def api_add_supplier():
    data = request.get_json()
    try:
        sid = database.add_supplier(
            data["name"], data.get("phone", ""),
            data.get("email", ""), data.get("address", "")
        )
        return jsonify({"success": True, "id": sid})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/suppliers/<int:supplier_id>", methods=["PUT"])
def api_update_supplier(supplier_id):
    data = request.get_json()
    try:
        database.update_supplier(supplier_id, **{
            k: v for k, v in data.items()
            if k in ("name", "phone", "email", "address")
        })
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/suppliers/<int:supplier_id>", methods=["DELETE"])
def api_delete_supplier(supplier_id):
    try:
        database.delete_supplier(supplier_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/suppliers/<int:supplier_id>/products")
def api_supplier_products(supplier_id):
    products = database.get_supplier_products(supplier_id)
    return jsonify([
        {"id": p["id"], "name": p["name"], "price": p["price"],
         "supply_price": p["supply_price"]}
        for p in products
    ])


@app.route("/api/suppliers/<int:supplier_id>/products", methods=["POST"])
def api_link_supplier_product(supplier_id):
    data = request.get_json()
    try:
        database.link_supplier_product(
            supplier_id, int(data["product_id"]),
            float(data.get("supply_price", 0))
        )
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/suppliers/<int:supplier_id>/products/<int:product_id>",
           methods=["DELETE"])
def api_unlink_supplier_product(supplier_id, product_id):
    try:
        database.unlink_supplier_product(supplier_id, product_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    database.init_db()
    database.seed_sample_data()
    app.run(debug=True, port=5000)
