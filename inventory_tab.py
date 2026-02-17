import tkinter as tk
from tkinter import ttk, messagebox
import database


class InventoryTab:
    def __init__(self, parent_notebook):
        self.frame = ttk.Frame(parent_notebook)
        self.setup_search_bar()
        self.setup_treeview()
        self.setup_buttons()
        self.refresh()

    def setup_search_bar(self):
        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=10, pady=(10, 5))

        ttk.Label(bar, text="Search:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(bar, textvariable=self.search_var, width=25)
        search_entry.pack(side="left", padx=(0, 10))
        search_entry.bind("<Return>", lambda e: self.search_products())

        ttk.Label(bar, text="Category:").pack(side="left", padx=(0, 5))
        self.category_var = tk.StringVar(value="All")
        self.category_combo = ttk.Combobox(bar, textvariable=self.category_var,
                                           state="readonly", width=18)
        self.category_combo.pack(side="left", padx=(0, 10))
        self.load_categories_combo()

        ttk.Button(bar, text="Search", command=self.search_products).pack(side="left", padx=2)
        ttk.Button(bar, text="Clear", command=self.clear_search).pack(side="left", padx=2)

    def setup_treeview(self):
        container = ttk.Frame(self.frame)
        container.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("ID", "Name", "Barcode", "Category", "Price", "Cost", "Stock", "Threshold")
        self.tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")

        widths = [50, 180, 100, 120, 80, 80, 70, 80]
        for col, w in zip(columns, widths):
            self.tree.heading(col, text=col)
            anchor = "center" if col in ("ID", "Price", "Cost", "Stock", "Threshold") else "w"
            self.tree.column(col, width=w, anchor=anchor)

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.tag_configure("low_stock", background="#ffcccc")
        self.tree.tag_configure("even", background="#f5f5f5")

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self.edit_product())

    def setup_buttons(self):
        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=10, pady=(5, 10))

        ttk.Button(bar, text="Add Product", command=self.add_product).pack(side="left", padx=5)
        ttk.Button(bar, text="Edit Selected", command=self.edit_product).pack(side="left", padx=5)
        ttk.Button(bar, text="Delete Selected", command=self.delete_product).pack(side="left", padx=5)
        ttk.Button(bar, text="Manage Categories", command=self.manage_categories).pack(side="right", padx=5)

    def load_categories_combo(self):
        categories = database.get_all_categories()
        names = ["All"] + [c["name"] for c in categories]
        self.category_combo["values"] = names

    def refresh(self):
        self.load_categories_combo()
        for row in self.tree.get_children():
            self.tree.delete(row)

        products = database.get_all_products()
        for i, p in enumerate(products):
            tags = []
            if p["stock"] <= p["low_stock_threshold"]:
                tags.append("low_stock")
            elif i % 2 == 0:
                tags.append("even")

            self.tree.insert("", "end", values=(
                p["id"], p["name"], p["barcode"] or "",
                p["category_name"] or "", f"${p['price']:.2f}",
                f"${p['cost_price']:.2f}", p["stock"], p["low_stock_threshold"]
            ), tags=tags)

    def search_products(self):
        keyword = self.search_var.get().strip()
        category_name = self.category_var.get()
        category_id = None
        if category_name != "All":
            cats = database.get_all_categories()
            for c in cats:
                if c["name"] == category_name:
                    category_id = c["id"]
                    break

        for row in self.tree.get_children():
            self.tree.delete(row)

        products = database.search_products(keyword, category_id)
        for i, p in enumerate(products):
            tags = []
            if p["stock"] <= p["low_stock_threshold"]:
                tags.append("low_stock")
            elif i % 2 == 0:
                tags.append("even")

            self.tree.insert("", "end", values=(
                p["id"], p["name"], p["barcode"] or "",
                p["category_name"] or "", f"${p['price']:.2f}",
                f"${p['cost_price']:.2f}", p["stock"], p["low_stock_threshold"]
            ), tags=tags)

    def clear_search(self):
        self.search_var.set("")
        self.category_var.set("All")
        self.refresh()

    def add_product(self):
        self._open_product_dialog("Add Product")

    def edit_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a product to edit.")
            return
        values = self.tree.item(selected[0], "values")
        product_id = int(values[0])
        product = database.get_product_by_id(product_id)
        if product:
            self._open_product_dialog("Edit Product", product)

    def delete_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a product to delete.")
            return
        values = self.tree.item(selected[0], "values")
        name = values[1]
        if messagebox.askyesno("Confirm Delete", f"Delete product '{name}'?"):
            database.delete_product(int(values[0]))
            self.refresh()

    def _open_product_dialog(self, title, product=None):
        dialog = tk.Toplevel(self.frame.winfo_toplevel())
        dialog.title(title)
        dialog.geometry("400x380")
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()
        dialog.resizable(False, False)

        fields_frame = ttk.Frame(dialog, padding=15)
        fields_frame.pack(fill="both", expand=True)

        categories = database.get_all_categories()
        cat_names = [c["name"] for c in categories]
        cat_map = {c["name"]: c["id"] for c in categories}

        entries = {}
        field_defs = [
            ("Name", "entry", ""),
            ("Barcode", "entry", ""),
            ("Category", "combo", cat_names),
            ("Price", "entry", "0.00"),
            ("Cost Price", "entry", "0.00"),
            ("Stock", "entry", "0"),
            ("Low Stock Threshold", "entry", "10"),
        ]

        for i, (label, ftype, default) in enumerate(field_defs):
            ttk.Label(fields_frame, text=label + ":").grid(row=i, column=0, sticky="w", pady=4, padx=(0, 10))
            if ftype == "combo":
                var = tk.StringVar()
                widget = ttk.Combobox(fields_frame, textvariable=var, values=default, state="readonly", width=25)
                entries[label] = var
            else:
                var = tk.StringVar(value=default)
                widget = ttk.Entry(fields_frame, textvariable=var, width=28)
                entries[label] = var
            widget.grid(row=i, column=1, sticky="ew", pady=4)

        if product:
            entries["Name"].set(product["name"])
            entries["Barcode"].set(product["barcode"] or "")
            entries["Category"].set(product["category_name"] or "")
            entries["Price"].set(f"{product['price']:.2f}")
            entries["Cost Price"].set(f"{product['cost_price']:.2f}")
            entries["Stock"].set(str(product["stock"]))
            entries["Low Stock Threshold"].set(str(product["low_stock_threshold"]))

        def save():
            name = entries["Name"].get().strip()
            if not name:
                messagebox.showerror("Validation Error", "Product name is required.", parent=dialog)
                return
            try:
                price = float(entries["Price"].get())
                cost = float(entries["Cost Price"].get())
                stock = int(entries["Stock"].get())
                threshold = int(entries["Low Stock Threshold"].get())
            except ValueError:
                messagebox.showerror("Validation Error",
                                     "Price, Cost, Stock, and Threshold must be valid numbers.",
                                     parent=dialog)
                return
            if price < 0 or cost < 0 or stock < 0:
                messagebox.showerror("Validation Error", "Values cannot be negative.", parent=dialog)
                return

            barcode = entries["Barcode"].get().strip() or None
            cat_name = entries["Category"].get()
            category_id = cat_map.get(cat_name)

            if product:
                database.update_product(product["id"],
                                        name=name, barcode=barcode, category_id=category_id,
                                        price=price, cost_price=cost, stock=stock,
                                        low_stock_threshold=threshold)
            else:
                database.add_product(name, barcode, category_id, price, cost, stock, threshold)

            dialog.destroy()
            self.refresh()

        btn_frame = ttk.Frame(dialog, padding=10)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Save", command=save).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)

    def manage_categories(self):
        dialog = tk.Toplevel(self.frame.winfo_toplevel())
        dialog.title("Manage Categories")
        dialog.geometry("350x400")
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()
        dialog.resizable(False, False)

        list_frame = ttk.Frame(dialog, padding=10)
        list_frame.pack(fill="both", expand=True)

        listbox = tk.Listbox(list_frame, font=("Helvetica", 11))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        cat_ids = []

        def reload():
            listbox.delete(0, "end")
            cat_ids.clear()
            for c in database.get_all_categories():
                listbox.insert("end", c["name"])
                cat_ids.append(c["id"])

        reload()

        add_frame = ttk.Frame(dialog, padding=10)
        add_frame.pack(fill="x")

        name_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=name_var, width=22).pack(side="left", padx=(0, 5))

        def add_cat():
            name = name_var.get().strip()
            if not name:
                return
            try:
                database.add_category(name)
                name_var.set("")
                reload()
            except Exception:
                messagebox.showerror("Error", "Category already exists or invalid.", parent=dialog)

        def delete_cat():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            name = listbox.get(idx)
            if messagebox.askyesno("Confirm", f"Delete category '{name}'?\nProducts in this category will become uncategorized.", parent=dialog):
                database.delete_category(cat_ids[idx])
                reload()

        ttk.Button(add_frame, text="Add", command=add_cat).pack(side="left", padx=2)
        ttk.Button(add_frame, text="Delete Selected", command=delete_cat).pack(side="left", padx=2)
