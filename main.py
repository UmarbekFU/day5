import tkinter as tk
from tkinter import ttk

import database
from dashboard_tab import DashboardTab
from inventory_tab import InventoryTab
from sales_tab import SalesTab
from supplier_tab import SupplierTab


class SupermarketApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Supermarket Management System")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)

        database.init_db()
        database.seed_sample_data()

        self.setup_styles()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.dashboard_tab = DashboardTab(self.notebook)
        self.inventory_tab = InventoryTab(self.notebook)
        self.sales_tab = SalesTab(self.notebook)
        self.supplier_tab = SupplierTab(self.notebook)

        self.notebook.add(self.dashboard_tab.frame, text="  Dashboard  ")
        self.notebook.add(self.inventory_tab.frame, text="  Inventory  ")
        self.notebook.add(self.sales_tab.frame, text="  Sales & Billing  ")
        self.notebook.add(self.supplier_tab.frame, text="  Suppliers  ")

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
        style.configure("Treeview", rowheight=28, font=("Helvetica", 10))
        style.configure("TLabel", font=("Helvetica", 10))
        style.configure("TButton", font=("Helvetica", 10), padding=5)
        style.configure("Header.TLabel", font=("Helvetica", 22, "bold"))
        style.configure("SubHeader.TLabel", font=("Helvetica", 11))
        style.configure("Stat.TLabel", font=("Helvetica", 28, "bold"))
        style.configure("StatDesc.TLabel", font=("Helvetica", 10), foreground="#555555")
        style.configure("Alert.Stat.TLabel", font=("Helvetica", 28, "bold"), foreground="#cc0000")

    def on_tab_changed(self, event):
        selected = self.notebook.index(self.notebook.select())
        if selected == 0:
            self.dashboard_tab.refresh()
        elif selected == 1:
            self.inventory_tab.refresh()


if __name__ == "__main__":
    root = tk.Tk()
    app = SupermarketApp(root)
    root.mainloop()
