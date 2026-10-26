from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.views.decorators.http import require_POST

from studio.models import sections_for

from .cart import Bag, wishlist_ids
from .forms import CheckoutForm, NewsletterForm, ReviewForm, TrackOrderForm, order_from_form
from .models import AddOn, Category, NewsletterSubscriber, Order, OrderItem, Product, Reel, Review
from .notify import shop_whatsapp_url, upi_qr_svg

SORTS = {
    "featured": ("sort_order", "-created_at"),
    "new": ("-created_at",),
    "price_low": ("price",),
    "price_high": ("-price",),
    "rating": ("-rating", "-review_count"),
}


def _int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# --- storefront ---------------------------------------------------------------

def home(request):
    products = Product.objects.active().select_related("category")
    hero = list(products.filter(is_hero=True)[:3])
    bestsellers = list(products.filter(is_bestseller=True)[:8])
    # The hero collage: one big round photo plus two polaroids
    main = (hero or bestsellers or [None])[0]
    polaroids = []
    for p in hero[1:] + bestsellers:
        if p != main and p not in polaroids:
            polaroids.append(p)
    polaroids = polaroids[:2]
    categories = list(Category.objects.filter(is_active=True))
    return render(request, "shop/home.html", {
        "sections": sections_for("home"),
        "hero_products": hero,
        "polaroids": polaroids,
        "categories": categories,
        "feature_category": categories[-1] if len(categories) > 1 else None,
        "bestsellers": bestsellers,
        "product_total": products.count(),
        "reels": Reel.objects.filter(is_active=True).select_related("product")[:6],
        "love_notes": Review.objects.filter(is_featured=True, is_approved=True)[:3],
    })


def product_list(request, slug=None):
    category = get_object_or_404(Category, slug=slug, is_active=True) if slug else None
    products = Product.objects.active().select_related("category")
    if category:
        products = products.filter(category=category)
    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(short_description__icontains=query)
            | Q(description__icontains=query) | Q(category__name__icontains=query)
        )
    sort = request.GET.get("sort", "featured")
    products = products.order_by(*SORTS.get(sort, SORTS["featured"]))
    return render(request, "shop/product_list.html", {
        "category": category,
        "products": products,
        "query": query,
        "sort": sort,
        "sort_options": [
            ("featured", "Featured"), ("new", "Newest"), ("price_low", "Price: Low to High"),
            ("price_high", "Price: High to Low"), ("rating", "Top Rated"),
        ],
    })


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.active().select_related("category").prefetch_related("images", "sizes", "colors", "reels"),
        slug=slug,
    )
    sizes = list(product.sizes.all())
    colors = list(product.colors.all())
    default_size = product.default_size()
    addons = AddOn.objects.filter(is_active=True, show_on_product=True)
    reviews = product.reviews.filter(is_approved=True)
    related = list(Product.objects.active().filter(category=product.category).exclude(pk=product.pk)[:4])
    if len(related) < 4:
        related += list(
            Product.objects.active().exclude(pk__in=[product.pk] + [p.pk for p in related])[: 4 - len(related)]
        )

    step = iter(range(1, 4))
    steps = {
        "size": next(step) if sizes else None,
        "color": next(step) if colors else None,
    }
    steps["gift"] = next(step)

    price = default_size.price if default_size else product.price
    compare = default_size.compare_at_price if default_size else product.compare_at_price
    save_percent = int(round((1 - price / compare) * 100)) if compare and compare > price else 0
    return render(request, "shop/product_detail.html", {
        "product": product,
        "save_percent": save_percent,
        "bag_note": Bag(request).note,
        "whatsapp_text": f"Hi Janjé! I'm interested in the {product.name} 🌸",
        "sizes": sizes,
        "colors": colors,
        "default_size": default_size,
        "price": price,
        "compare_price": compare,
        "addons": addons,
        "reviews": reviews[:6],
        "review_total": reviews.count(),
        "review_form": ReviewForm(),
        "related": related,
        "steps": steps,
        "reel": next(iter(product.reels.all()), None),
        "pdp_data": {
            "basePrice": float(price),
            "baseCompare": float(compare or price),
        },
    })


@login_required
@require_POST
def review_create(request, slug):
    product = get_object_or_404(Product.objects.active(), slug=slug)
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.name = request.user.get_full_name() or request.user.username
        review.is_verified = OrderItem.objects.filter(order__user=request.user, product=product).exists()
        review.save()
        product.add_rating(review.rating)
        messages.success(request, "Thank you for the love note! ♡")
    else:
        messages.error(request, "Please add a rating and a few words for your review.")
    return redirect(f"{product.get_absolute_url()}#reviews-section")


def our_story(request):
    return render(request, "shop/our_story.html")


# --- wishlist ---------------------------------------------------------------

def wishlist(request):
    ids = wishlist_ids(request)
    products = Product.objects.active().filter(pk__in=ids).select_related("category")
    return render(request, "shop/wishlist.html", {"products": products})


@require_POST
def wishlist_toggle(request):
    product = get_object_or_404(Product.objects.active(), pk=_int(request.POST.get("product_id")))
    ids = set(request.session.get("wishlist", []))
    if product.pk in ids:
        ids.discard(product.pk)
        added = False
    else:
        ids.add(product.pk)
        added = True
    request.session["wishlist"] = sorted(ids)
    return JsonResponse({"ok": True, "added": added, "count": len(ids)})


# --- bag (AJAX) ---------------------------------------------------------------

def _cart_context(bag):
    return {
        "bag": bag,
        "lines": bag.lines(),
        "totals": bag.totals(),
        "upsell_addons": AddOn.objects.filter(is_active=True, show_in_bag=True).exclude(pk__in=bag.addon_ids)[:3],
    }


def _bag_response(request, bag, **extra):
    html = render_to_string("partials/cart_body.html", _cart_context(bag), request=request)
    return JsonResponse({"ok": True, "count": bag.count, "html": html, **extra})


def cart(request):
    return render(request, "shop/cart.html", _cart_context(Bag(request)))


def bag_drawer(request):
    return _bag_response(request, Bag(request))


@require_POST
def bag_add(request):
    bag = Bag(request)
    product = get_object_or_404(Product.objects.active(), pk=_int(request.POST.get("product_id")))
    if not product.in_stock:
        return JsonResponse({"ok": False, "error": "Sorry, this one is sold out for now."}, status=400)
    qty = max(1, _int(request.POST.get("qty"), 1))
    size = product.sizes.filter(pk=_int(request.POST.get("size_id"))).first() or product.default_size()
    color = product.colors.filter(pk=_int(request.POST.get("color_id"))).first()
    if color is None:
        color = product.colors.first()
    bag.add_product(product, size, color, qty)
    for addon_id in request.POST.getlist("addons"):
        addon = AddOn.objects.filter(pk=_int(addon_id), is_active=True).first()
        if addon:
            bag.add_addon(addon, qty)
    if request.POST.get("gift_note", "").strip():
        bag.set_note(request.POST["gift_note"])
    extra = {"redirect": reverse("shop:checkout")} if request.POST.get("buy_now") else {"redirect": reverse("shop:cart")}
    return _bag_response(request, bag, message=f"{product.name} added to your bag ♡", **extra)


@require_POST
def bag_add_addon(request):
    bag = Bag(request)
    addon = get_object_or_404(AddOn, pk=_int(request.POST.get("addon_id")), is_active=True)
    bag.add_addon(addon)
    return _bag_response(request, bag, message=f"{addon.name} added ♡")


@require_POST
def bag_update(request):
    bag = Bag(request)
    bag.set_qty(request.POST.get("key", ""), _int(request.POST.get("qty"), 0))
    return _bag_response(request, bag)


@require_POST
def bag_note(request):
    bag = Bag(request)
    bag.set_note(request.POST.get("note", ""), request.POST.get("note_from"))
    return _bag_response(request, bag, message="Gift note saved ♡")


@require_POST
def bag_coupon(request):
    bag = Bag(request)
    code = request.POST.get("code", "")
    bag.set_coupon(code)
    coupon, discount, error = bag.coupon()
    if code and (error or not coupon):
        bag.set_coupon("")
        return JsonResponse({"ok": False, "error": error or "That code doesn't look right."}, status=400)
    message = f"‘{coupon.code}’ applied: ₹{discount:,.0f} boutique discount" if coupon else "Code removed."
    return JsonResponse({"ok": True, "message": message})


# --- checkout -----------------------------------------------------------------

def _checkout_initial(request, bag):
    initial = {"gift_note": bag.note, "gift_from": bag.note_from, "delivery_mode": "express", "payment_method": "upi"}
    user = request.user
    if user.is_authenticated:
        initial.update({"email": user.email, "gift_from": bag.note_from or user.first_name})
        profile = getattr(user, "profile", None)
        if profile and profile.phone:
            initial["phone"] = profile.phone
        address = user.addresses.order_by("-is_default", "-id").first()
        if address:
            initial.update({
                "recipient_name": address.recipient_name, "pincode": address.pincode,
                "address_line1": address.line1, "address_line2": address.line2,
                "city": address.city, "state": address.state,
            })
            initial.setdefault("phone", address.phone)
    note = request.GET.get("note")
    if note:
        initial["gift_note"] = note[:200]
    return initial


def checkout_summary(request):
    bag = Bag(request)
    payment = request.GET.get("payment", "upi")
    return render(request, "partials/checkout_summary.html", {
        "bag": bag, "lines": bag.lines(), "totals": bag.totals(payment), "payment_method": payment,
    })


def checkout(request):
    bag = Bag(request)
    if not bag.lines():
        messages.info(request, "Your bag is empty — let's find something cute first 🎀")
        return redirect("shop:product_list")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = _place_order(request, bag, form)
            return redirect(order.get_absolute_url())
        messages.error(request, "Please check the highlighted details below.")
    else:
        form = CheckoutForm(initial=_checkout_initial(request, bag))

    payment = form["payment_method"].value() or "upi"
    return render(request, "shop/checkout.html", {
        "form": form,
        "bag": bag,
        "lines": bag.lines(),
        "totals": bag.totals(payment),
        "payment_method": payment,
        "ncr_prefixes": settings.JANJE["NCR_PINCODE_PREFIXES"],
        "cod_fee": settings.JANJE["COD_FEE"],
    })


@transaction.atomic
def _place_order(request, bag, form):
    order = order_from_form(form, request.user)
    if order.delivery_mode == "express" and not order.is_ncr:
        order.delivery_mode = "standard"
    totals = bag.totals(order.payment_method)
    order.subtotal = totals["subtotal"]
    order.coupon_code = totals["coupon"].code if totals["coupon"] and totals["coupon_discount"] else ""
    order.coupon_discount = totals["coupon_discount"]
    order.prepaid_discount = totals["prepaid_discount"]
    order.shipping_fee = totals["shipping"]
    order.cod_fee = totals["cod_fee"]
    order.total = totals["total"]
    order.save()

    items = []
    for line in bag.lines():
        items.append(OrderItem(
            order=order, product=line.product, addon=line.addon, name=line.name,
            options=line.options, category_label=line.category_label, image_url=line.image,
            icon=line.icon, unit_price=line.unit_price, compare_at_price=line.compare_at_price, quantity=line.qty,
        ))
        if line.product:
            Product.objects.filter(pk=line.product.pk, stock__gte=line.qty).update(stock=F("stock") - line.qty)
    OrderItem.objects.bulk_create(items)

    if form.cleaned_data.get("save_address") and request.user.is_authenticated:
        from accounts.models import Address
        Address.objects.get_or_create(
            user=request.user, line1=order.address_line1, pincode=order.pincode,
            defaults={
                "recipient_name": order.recipient_name, "phone": order.phone, "line2": order.address_line2,
                "city": order.city, "state": order.state, "label": "Gifting",
                "is_default": not request.user.addresses.exists(),
            },
        )

    bag.clear()
    _remember_order(request, order.number)
    _send_order_email(request, order)
    return order


def _send_order_email(request, order):
    lines = "\n".join(f"  • {i.quantity} × {i.name} ({i.options}) — ₹{i.line_total:,.0f}" for i in order.items.all())
    body = (
        f"Hi {order.gift_from or order.recipient_name},\n\n"
        f"Thank you for your order {order.number}! Our Gurgaon artisans are getting started.\n\n"
        f"{lines}\n\nTotal: ₹{order.total:,.0f} ({order.get_payment_method_display()})\n"
        f"Delivering to: {order.recipient_name}, {order.address_line1}, {order.address_line2}, "
        f"{order.city}, {order.state} — {order.pincode}\n\n"
        f"Track your order: {request.build_absolute_uri(order.get_share_url())}\n\n"
        "Handcrafted with love,\nJanjé – Blush & Bow"
    )
    send_mail(f"Your Janjé order {order.number} ♡", body, None, [order.email], fail_silently=True)


def _remember_order(request, number):
    """Let this browser open the order page (guests have no account to tie it to)."""
    recent = [n for n in request.session.get("recent_orders", []) if n != number]
    request.session["recent_orders"] = ([number] + recent)[:10]


def order_detail(request, number):
    order = Order.objects.prefetch_related("items").filter(number=number).first()
    has_link = bool(order) and constant_time_compare(request.GET.get("k", ""), order.access_token)
    allowed = order and (
        has_link
        or number in request.session.get("recent_orders", [])
        or (request.user.is_authenticated and (order.user_id == request.user.pk or request.user.is_staff))
    )
    if not allowed:
        # Same response whether or not the order exists, so numbers can't be probed.
        return redirect(f"{reverse('shop:track_order')}?number={quote(number)}")
    if has_link:
        _remember_order(request, number)
    # Rendered (not redirected) for link holders so WhatsApp's preview bot sees the page too.
    first = next((i for i in order.items.all() if i.image_url), None)
    share_url = request.build_absolute_uri(order.get_share_url())
    return render(request, "shop/order_confirmation.html", {
        "order": order,
        "upi_link": order.upi_link,
        "upi_qr": upi_qr_svg(order.upi_link),
        "send_whatsapp_url": shop_whatsapp_url(order, share_url),
        "preview_image": request.build_absolute_uri(first.image_url) if first else "",
    })


TRACK_ATTEMPTS = 10  # failed lookups allowed per IP...
TRACK_WINDOW = 15 * 60  # ...in this many seconds


def track_order(request):
    throttle_key = f"track-order:{request.META.get('REMOTE_ADDR', '')}"
    throttled = cache.get(throttle_key, 0) >= TRACK_ATTEMPTS
    if request.method == "POST" and not throttled:
        form = TrackOrderForm(request.POST)
        if form.is_valid():
            cache.delete(throttle_key)
            _remember_order(request, form.order.number)
            return redirect(form.order.get_absolute_url())
        cache.set(throttle_key, cache.get(throttle_key, 0) + 1, TRACK_WINDOW)
    else:
        form = TrackOrderForm(initial={"number": request.POST.get("number") or request.GET.get("number", "")[:20]})
    return render(request, "shop/track_order.html", {"form": form, "throttled": throttled})


# --- newsletter ---------------------------------------------------------------

@require_POST
def newsletter_signup(request):
    form = NewsletterForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"ok": False, "error": "Please enter a valid email ♡"}, status=400)
    _, created = NewsletterSubscriber.objects.get_or_create(email=form.cleaned_data["email"].lower())
    message = (
        "Welcome to the Bow Club! Use code WELCOME10 for 10% off 🎀" if created
        else "You're already in the Bow Club ♡ Use WELCOME10 for 10% off."
    )
    return JsonResponse({"ok": True, "message": message})
