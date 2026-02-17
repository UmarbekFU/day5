import tkinter as tk
from tkinter import ttk, messagebox
import database


class SupplierTab:
    def __init__(self, parent_notebook):
        self.frame = ttk.Frame(parent_notebook)
        self.selected_supplier_id = None
        self.mode = None  # "add" or "edit"

        pane = ttk.PanedWindow(self.frame, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(pane)
        right = ttk.Frame(pane)
        pane.add(left, weight=1)
        pane.add(right, weight=1)

        self.setup_supplier_list(left)
        self.setup_detail_panel(right)
        self.setup_linked_products(right)
        self.refresh()

    def setup_supplier_list(self, parent):
        ttk.Label(parent, text="Suppliers", font=("Helvetica", 12, "bold")).pack(anchor="w", pady=(0, 5))

        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True, pady=(0, 5))

        columns = ("ID", "Name", "Phone", "Email")
        self.supplier_tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="browse")

        widths = [40, 150, 100, 150]
        for col, w in zip(columns, widths):
            self.supplier_tree.heading(col, text=col)
            self.supplier_tree.column(col, width=w, anchor="w" if col != "ID" else "center")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.supplier_tree.yview)
        self.supplier_tree.configure(yscrollcommand=scrollbar.set)
        self.supplier_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.supplier_tree.bind("<<TreeviewSelect>>", self.on_supplier_select)

        btn_bar = ttk.Frame(parent)
        btn_bar.pack(fill="x")
        ttk.Button(btn_bar, text="New Supplier", command=self.new_supplier).pack(side="left", padx=5)
        ttk.Button(btn_bar, text="Delete Selected", command=self.delete_supplier).pack(side="left", padx=5)

    def setup_detail_panel(self, parent):
        detail = ttk.LabelFrame(parent, text="Supplier Details", padding=10)
        detail.pack(fill="x", pady=(0, 10))

        self.detail_vars = {}
        fields = ["Name", "Phone", "Email", "Address"]

        for i, field in enumerate(fields):
            ttk.Label(detail, text=field + ":").grid(row=i, column=0, sticky="w", pady=4, padx=(0, 10))
            var = tk.StringVar()
            entry = ttk.Entry(detail, textvariable=var, width=30)
            entry.grid(row=i, column=1, sticky="ew", pady=4)
            self.detail_vars[field.lower()] = var

        detail.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(detail)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btn_frame, text="Save", command=self.save_supplier).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel_edit).pack(side="left", padx=5)

    def setup_linked_products(self, parent):
        lf = ttk.LabelFrame(parent, text="Linked Products", padding=10)
        lf.pack(fill="both", expand=True)

        container = ttk.Frame(lf)
        container.pack(fill="both", expand=True, pady=(0, 5))

        columns = ("Product", "Price", "Supply Price")
        self.linked_tree = ttk.Treeview(container, columns=columns, show="headings",
                                        selectmode="browse", height=6)

        for col in columns:
            self.linked_tree.heading(col, text=col)
            self.linked_tree.column(col, width=120, anchor="center" if "Price" in col else "w")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.linked_tree.yview)
        self.linked_tree.configure(yscrollcommand=scrollbar.set)
        self.linked_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        btn_bar = ttk.Frame(lf)
        btn_bar.pack(fill="x")
        ttk.Button(btn_bar, text="Link Product", command=self.link_product).pack(side="left", padx=5)
        ttk.Button(btn_bar, text="Unlink Selected", command=self.unlink_product).pack(side="left", padx=5)

    # ── Actions ─────────────────────────────────────────────────────

    def refresh(self):
        for row in self.supplier_tree.get_children():
            self.supplier_tree.delete(row)

        for s in database.get_all_suppliers():
            self.supplier_tree.insert("", "end", values=(
                s["id"], s["name"], s["phone"] or "", s["email"] or ""
            ))

    def on_supplier_select(self, event):
        selected = self.supplier_tree.selection()
        if not selected:
            return

        values = self.supplier_tree.item(selected[0], "values")
        self.selected_supplier_id = int(values[0])
        supplier = database.get_supplier_by_id(self.selected_supplier_id)
        if not supplier:
            return

        self.mode = "edit"
        self.detail_vars["name"].set(supplier["name"])
        self.detail_vars["phone"].set(supplier["phone"] or "")
        self.detail_vars["email"].set(supplier["email"] or "")
        self.detail_vars["address"].set(supplier["address"] or "")

        self.refresh_linked_products()

    def refresh_linked_products(self):
        for row in self.linked_tree.get_children():
            self.linked_tree.delete(row)

        if not self.selected_supplier_id:
            return

        products = database.get_supplier_products(self.selected_supplier_id)
        for p in products:
            supply_price = f"${p['supply_price']:.2f}" if p["supply_price"] else "N/A"
            self.linked_tree.insert("", "end", iid=str(p["id"]), values=(
                p["name"], f"${p['price']:.2f}", supply_price
            ))

    def new_supplier(self):
        self.mode = "add"
        self.selected_supplier_id = None
        for var in self.detail_vars.values():
            var.set("")
        for row in self.linked_tree.get_children():
            self.linked_tree.delete(row)

    def save_supplier(self):
        name = self.detail_vars["name"].get().strip()
        if not name:
            messagebox.showerror("Validation Error", "Supplier name is required.")
            return

        phone = self.detail_vars["phone"].get().strip()
        email = self.detail_vars["email"].get().strip()
        address = self.detail_vars["address"].get().strip()

        if self.mode == "add":
            new_id = database.add_supplier(name, phone, email, address)
            self.selected_supplier_id = new_id
            self.mode = "edit"
        elif self.mode == "edit" and self.selected_supplier_id:
            database.update_supplier(self.selected_supplier_id,
                                     name=name, phone=phone, email=email, address=address)

        self.refresh()

    def cancel_edit(self):
        self.mode = None
        self.selected_supplier_id = None
        for var in self.detail_vars.values():
            var.set("")
        for row in self.linked_tree.get_children():
            self.linked_tree.delete(row)

    def delete_supplier(self):
        selected = self.supplier_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a supplier to delete.")
            return

        values = self.supplier_tree.item(selected[0], "values")
        name = values[1]
        if messagebox.askyesno("Confirm Delete", f"Delete supplier '{name}'?"):
            database.delete_supplier(int(values[0]))
            self.cancel_edit()
            self.refresh()

    def link_product(self):
        if not self.selected_supplier_id:
            messagebox.showwarning("No Supplier", "Select or create a supplier first.")
            return

        dialog = tk.Toplevel(self.frame.winfo_toplevel())
        dialog.title("Link Product")
        dialog.geometry("350x200")
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill="both", expand=True)

        products = database.get_all_products()
        product_map = {f"{p['name']} ({p['barcode'] or 'N/A'})": p["id"] for p in products}

        ttk.Label(frame, text="Product:").grid(row=0, column=0, sticky="w", pady=5)
        product_var = tk.StringVar()
        product_combo = ttk.Combobox(frame, textvariable=product_var,
                                     values=list(product_map.keys()), state="readonly", width=30)
        product_combo.grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="Supply Price:").grid(row=1, column=0, sticky="w", pady=5)
        price_var = tk.StringVar(value="0.00")
        ttk.Entry(frame, textvariable=price_var, width=15).grid(row=1, column=1, sticky="w", pady=5)

        def save():
            selected_name = product_var.get()
            product_id = product_map.get(selected_name)
            if not product_id:
                messagebox.showerror("Error", "Please select a product.", parent=dialog)
                return
            try:
                supply_price = float(price_var.get())
            except ValueError:
                messagebox.showerror("Error", "Supply price must be a number.", parent=dialog)
                return

            database.link_supplier_product(self.selected_supplier_id, product_id, supply_price)
            dialog.destroy()
            self.refresh_linked_products()

        ttk.Button(frame, text="Link", command=save).grid(row=2, column=1, sticky="e", pady=15)

    def unlink_product(self):
        if not self.selected_supplier_id:
            return
        selected = self.linked_tree.selection()
        if not selected:
            return

        product_id = int(selected[0])
        database.unlink_supplier_product(self.selected_supplier_id, product_id)
        self.refresh_linked_products()
