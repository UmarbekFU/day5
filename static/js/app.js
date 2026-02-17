// ── Toast Notifications ─────────────────────────────────────────

function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast align-items-center text-bg-${type} border-0`;
    toast.setAttribute("role", "alert");
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>`;
    container.appendChild(toast);
    new bootstrap.Toast(toast, { delay: 3000 }).show();
    toast.addEventListener("hidden.bs.toast", () => toast.remove());
}

// ── Sidebar Toggle (Mobile) ────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");
    if (toggle && sidebar) {
        toggle.addEventListener("click", () => sidebar.classList.toggle("show"));
        document.addEventListener("click", (e) => {
            if (sidebar.classList.contains("show") &&
                !sidebar.contains(e.target) && !toggle.contains(e.target)) {
                sidebar.classList.remove("show");
            }
        });
    }
});

// ── Inventory: Product CRUD ─────────────────────────────────────

function openProductModal(productId = null) {
    const form = document.getElementById("productForm");
    if (!form) return;
    form.reset();
    document.getElementById("product-id").value = "";
    document.getElementById("productModalLabel").textContent = productId ? "Edit Product" : "Add Product";

    if (productId) {
        fetch(`/api/products/${productId}`)
            .then(r => r.json())
            .then(p => {
                document.getElementById("product-id").value = p.id;
                document.getElementById("product-name").value = p.name;
                document.getElementById("product-barcode").value = p.barcode || "";
                document.getElementById("product-category").value = p.category_id || "";
                document.getElementById("product-price").value = p.price;
                document.getElementById("product-cost").value = p.cost_price;
                document.getElementById("product-stock").value = p.stock;
                document.getElementById("product-threshold").value = p.low_stock_threshold;
                new bootstrap.Modal(document.getElementById("productModal")).show();
            });
    } else {
        new bootstrap.Modal(document.getElementById("productModal")).show();
    }
}

async function saveProduct() {
    const productId = document.getElementById("product-id").value;
    const payload = {
        name: document.getElementById("product-name").value.trim(),
        barcode: document.getElementById("product-barcode").value.trim() || null,
        category_id: document.getElementById("product-category").value || null,
        price: parseFloat(document.getElementById("product-price").value),
        cost_price: parseFloat(document.getElementById("product-cost").value),
        stock: parseInt(document.getElementById("product-stock").value),
        low_stock_threshold: parseInt(document.getElementById("product-threshold").value),
    };

    if (!payload.name) { showToast("Product name is required", "warning"); return; }
    if (isNaN(payload.price) || payload.price < 0) { showToast("Invalid price", "warning"); return; }

    const url = productId ? `/api/products/${productId}` : "/api/products";
    const method = productId ? "PUT" : "POST";

    const resp = await fetch(url, {
        method, headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (data.success) {
        bootstrap.Modal.getInstance(document.getElementById("productModal")).hide();
        showToast(productId ? "Product updated" : "Product added", "success");
        setTimeout(() => location.reload(), 500);
    } else {
        showToast(data.error || "Failed to save", "danger");
    }
}

async function deleteProduct(productId, name) {
    if (!confirm(`Delete "${name}"?`)) return;
    const resp = await fetch(`/api/products/${productId}`, { method: "DELETE" });
    const data = await resp.json();
    if (data.success) {
        showToast("Product deleted", "success");
        setTimeout(() => location.reload(), 500);
    } else {
        showToast(data.error || "Failed to delete", "danger");
    }
}

// ── Inventory: Category Management ──────────────────────────────

async function addCategory() {
    const input = document.getElementById("new-category-name");
    const name = input.value.trim();
    if (!name) return;

    const resp = await fetch("/api/categories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
    });
    const data = await resp.json();
    if (data.success) {
        input.value = "";
        refreshCategoryList();
        showToast("Category added", "success");
    } else {
        showToast(data.error || "Failed to add", "danger");
    }
}

async function deleteCategory(categoryId) {
    if (!confirm("Delete this category? Products will become uncategorized.")) return;
    const resp = await fetch(`/api/categories/${categoryId}`, { method: "DELETE" });
    const data = await resp.json();
    if (data.success) {
        refreshCategoryList();
        showToast("Category deleted", "success");
    }
}

async function refreshCategoryList() {
    const resp = await fetch("/api/categories");
    const categories = await resp.json();
    const list = document.getElementById("category-list");
    if (!list) return;

    list.innerHTML = "";
    categories.forEach(c => {
        const li = document.createElement("li");
        li.className = "list-group-item d-flex justify-content-between align-items-center";
        li.innerHTML = `
            ${c.name}
            <button class="btn btn-sm btn-outline-danger" onclick="deleteCategory(${c.id})">
                <i class="bi bi-trash"></i>
            </button>`;
        list.appendChild(li);
    });

    // Also update the filter dropdown and modal dropdown
    const filterSelect = document.getElementById("filter-category");
    const productSelect = document.getElementById("product-category");
    [filterSelect, productSelect].forEach(sel => {
        if (!sel) return;
        const current = sel.value;
        const firstOpt = sel.querySelector("option:first-child");
        sel.innerHTML = "";
        if (firstOpt) sel.appendChild(firstOpt);
        categories.forEach(c => {
            const opt = document.createElement("option");
            opt.value = c.id;
            opt.textContent = c.name;
            sel.appendChild(opt);
        });
        sel.value = current;
    });
}

// ── Sales: Cart ─────────────────────────────────────────────────

async function addToCart() {
    const input = document.getElementById("product-search");
    const qtyInput = document.getElementById("cart-qty");
    if (!input) return;

    const query = input.value.trim();
    const qty = parseInt(qtyInput.value) || 1;
    if (!query) return;

    const resp = await fetch(`/api/products/search?q=${encodeURIComponent(query)}`);
    const products = await resp.json();

    if (products.length === 0) {
        showToast("No product found", "warning");
    } else if (products.length === 1) {
        await doAddToCart(products[0].id, qty);
    } else {
        showProductPicker(products, qty);
    }
}

function showProductPicker(products, qty) {
    const list = document.getElementById("picker-list");
    if (!list) return;
    list.innerHTML = "";
    products.forEach(p => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "list-group-item list-group-item-action d-flex justify-content-between";
        btn.innerHTML = `
            <span>${p.name}</span>
            <span class="text-muted">$${p.price.toFixed(2)} (Stock: ${p.stock})</span>`;
        btn.addEventListener("click", () => {
            doAddToCart(p.id, qty);
            bootstrap.Modal.getInstance(document.getElementById("pickerModal")).hide();
        });
        list.appendChild(btn);
    });
    new bootstrap.Modal(document.getElementById("pickerModal")).show();
}

async function doAddToCart(productId, quantity) {
    const resp = await fetch("/api/cart/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, quantity }),
    });
    const data = await resp.json();
    if (data.success) {
        refreshCartDisplay(data.cart, data.totals);
        document.getElementById("product-search").value = "";
        document.getElementById("cart-qty").value = "1";
        document.getElementById("product-search").focus();
    } else {
        showToast(data.error, "danger");
    }
}

async function removeFromCart(index) {
    const resp = await fetch("/api/cart/remove", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ index }),
    });
    const data = await resp.json();
    if (data.success) refreshCartDisplay(data.cart, data.totals);
}

async function clearCart() {
    if (!confirm("Clear entire cart?")) return;
    const resp = await fetch("/api/cart/clear", { method: "POST" });
    const data = await resp.json();
    if (data.success) refreshCartDisplay(data.cart, data.totals);
}

function refreshCartDisplay(cart, totals) {
    const tbody = document.getElementById("cart-body");
    const emptyState = document.getElementById("cart-empty");
    if (!tbody) return;

    tbody.innerHTML = "";
    if (cart.length === 0) {
        if (emptyState) emptyState.style.display = "";
    } else {
        if (emptyState) emptyState.style.display = "none";
        cart.forEach((item, i) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>${i + 1}</td>
                <td>${item.name}</td>
                <td>$${item.price.toFixed(2)}</td>
                <td>${item.quantity}</td>
                <td>$${item.subtotal.toFixed(2)}</td>
                <td>
                    <button class="btn btn-sm btn-outline-danger btn-action" onclick="removeFromCart(${i})">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </td>`;
            tbody.appendChild(tr);
        });
    }

    document.getElementById("summary-items").textContent = totals.item_count;
    document.getElementById("summary-subtotal").textContent = `$${totals.subtotal.toFixed(2)}`;
    document.getElementById("summary-tax").textContent = `$${totals.tax.toFixed(2)}`;
    document.getElementById("summary-total").textContent = `$${totals.total.toFixed(2)}`;
}

async function checkout() {
    const cartBody = document.getElementById("cart-body");
    if (!cartBody || cartBody.children.length === 0) {
        showToast("Cart is empty", "warning");
        return;
    }

    const paymentMethod = document.getElementById("payment-method").value;
    if (!confirm(`Complete checkout? (${paymentMethod})`)) return;

    const resp = await fetch("/api/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ payment_method: paymentMethod }),
    });
    const data = await resp.json();
    if (data.success) {
        refreshCartDisplay([], { item_count: 0, subtotal: 0, tax: 0, total: 0 });
        showToast("Sale completed!", "success");
        window.open(`/receipt/${data.sale_id}`, "_blank");
        setTimeout(() => location.reload(), 1000);
    } else {
        showToast(data.error, "danger");
    }
}

// ── Suppliers ───────────────────────────────────────────────────

async function saveSupplier() {
    const idField = document.getElementById("supplier-id");
    const supplierId = idField ? idField.value : "";
    const payload = {
        name: document.getElementById("supplier-name").value.trim(),
        phone: document.getElementById("supplier-phone").value.trim(),
        email: document.getElementById("supplier-email").value.trim(),
        address: document.getElementById("supplier-address").value.trim(),
    };

    if (!payload.name) { showToast("Supplier name is required", "warning"); return; }

    const url = supplierId ? `/api/suppliers/${supplierId}` : "/api/suppliers";
    const method = supplierId ? "PUT" : "POST";

    const resp = await fetch(url, {
        method, headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (data.success) {
        showToast(supplierId ? "Supplier updated" : "Supplier added", "success");
        const newId = supplierId || data.id;
        setTimeout(() => window.location.href = `/suppliers/${newId}`, 500);
    } else {
        showToast(data.error || "Failed to save", "danger");
    }
}

async function deleteSupplier(supplierId, name) {
    if (!confirm(`Delete supplier "${name}"?`)) return;
    const resp = await fetch(`/api/suppliers/${supplierId}`, { method: "DELETE" });
    const data = await resp.json();
    if (data.success) {
        showToast("Supplier deleted", "success");
        setTimeout(() => window.location.href = "/suppliers", 500);
    }
}

async function linkProduct(supplierId) {
    const productId = document.getElementById("link-product-id").value;
    const supplyPrice = parseFloat(document.getElementById("link-supply-price").value) || 0;
    if (!productId) { showToast("Select a product", "warning"); return; }

    const resp = await fetch(`/api/suppliers/${supplierId}/products`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, supply_price: supplyPrice }),
    });
    const data = await resp.json();
    if (data.success) {
        bootstrap.Modal.getInstance(document.getElementById("linkProductModal")).hide();
        showToast("Product linked", "success");
        setTimeout(() => location.reload(), 500);
    } else {
        showToast(data.error || "Failed to link", "danger");
    }
}

async function unlinkProduct(supplierId, productId) {
    if (!confirm("Unlink this product?")) return;
    const resp = await fetch(`/api/suppliers/${supplierId}/products/${productId}`, { method: "DELETE" });
    const data = await resp.json();
    if (data.success) {
        showToast("Product unlinked", "success");
        setTimeout(() => location.reload(), 500);
    }
}
