"""Session-backed shopping bag. Prices are always re-read from the database."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.conf import settings

from .models import AddOn, Coupon, Product, ProductColor, ProductSize

SESSION_KEY = "bag"
MAX_QTY = 20


@dataclass
class BagLine:
    key: str
    kind: str  # "product" | "addon"
    name: str
    options: str
    image: str
    icon: str
    unit_price: Decimal
    compare_at_price: Optional[Decimal]
    qty: int
    url: str = ""
    badge: str = ""
    category_label: str = ""
    product: Optional[Product] = None
    addon: Optional[AddOn] = None

    @property
    def line_total(self):
        return self.unit_price * self.qty

    @property
    def discount_percent(self):
        if self.compare_at_price and self.compare_at_price > self.unit_price:
            return int(round((1 - self.unit_price / self.compare_at_price) * 100))
        return 0


class Bag:
    def __init__(self, request):
        self.session = request.session
        data = self.session.get(SESSION_KEY) or {}
        data.setdefault("lines", {})
        data.setdefault("coupon", "")
        data.setdefault("note", "")
        data.setdefault("note_from", "")
        self.data = data
        self._lines = None

    # -- mutations -----------------------------------------------------------
    def save(self):
        self.session[SESSION_KEY] = self.data
        self.session.modified = True
        self._lines = None

    def add_product(self, product, size=None, color=None, qty=1):
        key = f"p{product.pk}-s{size.pk if size else 0}-c{color.pk if color else 0}"
        line = self.data["lines"].get(key)
        if line:
            line["qty"] = min(line["qty"] + qty, MAX_QTY)
        else:
            self.data["lines"][key] = {
                "type": "product",
                "id": product.pk,
                "size": size.pk if size else None,
                "color": color.pk if color else None,
                "qty": min(qty, MAX_QTY),
            }
        self.save()
        return key

    def add_addon(self, addon, qty=1):
        key = f"a{addon.pk}"
        line = self.data["lines"].get(key)
        if line:
            line["qty"] = min(line["qty"] + qty, MAX_QTY)
        else:
            self.data["lines"][key] = {"type": "addon", "id": addon.pk, "qty": min(qty, MAX_QTY)}
        self.save()
        return key

    def set_qty(self, key, qty):
        if key in self.data["lines"]:
            if qty <= 0:
                del self.data["lines"][key]
            else:
                self.data["lines"][key]["qty"] = min(qty, MAX_QTY)
            self.save()

    def remove(self, key):
        self.set_qty(key, 0)

    def set_coupon(self, code):
        self.data["coupon"] = (code or "").strip().upper()
        self.save()

    def set_note(self, note, note_from=None):
        self.data["note"] = (note or "").strip()[:200]
        if note_from is not None:
            self.data["note_from"] = note_from.strip()[:40]
        self.save()

    def clear(self):
        self.session[SESSION_KEY] = {"lines": {}, "coupon": "", "note": "", "note_from": ""}
        self.session.modified = True
        self._lines = None

    # -- reading -------------------------------------------------------------
    @property
    def note(self):
        return self.data["note"]

    @property
    def note_from(self):
        return self.data["note_from"]

    @property
    def coupon_code(self):
        return self.data["coupon"]

    def lines(self):
        if self._lines is not None:
            return self._lines
        raw = self.data["lines"]
        product_ids = {l["id"] for l in raw.values() if l["type"] == "product"}
        addon_ids = {l["id"] for l in raw.values() if l["type"] == "addon"}
        size_ids = {l.get("size") for l in raw.values() if l.get("size")}
        color_ids = {l.get("color") for l in raw.values() if l.get("color")}
        products = Product.objects.active().select_related("category").in_bulk(product_ids)
        addons = AddOn.objects.filter(is_active=True).in_bulk(addon_ids)
        sizes = ProductSize.objects.in_bulk(size_ids)
        colors = ProductColor.objects.in_bulk(color_ids)

        lines, stale = [], []
        for key, l in raw.items():
            if l["type"] == "product":
                p = products.get(l["id"])
                if not p:
                    stale.append(key)
                    continue
                size = sizes.get(l.get("size"))
                color = colors.get(l.get("color"))
                options = " • ".join(x for x in [size.name if size else "", color.name if color else ""] if x)
                lines.append(BagLine(
                    key=key, kind="product", name=p.name,
                    options=options or p.short_description,
                    image=p.image_src, icon="",
                    unit_price=size.price if size else p.price,
                    compare_at_price=(size.compare_at_price if size else p.compare_at_price),
                    qty=l["qty"], url=p.get_absolute_url(), badge=p.badge,
                    category_label=p.category.pill_name, product=p,
                ))
            else:
                a = addons.get(l["id"])
                if not a:
                    stale.append(key)
                    continue
                lines.append(BagLine(
                    key=key, kind="addon", name=a.name, options=a.description,
                    image=a.image_src, icon=a.icon or "spa",
                    unit_price=a.price, compare_at_price=a.compare_at_price,
                    qty=l["qty"], category_label="Gifting Add-on", addon=a,
                ))
        if stale:
            for key in stale:
                raw.pop(key, None)
            self.save()
        # products first, add-ons after
        lines.sort(key=lambda x: x.kind != "product")
        self._lines = lines
        return lines

    def __len__(self):
        return sum(l.qty for l in self.lines())

    @property
    def count(self):
        return len(self)

    @property
    def addon_ids(self):
        return {l.addon.pk for l in self.lines() if l.addon}

    @property
    def subtotal(self):
        return sum((l.line_total for l in self.lines()), Decimal("0"))

    def coupon(self):
        """Return (coupon or None, discount, message)."""
        code = self.coupon_code
        if not code:
            return None, Decimal("0"), ""
        coupon = Coupon.objects.filter(code=code).first()
        if not coupon:
            return None, Decimal("0"), "That code doesn't look right."
        discount, error = coupon.evaluate(self.subtotal)
        return coupon, discount, error

    def totals(self, payment_method=None):
        cfg = settings.JANJE
        subtotal = self.subtotal
        coupon, coupon_discount, coupon_error = self.coupon()
        threshold = Decimal(cfg["FREE_SHIPPING_THRESHOLD"])
        shipping = Decimal("0") if subtotal == 0 or subtotal >= threshold else Decimal(cfg["SHIPPING_FEE"])
        prepaid = Decimal(cfg["UPI_PREPAID_DISCOUNT"]) if payment_method == "upi" and subtotal > 0 else Decimal("0")
        cod_fee = Decimal(cfg["COD_FEE"]) if payment_method == "cod" and subtotal > 0 else Decimal("0")
        total = max(subtotal - coupon_discount - prepaid + shipping + cod_fee, Decimal("0"))
        remaining = max(threshold - subtotal, Decimal("0"))
        return {
            "subtotal": subtotal,
            "coupon": coupon,
            "coupon_code": self.coupon_code,
            "coupon_discount": coupon_discount,
            "coupon_error": coupon_error,
            "shipping": shipping,
            "prepaid_discount": prepaid,
            "cod_fee": cod_fee,
            "total": total,
            "free_shipping_threshold": threshold,
            "free_shipping_remaining": remaining,
            "free_shipping_progress": 100 if threshold == 0 else min(int(subtotal / threshold * 100), 100),
        }


def wishlist_ids(request):
    return set(request.session.get("wishlist", []))
