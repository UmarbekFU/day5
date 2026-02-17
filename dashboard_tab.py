import tkinter as tk
from tkinter import ttk
import database


class DashboardTab:
    def __init__(self, parent_notebook):
        self.frame = ttk.Frame(parent_notebook)
        self.stat_labels = {}

        self.setup_header()
        self.setup_stat_cards()
        self.setup_tables()
        self.setup_refresh_button()
        self.refresh()

    def setup_header(self):
        ttk.Label(self.frame, text="Dashboard", style="Header.TLabel").pack(
            anchor="w", padx=15, pady=(10, 5))

    def setup_stat_cards(self):
        cards_frame = ttk.Frame(self.frame)
        cards_frame.pack(fill="x", padx=10, pady=10)

        card_defs = [
            ("total_products", "Total Products", "#2196F3"),
            ("total_categories", "Categories", "#4CAF50"),
            ("low_stock_count", "Low Stock Alerts", "#FF9800"),
            ("today_revenue", "Today's Revenue", "#9C27B0"),
        ]

        for i, (key, desc, color) in enumerate(card_defs):
            card = ttk.LabelFrame(cards_frame, text="", padding=15)
            card.grid(row=0, column=i, padx=8, pady=5, sticky="nsew")

            if key == "low_stock_count":
                value_label = ttk.Label(card, text="0", style="Alert.Stat.TLabel")
            elif key == "today_revenue":
                value_label = ttk.Label(card, text="$0.00", style="Stat.TLabel")
            else:
                value_label = ttk.Label(card, text="0", style="Stat.TLabel")

            value_label.pack()
            ttk.Label(card, text=desc, style="StatDesc.TLabel").pack(pady=(5, 0))
            self.stat_labels[key] = value_label

        for i in range(4):
            cards_frame.columnconfigure(i, weight=1)

    def setup_tables(self):
        tables_frame = ttk.Frame(self.frame)
        tables_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Left: Low stock alerts
        left = ttk.LabelFrame(tables_frame, text="Low Stock Alerts", padding=5)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        columns_l = ("Product", "Stock", "Threshold")
        self.low_stock_tree = ttk.Treeview(left, columns=columns_l, show="headings",
                                           selectmode="browse", height=10)
        for col in columns_l:
            self.low_stock_tree.heading(col, text=col)
            w = 60 if col != "Product" else 180
            self.low_stock_tree.column(col, width=w, anchor="center" if col != "Product" else "w")

        self.low_stock_tree.tag_configure("critical", background="#ffcccc")
        self.low_stock_tree.tag_configure("warning", background="#fff3cd")

        scroll_l = ttk.Scrollbar(left, orient="vertical", command=self.low_stock_tree.yview)
        self.low_stock_tree.configure(yscrollcommand=scroll_l.set)
        self.low_stock_tree.pack(side="left", fill="both", expand=True)
        scroll_l.pack(side="right", fill="y")

        # Right: Recent sales
        right = ttk.LabelFrame(tables_frame, text="Recent Sales", padding=5)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        columns_r = ("Sale #", "Date", "Items", "Total", "Payment")
        self.recent_tree = ttk.Treeview(right, columns=columns_r, show="headings",
                                        selectmode="browse", height=10)
        widths_r = [55, 120, 50, 75, 70]
        for col, w in zip(columns_r, widths_r):
            self.recent_tree.heading(col, text=col)
            self.recent_tree.column(col, width=w, anchor="center")

        scroll_r = ttk.Scrollbar(right, orient="vertical", command=self.recent_tree.yview)
        self.recent_tree.configure(yscrollcommand=scroll_r.set)
        self.recent_tree.pack(side="left", fill="both", expand=True)
        scroll_r.pack(side="right", fill="y")

        tables_frame.columnconfigure(0, weight=1)
        tables_frame.columnconfigure(1, weight=1)
        tables_frame.rowconfigure(0, weight=1)

    def setup_refresh_button(self):
        ttk.Button(self.frame, text="Refresh", command=self.refresh).pack(
            anchor="e", padx=15, pady=(5, 10))

    def refresh(self):
        stats = database.get_dashboard_stats()

        self.stat_labels["total_products"].config(text=str(stats["total_products"]))
        self.stat_labels["total_categories"].config(text=str(stats["total_categories"]))
        self.stat_labels["low_stock_count"].config(text=str(stats["low_stock_count"]))
        self.stat_labels["today_revenue"].config(text=f"${stats['today_revenue']:.2f}")

        # Update low stock alert style
        if stats["low_stock_count"] > 0:
            self.stat_labels["low_stock_count"].configure(style="Alert.Stat.TLabel")
        else:
            self.stat_labels["low_stock_count"].configure(style="Stat.TLabel")

        # Low stock table
        for row in self.low_stock_tree.get_children():
            self.low_stock_tree.delete(row)

        low_stock = database.get_low_stock_products()
        for p in low_stock:
            tag = "critical" if p["stock"] <= p["low_stock_threshold"] // 2 else "warning"
            self.low_stock_tree.insert("", "end", values=(
                p["name"], p["stock"], p["low_stock_threshold"]
            ), tags=(tag,))

        # Recent sales table
        for row in self.recent_tree.get_children():
            self.recent_tree.delete(row)

        sales = database.get_recent_sales(10)
        for s in sales:
            date_str = s["created_at"][:16] if s["created_at"] else ""
            self.recent_tree.insert("", "end", values=(
                f"#{s['id']}", date_str, s["item_count"],
                f"${s['total']:.2f}", s["payment_method"]
            ))
