"""Sales numbers for the Studio reports page.

Cancelled orders are left out everywhere. "Sales" is the order total the customer pays (after discounts,
including delivery); product revenue is price × quantity of each line.
"""
from datetime import datetime, time, timedelta

from django.db.models import Count, F, Sum
from django.db.models.functions import Trunc
from django.utils import timezone

from shop.models import Order, OrderItem

PERIODS = {
    # key: (label, Trunc kind, how many buckets to show)
    "day": ("Daily", "day", 30),
    "week": ("Weekly", "week", 12),
    "month": ("Monthly", "month", 12),
}


def bucket_start(day, kind):
    if kind == "week":
        return day - timedelta(days=day.weekday())
    if kind == "month":
        return day.replace(day=1)
    return day


def step_back(day, kind, n):
    if kind == "day":
        return day - timedelta(days=n)
    if kind == "week":
        return day - timedelta(weeks=n)
    month = day.month - 1 - n
    return day.replace(year=day.year + month // 12, month=month % 12 + 1, day=1)


def step_forward(day, kind):
    if kind == "day":
        return day + timedelta(days=1)
    if kind == "week":
        return day + timedelta(weeks=1)
    return step_back(day, kind, -1)


def bucket_label(day, kind):
    if kind == "day":
        return f"{day:%a} {day.day} {day:%b}"
    if kind == "week":
        end = day + timedelta(days=6)
        return f"{day.day} {day:%b} – {end.day} {end:%b}"
    return f"{day:%b %Y}"


def short_label(day, kind):
    return f"{day:%b}" if kind == "month" else f"{day.day} {day:%b}"


def _aware(day):
    return timezone.make_aware(datetime.combine(day, time.min))


def _date(day):
    return f"{day.day} {day:%b %Y}"


def sales_report(period="day", on=None):
    label, kind, count = PERIODS.get(period, PERIODS["day"])
    today = timezone.localdate()
    last = bucket_start(today, kind)
    first = step_back(last, kind, count - 1)
    start, end = _aware(first), _aware(step_forward(last, kind))

    orders = Order.objects.exclude(status="cancelled").filter(created_at__gte=start, created_at__lt=end)
    lines = OrderItem.objects.filter(order__in=orders)

    per_order = {
        row["bucket"]: row for row in orders.annotate(bucket=Trunc("created_at", kind))
        .values("bucket").annotate(orders=Count("id"), sales=Sum("total"))
    }
    per_item = {
        row["bucket"]: row["items"] for row in lines.annotate(bucket=Trunc("order__created_at", kind))
        .values("bucket").annotate(items=Sum("quantity"))
    }
    per_order = {timezone.localtime(k).date(): v for k, v in per_order.items()}
    per_item = {timezone.localtime(k).date(): v for k, v in per_item.items()}

    rows, day = [], first
    while day <= last:
        o = per_order.get(day, {})
        rows.append({
            "start": day, "label": bucket_label(day, kind), "short": short_label(day, kind),
            "orders": o.get("orders", 0), "items": per_item.get(day, 0) or 0, "sales": o.get("sales") or 0,
        })
        day = step_forward(day, kind)
    peak = max((r["sales"] for r in rows), default=0)
    label_every = {"day": 5, "week": 2, "month": 1}[kind]  # keep axis labels from colliding
    for i, r in enumerate(rows):
        r["height"] = round(float(r["sales"]) / float(peak) * 100, 1) if peak else 0
        r["show_label"] = i % label_every == 0 or i == len(rows) - 1

    # Product table: the whole range, or one bucket when a bar is picked.
    selected = next((r for r in rows if on and r["start"].isoformat() == on), None)
    product_lines = lines
    if selected:
        product_lines = lines.filter(
            order__created_at__gte=_aware(selected["start"]),
            order__created_at__lt=_aware(step_forward(selected["start"], kind)),
        )
    products = list(
        product_lines.values("name").annotate(
            qty=Sum("quantity"), revenue=Sum(F("unit_price") * F("quantity")), orders=Count("order", distinct=True),
        ).order_by("-revenue", "-qty", "name")
    )
    top = products[0]["revenue"] if products else 0
    addon_names = set(product_lines.filter(addon__isnull=False).values_list("name", flat=True))
    for p in products:
        p["share"] = round(float(p["revenue"]) / float(top) * 100, 1) if top else 0
        p["is_addon"] = p["name"] in addon_names

    total_sales = sum(r["sales"] for r in rows)
    total_orders = sum(r["orders"] for r in rows)
    return {
        "period": period if period in PERIODS else "day",
        "period_label": label,
        "periods": [(key, value[0]) for key, value in PERIODS.items()],
        "range_label": f"{_date(first)} – {_date(step_forward(last, kind) - timedelta(days=1))}",
        "rows": rows,
        "peak": peak,
        "totals": {
            "sales": total_sales,
            "orders": total_orders,
            "items": sum(r["items"] for r in rows),
            "average": (total_sales / total_orders) if total_orders else 0,
            "paid": orders.filter(is_paid=True).aggregate(s=Sum("total"))["s"] or 0,
        },
        "selected": selected,
        "products": products,
    }
