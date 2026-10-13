import streamlit as st
import csv
import io
from datetime import date, datetime
from database import (
    create_tables, add_item, get_all_items, update_item, delete_item,
    add_purchase, get_all_purchases, delete_purchase, update_purchase,
    search_purchases, get_monthly_expenditure, get_frequent_items,
    get_expiring_purchases, get_available_months, get_month_purchases,
    add_image_column, get_items_with_images, set_item_image
)
from image_service import find_food_image

create_tables()

add_image_column()

CATEGORIES = ["Dairy", "Vegetables", "Fruits", "Grains", "Snacks", "Beverages", "Meat", "Other"]
UNITS = ["kg", "g", "litre", "ml", "packet", "piece"]
page = st.sidebar.radio("Go to", ["Dashboard", "Items", "Purchases", "Search", "Report"])


# =====================================================
# PAGE 1: ITEMS
# =====================================================
def show_item_gallery():
    items = get_items_with_images()
    if len(items) == 0:
        return

    st.header("Item Photos")
    gallery = []
    with st.spinner("Getting image..."):
        for it in items:
            url = it[4]
            if url is None:  # inka vetakaledu
                url = find_food_image(it[1]) or ""
                set_item_image(it[0], url)
            gallery.append((it[1], url))

    cols = st.columns(4)
    for i, (item_name, url) in enumerate(gallery):
        with cols[i % 4]:
            if url:
                st.image(url, caption=item_name, use_container_width=True)
            else:
                st.write(f"🖼️ {item_name}")
                st.caption("Photo dorakaledu")

def items_page():
    st.title("Items")

    st.header("Add Grocery Item")
    name = st.text_input("Item name (e.g. Milk)")
    category = st.selectbox("Category", CATEGORIES)
    unit = st.selectbox("Unit", UNITS)

    if st.button("Add Item"):
        if name.strip() == "":
            st.error("Please enter an item name.")
        else:
            add_item(name.strip(), category, unit)
            st.rerun()

    st.header("All Items")
    items = get_all_items()

    if len(items) == 0:
        st.info("No items yet. Add your first one above.")
        return

    st.table(
        {
            "ID": [r[0] for r in items],
            "Name": [r[1] for r in items],
            "Category": [r[2] for r in items],
            "Unit": [r[3] for r in items],
        }
    )
    show_item_gallery()

    st.header("Edit or Delete an Item")
    choices = {f"{r[0]} - {r[1]}": r for r in items}
    selected = st.selectbox("Choose an item", list(choices.keys()))
    row = choices[selected]

    new_name = st.text_input("Name", value=row[1], key=f"name_{row[0]}")
    new_category = st.selectbox(
        "Category", CATEGORIES,
        index=CATEGORIES.index(row[2]) if row[2] in CATEGORIES else 0,
        key=f"cat_{row[0]}"
    )
    new_unit = st.selectbox(
        "Unit", UNITS,
        index=UNITS.index(row[3]) if row[3] in UNITS else 0,
        key=f"unit_{row[0]}"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Changes"):
            if new_name.strip() == "":
                st.error("Name cannot be empty.")
            else:
                update_item(row[0], new_name.strip(), new_category, new_unit)
                set_item_image(row[0], None)
                st.rerun()
    with col2:
        if st.button("Delete Item"):
            delete_item(row[0])
            st.rerun()


# =====================================================
# PAGE 2: PURCHASES
# =====================================================
def purchases_page():
    st.title("Purchases")

    items = get_all_items()
    if len(items) == 0:
        st.info("Add some items first on the Items page.")
        return

    choices = {f"{r[0]} - {r[1]}": r for r in items}

    # ---------- Record Purchase ----------
    st.header("Record a Purchase")

    buy_choice = st.selectbox("Item bought", list(choices.keys()), key="buy_item")
    buy_row = choices[buy_choice]

    quantity = st.number_input(
        f"Quantity (in {buy_row[3]})", min_value=0.0, value=1.0, step=0.5
    )
    price = st.number_input(
        f"Price per {buy_row[3]} (₹)", min_value=0.0, value=0.0, step=1.0
    )
    purchase_date = st.date_input("Purchase date", value=date.today())

    has_expiry = st.checkbox("This item has an expiry date")
    expiry_date = None
    if has_expiry:
        expiry_date = st.date_input("Expiry date", value=date.today(), key="expiry")

    store = st.text_input("Store (optional)")

    if st.button("Save Purchase"):
        if quantity <= 0:
            st.error("Quantity must be more than 0.")
        elif price <= 0:
            st.error("Price must be more than 0.")
        elif expiry_date is not None and expiry_date < purchase_date:
            st.error("Expiry date cannot be before the purchase date.")
        else:
            add_purchase(
                buy_row[0], quantity, price,
                str(purchase_date),
                str(expiry_date) if expiry_date else None,
                store.strip(),
            )
            st.rerun()

    # ---------- Purchase History ----------
    st.header("Purchase History")
    purchases = get_all_purchases()

    if len(purchases) == 0:
        st.info("No purchases yet.")
        return

    days_left = []
    totals = []
    for p in purchases:
        totals.append(round(p[3] * p[4], 2))
        if p[6]:
            days_left.append((date.fromisoformat(p[6]) - date.today()).days)
        else:
            days_left.append("-")

    st.table(
        {
            "ID": [p[0] for p in purchases],
            "Item": [p[1] for p in purchases],
            "Qty": [f"{p[3]} {p[2]}" for p in purchases],
            "Price/unit (₹)": [p[4] for p in purchases],
            "Total (₹)": totals,
            "Bought on": [p[5] for p in purchases],
            "Expiry": [p[6] if p[6] else "-" for p in purchases],
            "Days left": days_left,
            "Store": [p[7] for p in purchases],
        }
    )

    # ---------- Edit / Delete Purchase ----------
    st.header("Edit or Delete a Purchase")

    p_choices = {f"#{p[0]} - {p[1]} ({p[5]})": p for p in purchases}
    p_selected = st.selectbox("Choose a purchase", list(p_choices.keys()))
    p = p_choices[p_selected]
    pid = p[0]

    e_qty = st.number_input("Quantity", min_value=0.0, value=float(p[3]), step=0.5, key=f"eq_{pid}")
    e_price = st.number_input("Price per unit (₹)", min_value=0.0, value=float(p[4]), step=1.0, key=f"ep_{pid}")
    e_bought = st.date_input("Purchase date", value=datetime.strptime(p[5], "%Y-%m-%d").date(), key=f"ebd_{pid}")

    e_has_expiry = st.checkbox("Has expiry date", value=bool(p[6]), key=f"ehe_{pid}")
    e_expiry = None
    if e_has_expiry:
        default_exp = datetime.strptime(p[6], "%Y-%m-%d").date() if p[6] else date.today()
        e_expiry = st.date_input("Expiry date", value=default_exp, key=f"eex_{pid}")

    e_store = st.text_input("Store", value=p[7] or "", key=f"es_{pid}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save Purchase Changes"):
            if e_qty <= 0 or e_price <= 0:
                st.error("Quantity and price must be more than 0.")
            elif e_expiry is not None and e_expiry < e_bought:
                st.error("Expiry date cannot be before the purchase date.")
            else:
                update_purchase(
                    pid, e_qty, e_price, str(e_bought),
                    str(e_expiry) if e_expiry else None,
                    e_store.strip(),
                )
                st.rerun()
    with c2:
        if st.button("Delete Purchase"):
            delete_purchase(pid)
            st.rerun()

# =====================================================
# PAGE 3: SEARCH
# =====================================================
def search_page():
    st.title("Search and Filter")

    name = st.text_input("Item name contains")
    category = st.selectbox("Category", ["All"] + CATEGORIES)

    use_dates = st.checkbox("Filter by purchase date")
    start_date = end_date = None
    if use_dates:
        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input("From", value=date.today().replace(day=1))
        with c2:
            end_date = st.date_input("To", value=date.today())

    use_price = st.checkbox("Filter by price per unit")
    min_price = max_price = None
    if use_price:
        c3, c4 = st.columns(2)
        with c3:
            min_price = st.number_input("Min price (₹)", min_value=0.0, value=0.0, step=1.0)
        with c4:
            max_price = st.number_input("Max price (₹)", min_value=0.0, value=1000.0, step=1.0)

    results = search_purchases(
        name.strip(), category,
        str(start_date) if start_date else None,
        str(end_date) if end_date else None,
        min_price, max_price,
    )

    st.subheader(f"{len(results)} record(s) found")

    if len(results) == 0:
        st.info("No matching purchases.")
        return

    total_spent = sum(r[4] * r[5] for r in results)
    st.write(f"**Total spent on these records: ₹{total_spent:,.2f}**")

    st.table(
        {
            "Item": [r[1] for r in results],
            "Category": [r[2] for r in results],
            "Qty": [f"{r[4]} {r[3]}" for r in results],
            "Price/unit (₹)": [r[5] for r in results],
            "Total (₹)": [round(r[4] * r[5], 2) for r in results],
            "Bought on": [r[6] for r in results],
            "Expiry": [r[7] if r[7] else "-" for r in results],
            "Store": [r[8] for r in results],
        }
    )

# =====================================================
# PAGE 4: DASHBOARD
# =====================================================
def dashboard_page():
    st.title("Dashboard")

    # ---------- Expiring items ----------
    st.header("⚠️ Expiring Items")
    within = st.slider("Show items expiring within (days)", 1, 30, 7)
    expiring = get_expiring_purchases(within)

    if len(expiring) == 0:
        st.success("Nothing is expiring soon.")
    else:
        expired = [r for r in expiring if r[5] <= 0 and r[4] < str(date.today())]
        if expired:
            st.error(f"{len(expired)} item(s) already expired!")

        status = []
        for r in expiring:
            days = (date.fromisoformat(r[4]) - date.today()).days
            if days < 0:
                status.append(f"Expired {abs(days)} day(s) ago")
            elif days == 0:
                status.append("Expires today")
            else:
                status.append(f"{days} day(s) left")

        st.table(
            {
                "Item": [r[0] for r in expiring],
                "Category": [r[1] for r in expiring],
                "Qty": [f"{r[2]} {r[3]}" for r in expiring],
                "Expiry date": [r[4] for r in expiring],
                "Status": status,
            }
        )

    # ---------- Monthly expenditure ----------
    st.header("💰 Monthly Expenditure")
    monthly = get_monthly_expenditure()

    if len(monthly) == 0:
        st.info("No purchases yet.")
    else:
        months = [m[0] for m in monthly]
        totals = [round(m[1], 2) for m in monthly]

        st.bar_chart({"Month": months, "Spent (₹)": totals}, x="Month", y="Spent (₹)")
        st.table(
            {
                "Month": months,
                "Total spent (₹)": totals,
            }
        )

    # ---------- Frequently purchased ----------
    st.header("🔁 Frequently Purchased Items")
    frequent = get_frequent_items(10)

    if len(frequent) == 0:
        st.info("No purchases yet.")
    else:
        st.table(
            {
                "Item": [f[0] for f in frequent],
                "Category": [f[1] for f in frequent],
                "Times bought": [f[2] for f in frequent],
                "Total spent (₹)": [round(f[3], 2) for f in frequent],
            }
        )

# =====================================================
# PAGE 5: MONTHLY REPORT
# =====================================================
def report_page():
    st.title("Monthly Report")

    months = get_available_months()
    if len(months) == 0:
        st.info("No purchases yet. Record some purchases first.")
        return

    month = st.selectbox("Choose month", months)
    rows = get_month_purchases(month)

    # ---------- Summary ----------
    total = sum(r[2] * r[4] for r in rows)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total spent", f"₹{total:,.2f}")
    c2.metric("Purchases", len(rows))
    c3.metric("Average per purchase", f"₹{total / len(rows):,.2f}")

    # ---------- Spending by category ----------
    st.header("Spending by Category")
    by_category = {}
    for r in rows:
        by_category[r[1]] = by_category.get(r[1], 0) + r[2] * r[4]

    sorted_cats = sorted(by_category.items(), key=lambda x: x[1], reverse=True)
    cat_names = [c[0] for c in sorted_cats]
    cat_amounts = [round(c[1], 2) for c in sorted_cats]

    st.bar_chart({"Category": cat_names, "Spent (₹)": cat_amounts}, x="Category", y="Spent (₹)")
    st.table(
        {
            "Category": cat_names,
            "Spent (₹)": cat_amounts,
            "Share": [f"{(a / total) * 100:.1f}%" for a in cat_amounts],
        }
    )

    # ---------- Top items ----------
    st.header("Top Items This Month")
    counts = {}
    for r in rows:
        entry = counts.setdefault(r[0], [0, 0.0])
        entry[0] += 1
        entry[1] += r[2] * r[4]

    top = sorted(counts.items(), key=lambda x: (x[1][0], x[1][1]), reverse=True)[:5]
    st.table(
        {
            "Item": [t[0] for t in top],
            "Times bought": [t[1][0] for t in top],
            "Spent (₹)": [round(t[1][1], 2) for t in top],
        }
    )

    # ---------- Expired items ----------
    st.header("Expired Items (possible waste)")
    today_str = str(date.today())
    expired = [r for r in rows if r[6] and r[6] < today_str]

    if len(expired) == 0:
        st.success("None of this month's purchases have expired.")
    else:
        wasted_value = sum(r[2] * r[4] for r in expired)
        st.warning(f"{len(expired)} item(s) expired, worth up to ₹{wasted_value:,.2f}")
        st.table(
            {
                "Item": [r[0] for r in expired],
                "Qty": [f"{r[2]} {r[3]}" for r in expired],
                "Expiry date": [r[6] for r in expired],
                "Value (₹)": [round(r[2] * r[4], 2) for r in expired],
            }
        )
        st.caption("The app doesn't know if you used the item before it expired, so this is an upper estimate.")

    # ---------- CSV download ----------
    st.header("Download")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Item", "Category", "Quantity", "Unit", "Price per unit",
                     "Total", "Purchase date", "Expiry date", "Store"])
    for r in rows:
        writer.writerow([r[0], r[1], r[2], r[3], r[4], round(r[2] * r[4], 2),
                         r[5], r[6] or "", r[7] or ""])

    st.download_button(
        "Download report as CSV",
        data=buffer.getvalue(),
        file_name=f"grocery_report_{month}.csv",
        mime="text/csv",
    )


# =====================================================
# ROUTER: show the page chosen in the sidebar
# =====================================================
if page == "Dashboard":
    dashboard_page()
elif page == "Items":
    items_page()
elif page == "Purchases":
    purchases_page()
elif page == "Search":
    search_page()
elif page == "Report":
    report_page()