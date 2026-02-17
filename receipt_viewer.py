import tkinter as tk
from tkinter import ttk
import database


class ReceiptViewer:
    def __init__(self, parent, sale_id, tax_amount=None):
        self.window = tk.Toplevel(parent)
        self.window.title(f"Receipt - Sale #{sale_id}")
        self.window.geometry("420x520")
        self.window.transient(parent)
        self.window.resizable(False, False)

        self.sale_id = sale_id
        self.tax_amount = tax_amount
        self.receipt_text = ""

        self.display_receipt()

    def display_receipt(self):
        sale, items = database.get_sale_details(self.sale_id)
        if not sale:
            return

        text_widget = tk.Text(self.window, font=("Courier", 11), wrap="none",
                              padx=15, pady=15, bg="#fffff0")
        text_widget.pack(fill="both", expand=True)

        lines = []
        w = 40  # receipt width in chars

        lines.append("=" * w)
        lines.append("SUPERMARKET".center(w))
        lines.append("Management System".center(w))
        lines.append("=" * w)
        lines.append("")

        date_str = sale["created_at"][:19] if sale["created_at"] else "N/A"
        lines.append(f"  Date:    {date_str}")
        lines.append(f"  Receipt: #{sale['id']}")
        lines.append(f"  Payment: {sale['payment_method']}")
        lines.append("")
        lines.append("-" * w)
        lines.append(f"  {'Item':<18} {'Qty':>4} {'Price':>7} {'Sub':>7}")
        lines.append("-" * w)

        subtotal = 0.0
        for item in items:
            name = item["product_name"][:18]
            qty = item["quantity"]
            price = item["unit_price"]
            sub = item["subtotal"]
            subtotal += sub
            lines.append(f"  {name:<18} {qty:>4} {price:>7.2f} {sub:>7.2f}")

        lines.append("-" * w)

        tax = self.tax_amount if self.tax_amount is not None else subtotal * 0.05

        lines.append(f"  {'Subtotal:':<26} ${subtotal:>8.2f}")
        lines.append(f"  {'Tax:':<26} ${tax:>8.2f}")
        lines.append(f"  {'TOTAL:':<26} ${sale['total'] + tax:>8.2f}" if self.tax_amount else
                      f"  {'TOTAL:':<26} ${sale['total']:>8.2f}")
        lines.append("")
        lines.append("=" * w)
        lines.append("Thank you for shopping!".center(w))
        lines.append("=" * w)

        self.receipt_text = "\n".join(lines)
        text_widget.insert("1.0", self.receipt_text)
        text_widget.config(state="disabled")

        btn_frame = ttk.Frame(self.window, padding=10)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Copy to Clipboard", command=self.copy_receipt).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=self.window.destroy).pack(side="right", padx=5)

    def copy_receipt(self):
        self.window.clipboard_clear()
        self.window.clipboard_append(self.receipt_text)
