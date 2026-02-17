import tkinter as tk
from tkinter import ttk, messagebox
import database
from receipt_viewer import ReceiptViewer

TAX_RATE = 0.05


class SalesTab:
    def __init__(self, parent_notebook):
        self.frame = ttk.Frame(parent_notebook)
        self.cart = []  # list of dicts: product_id, name, price, quantity, subtotal

        # Main split: left (cart) and right (summary)
        main_pane = ttk.PanedWindow(self.frame, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(main_pane)
        right = ttk.Frame(main_pane)
        main_pane.add(left, weight=3)
        main_pane.add(right, weight=2)

        self.setup_input_area(left)
        self.setup_cart_treeview(left)
        self.setup_cart_buttons(left)
        self.setup_summary_panel(right)
        self.setup_recent_sales(right)

    def setup_input_area(self, parent):
        bar = ttk.Frame(parent)
        bar.pack(fill="x", pady=(0, 5))

        ttk.Label(bar, text="Barcode / Product Name:").pack(side="left", padx=(0, 5))
        self.product_entry_var = tk.StringVar()
        entry = ttk.Entry(bar, textvariable=self.product_entry_var, width=30)
        entry.pack(side="left", padx=(0, 5))
        entry.bind("<Return>", lambda e: self.add_to_cart())

        ttk.Label(bar, text="Qty:").pack(side="left", padx=(5, 2))
        self.qty_var = tk.StringVar(value="1")
        qty_entry = ttk.Entry(bar, textvariable=self.qty_var, width=5)
        qty_entry.pack(side="left", padx=(0, 5))
        qty_entry.bind("<Return>", lambda e: self.add_to_cart())

        ttk.Button(bar, text="Add to Cart", command=self.add_to_cart).pack(side="left", padx=5)

    def setup_cart_treeview(self, parent):
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True, pady=5)

        columns = ("#", "Product", "Price", "Qty", "Subtotal")
        self.cart_tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")

        widths = [40, 200, 80, 60, 90]
        for col, w in zip(columns, widths):
            self.cart_tree.heading(col, text=col)
            anchor = "center" if col != "Product" else "w"
            self.cart_tree.column(col, width=w, anchor=anchor)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=scrollbar.set)
        self.cart_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def setup_cart_buttons(self, parent):
        bar = ttk.Frame(parent)
        bar.pack(fill="x", pady=(5, 0))
        ttk.Button(bar, text="Remove Item", command=self.remove_from_cart).pack(side="left", padx=5)
        ttk.Button(bar, text="Clear Cart", command=self.clear_cart).pack(side="left", padx=5)

    def setup_summary_panel(self, parent):
        summary = ttk.LabelFrame(parent, text="Order Summary", padding=15)
        summary.pack(fill="x", pady=(0, 10))

        self.items_count_var = tk.StringVar(value="0")
        self.subtotal_var = tk.StringVar(value="$0.00")
        self.tax_var = tk.StringVar(value="$0.00")
        self.total_var = tk.StringVar(value="$0.00")

        rows = [
            ("Items:", self.items_count_var),
            ("Subtotal:", self.subtotal_var),
            (f"Tax ({TAX_RATE*100:.0f}%):", self.tax_var),
        ]

        for i, (label, var) in enumerate(rows):
            ttk.Label(summary, text=label).grid(row=i, column=0, sticky="w", pady=3)
            ttk.Label(summary, textvariable=var).grid(row=i, column=1, sticky="e", pady=3)

        ttk.Separator(summary, orient="horizontal").grid(row=len(rows), column=0, columnspan=2,
                                                          sticky="ew", pady=8)

        ttk.Label(summary, text="TOTAL:", font=("Helvetica", 14, "bold")).grid(
            row=len(rows)+1, column=0, sticky="w")
        ttk.Label(summary, textvariable=self.total_var, font=("Helvetica", 14, "bold")).grid(
            row=len(rows)+1, column=1, sticky="e")

        summary.columnconfigure(1, weight=1)

        # Payment method
        pay_frame = ttk.Frame(parent)
        pay_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(pay_frame, text="Payment:").pack(side="left", padx=(0, 5))
        self.payment_var = tk.StringVar(value="Cash")
        ttk.Combobox(pay_frame, textvariable=self.payment_var,
                     values=["Cash", "Card", "Mobile"], state="readonly",
                     width=12).pack(side="left")

        ttk.Button(parent, text="Checkout", command=self.checkout,
                   style="TButton").pack(fill="x", pady=(0, 10), ipady=8)

    def setup_recent_sales(self, parent):
        ttk.Label(parent, text="Recent Sales", font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(5, 3))

        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)

        columns = ("ID", "Date", "Items", "Total")
        self.recent_tree = ttk.Treeview(container, columns=columns, show="headings",
                                        selectmode="browse", height=6)

        widths = [45, 130, 50, 80]
        for col, w in zip(columns, widths):
            self.recent_tree.heading(col, text=col)
            self.recent_tree.column(col, width=w, anchor="center")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.recent_tree.yview)
        self.recent_tree.configure(yscrollcommand=scrollbar.set)
        self.recent_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.recent_tree.bind("<Double-1>", lambda e: self.view_receipt())
        self.refresh_recent_sales()

    # ── Cart Logic ──────────────────────────────────────────────────

    def add_to_cart(self):
        search = self.product_entry_var.get().strip()
        if not search:
            return

        try:
            qty = int(self.qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Quantity", "Quantity must be a positive integer.")
            return

        # Try barcode first, then name search
        product = database.get_product_by_barcode(search)
        if not product:
            results = database.search_products(keyword=search)
            if len(results) == 1:
                product = results[0]
            elif len(results) > 1:
                self._show_product_picker(results, qty)
                return
            else:
                messagebox.showwarning("Not Found", f"No product found for '{search}'.")
                return

        self._add_product_to_cart(product, qty)

    def _show_product_picker(self, products, qty):
        dialog = tk.Toplevel(self.frame.winfo_toplevel())
        dialog.title("Select Product")
        dialog.geometry("400x300")
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(dialog, text="Multiple products found. Select one:", padding=10).pack(anchor="w")

        listbox = tk.Listbox(dialog, font=("Helvetica", 11))
        listbox.pack(fill="both", expand=True, padx=10, pady=5)

        product_list = list(products)
        for p in product_list:
            listbox.insert("end", f"{p['name']} - ${p['price']:.2f} (Stock: {p['stock']})")

        def select():
            sel = listbox.curselection()
            if sel:
                self._add_product_to_cart(product_list[sel[0]], qty)
                dialog.destroy()

        ttk.Button(dialog, text="Select", command=select).pack(pady=10)

    def _add_product_to_cart(self, product, qty):
        # Check if already in cart
        for item in self.cart:
            if item["product_id"] == product["id"]:
                new_qty = item["quantity"] + qty
                if new_qty > product["stock"]:
                    messagebox.showwarning("Insufficient Stock",
                                           f"Only {product['stock']} available for '{product['name']}'.")
                    return
                item["quantity"] = new_qty
                item["subtotal"] = product["price"] * new_qty
                self.update_cart_display()
                self.product_entry_var.set("")
                self.qty_var.set("1")
                return

        if qty > product["stock"]:
            messagebox.showwarning("Insufficient Stock",
                                   f"Only {product['stock']} available for '{product['name']}'.")
            return

        self.cart.append({
            "product_id": product["id"],
            "name": product["name"],
            "price": product["price"],
            "quantity": qty,
            "subtotal": product["price"] * qty,
        })
        self.update_cart_display()
        self.product_entry_var.set("")
        self.qty_var.set("1")

    def remove_from_cart(self):
        selected = self.cart_tree.selection()
        if not selected:
            return
        idx = self.cart_tree.index(selected[0])
        self.cart.pop(idx)
        self.update_cart_display()

    def clear_cart(self):
        self.cart.clear()
        self.update_cart_display()

    def update_cart_display(self):
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)

        for i, item in enumerate(self.cart, 1):
            self.cart_tree.insert("", "end", values=(
                i, item["name"], f"${item['price']:.2f}",
                item["quantity"], f"${item['subtotal']:.2f}"
            ))

        totals = self.calculate_totals()
        self.items_count_var.set(str(totals["item_count"]))
        self.subtotal_var.set(f"${totals['subtotal']:.2f}")
        self.tax_var.set(f"${totals['tax']:.2f}")
        self.total_var.set(f"${totals['total']:.2f}")

    def calculate_totals(self):
        subtotal = sum(item["subtotal"] for item in self.cart)
        tax = subtotal * TAX_RATE
        total = subtotal + tax
        item_count = sum(item["quantity"] for item in self.cart)
        return {
            "subtotal": round(subtotal, 2),
            "tax": round(tax, 2),
            "total": round(total, 2),
            "item_count": item_count,
        }

    # ── Checkout ────────────────────────────────────────────────────

    def checkout(self):
        if not self.cart:
            messagebox.showwarning("Empty Cart", "Add items to cart before checkout.")
            return

        totals = self.calculate_totals()
        confirm = messagebox.askyesno(
            "Confirm Checkout",
            f"Total: ${totals['total']:.2f}\nPayment: {self.payment_var.get()}\n\nProceed?"
        )
        if not confirm:
            return

        items = [{"product_id": item["product_id"], "quantity": item["quantity"]}
                 for item in self.cart]

        try:
            sale_id = database.create_sale(items, self.payment_var.get())
            self.cart.clear()
            self.update_cart_display()
            self.refresh_recent_sales()
            ReceiptViewer(self.frame.winfo_toplevel(), sale_id, totals["tax"])
        except ValueError as e:
            messagebox.showerror("Checkout Failed", str(e))

    # ── Recent Sales ────────────────────────────────────────────────

    def refresh_recent_sales(self):
        for row in self.recent_tree.get_children():
            self.recent_tree.delete(row)

        sales = database.get_recent_sales(20)
        for s in sales:
            date_str = s["created_at"][:16] if s["created_at"] else ""
            self.recent_tree.insert("", "end", values=(
                f"#{s['id']}", date_str, s["item_count"], f"${s['total']:.2f}"
            ))

    def view_receipt(self):
        selected = self.recent_tree.selection()
        if not selected:
            return
        values = self.recent_tree.item(selected[0], "values")
        sale_id = int(values[0].replace("#", ""))
        ReceiptViewer(self.frame.winfo_toplevel(), sale_id)
