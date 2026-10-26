import json
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.db.models import ProtectedError, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from shop.models import Order, Product, Review
from shop.notify import customer_whatsapp_url_for, whatsapp_action_label

from .forms import (
    ColorFormSet, ContentBlockForm, ImageFormSet, OrderUpdateForm, ProductForm, SiteSettingsForm, SizeFormSet,
)
from .models import FONT_ROLES, WEIGHTS, ContentBlock, PageSection, SiteSettings, sections_for
from .reports import sales_report
from .resources import RESOURCES
from .theme import COLORS, FONTS, google_fonts_url


def staff_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_staff:
            raise Http404
        return view(request, *args, **kwargs)
    return wrapper


def _resource(slug):
    try:
        return RESOURCES[slug]
    except KeyError:
        raise Http404


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except ValueError:
        return {}


# --- overview -----------------------------------------------------------------

@staff_required
def dashboard(request):
    orders = Order.objects.all()
    return render(request, "studio/dashboard.html", {
        "stats": [
            ("Products live", Product.objects.filter(is_active=True).count(), "studio:list", "products"),
            ("Orders to make", orders.filter(status__in=["placed", "crafting", "packing"]).count(), "studio:orders", None),
            ("Awaiting payment", orders.filter(is_paid=False, payment_method="upi").exclude(status="cancelled").count(), "studio:orders", None),
            ("Reviews", Review.objects.count(), "studio:list", "reviews"),
        ],
        "revenue": orders.filter(is_paid=True).aggregate(total=Sum("total"))["total"] or 0,
        "recent_orders": orders[:6],
        "low_stock": Product.objects.filter(is_active=True, stock__lte=5)[:6],
    })


# --- generic list / edit / delete ---------------------------------------------------

@staff_required
def resource_list(request, slug):
    res = _resource(slug)
    items = res.model.objects.all()
    if slug == "products":
        items = items.select_related("category")
        if request.GET.get("category"):
            items = items.filter(category__slug=request.GET["category"])
    query = request.GET.get("q", "").strip()
    if query and res.search:
        cond = Q()
        for f in res.search:
            cond |= Q(**{f"{f}__icontains": query})
        items = items.filter(cond)
    rows = []
    for obj in items:
        cells = []
        for _, attr in res.columns:
            value = getattr(obj, attr, "")
            cells.append(value() if callable(value) else value)
        rows.append({"obj": obj, "cells": cells, "toggles": [(f, getattr(obj, f)) for f in res.toggles]})
    return render(request, "studio/list.html", {
        "res": res, "rows": rows, "query": query,
        "toggle_labels": [res.model._meta.get_field(f).verbose_name for f in res.toggles],
        "categories": RESOURCES["categories"].model.objects.all() if slug == "products" else None,
        "sortable": res.sortable and not query and not request.GET.get("category"),
    })


@staff_required
def resource_edit(request, slug, pk=None):
    if slug == "products":
        return product_edit(request, pk)
    res = _resource(slug)
    obj = get_object_or_404(res.model, pk=pk) if pk else None
    form = res.form_class()(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        messages.success(request, f"Saved {obj}.")
        return redirect("studio:list", slug=slug)
    return render(request, "studio/form.html", {"res": res, "form": form, "obj": obj})


@staff_required
def resource_delete(request, slug, pk):
    res = _resource(slug)
    obj = get_object_or_404(res.model, pk=pk)
    if request.method == "POST":
        try:
            obj.delete()
            messages.success(request, f"Deleted {obj}.")
        except ProtectedError:
            messages.error(request, f"{obj} still has products in it. Move or delete those first.")
        return redirect("studio:list", slug=slug)
    return render(request, "studio/confirm_delete.html", {"res": res, "obj": obj})


@staff_required
@require_POST
def resource_reorder(request, slug):
    res = _resource(slug)
    if not res.sortable:
        raise Http404
    ids = [int(i) for i in _json_body(request).get("ids", []) if str(i).isdigit()]
    with transaction.atomic():
        for position, pk in enumerate(ids):
            res.model.objects.filter(pk=pk).update(sort_order=position)
    return JsonResponse({"ok": True})


@staff_required
@require_POST
def resource_toggle(request, slug, pk):
    res = _resource(slug)
    name = request.POST.get("field")
    if name not in res.toggles:
        raise Http404
    obj = get_object_or_404(res.model, pk=pk)
    setattr(obj, name, not getattr(obj, name))
    obj.save(update_fields=[name])
    return JsonResponse({"ok": True, "value": getattr(obj, name)})


# --- products ----------------------------------------------------------------------

def product_edit(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else Product()
    data, files = (request.POST, request.FILES) if request.method == "POST" else (None, None)
    form = ProductForm(data, files, instance=product)
    formsets = {
        "images": ImageFormSet(data, files, instance=product, prefix="images"),
        "sizes": SizeFormSet(data, instance=product, prefix="sizes"),
        "colors": ColorFormSet(data, instance=product, prefix="colors"),
    }
    if request.method == "POST" and form.is_valid() and all(fs.is_valid() for fs in formsets.values()):
        with transaction.atomic():
            product = form.save()
            for fs in formsets.values():
                fs.instance = product
                fs.save()
        messages.success(request, f"Saved {product.name}.")
        if "continue" in request.POST:
            return redirect("studio:edit", slug="products", pk=product.pk)
        return redirect("studio:list", slug="products")
    return render(request, "studio/product_form.html", {
        "res": RESOURCES["products"], "form": form, "obj": product if product.pk else None, "formsets": formsets,
    })


@staff_required
@require_POST
def product_duplicate(request, pk):
    original = get_object_or_404(Product.objects.prefetch_related("images", "sizes", "colors"), pk=pk)
    with transaction.atomic():
        copy = Product.objects.get(pk=pk)
        copy.pk = None
        copy.slug = ""
        copy.name = f"{original.name} (copy)"
        copy.is_active = False
        copy.save()
        for related in ("images", "sizes", "colors"):
            for item in getattr(original, related).all():
                item.pk = None
                item.product = copy
                item.save()
    messages.success(request, f"Made a hidden copy of {original.name}. Edit it, then switch it on.")
    return redirect("studio:edit", slug="products", pk=copy.pk)


# --- reports -----------------------------------------------------------------------

@staff_required
def reports(request):
    return render(request, "studio/reports.html", sales_report(request.GET.get("period", "day"), request.GET.get("on")))


# --- orders ------------------------------------------------------------------------

@staff_required
def orders(request):
    items = Order.objects.all()
    status = request.GET.get("status", "")
    if status:
        items = items.filter(status=status)
    query = request.GET.get("q", "").strip()
    if query:
        items = items.filter(Q(number__icontains=query) | Q(recipient_name__icontains=query) | Q(phone__icontains=query))
    items = list(items.prefetch_related("items")[:200])
    for o in items:
        o.whatsapp_url = customer_whatsapp_url_for(request, o)
        o.whatsapp_label = whatsapp_action_label(o)
    return render(request, "studio/orders.html", {
        "orders": items, "status": status, "query": query, "statuses": Order.STATUS_CHOICES,
    })


@staff_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
    form = OrderUpdateForm(request.POST or None, instance=order)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Updated order {order.number}. Use “{whatsapp_action_label(order)}” to let the customer know.")
        return redirect("studio:order", pk=order.pk)
    return render(request, "studio/order_detail.html", {
        "order": order, "form": form,
        "customer_whatsapp_url": customer_whatsapp_url_for(request, order),
        "whatsapp_label": whatsapp_action_label(order),
    })


# --- appearance, text and layout ----------------------------------------------------

@staff_required
def appearance(request):
    settings_obj = SiteSettings.load()
    form = SiteSettingsForm(request.POST or None, instance=settings_obj)
    if request.method == "POST":
        if "reset_colors" in request.POST:
            for field, _, _, default in COLORS:
                setattr(settings_obj, field, default)
            settings_obj.save()
            messages.success(request, "Colours are back to the original palette.")
            return redirect("studio:appearance")
        if form.is_valid():
            form.save()
            messages.success(request, "Appearance saved. Open the shop to see it.")
            return redirect("studio:appearance")
    color_fields = [form[field] for field, _, _, _ in COLORS]
    return render(request, "studio/appearance.html", {
        "form": form, "color_fields": color_fields, "font_preview_url": google_fonts_url(*FONTS),
    })


@staff_required
def content(request):
    blocks = ContentBlock.objects.all()
    query = request.GET.get("q", "").strip()
    if query:
        blocks = blocks.filter(Q(key__icontains=query) | Q(text__icontains=query))
    page = request.GET.get("page", "")
    if page:
        blocks = blocks.filter(key__startswith=f"{page}.")
    pages = sorted({k.split(".", 1)[0] for k in ContentBlock.objects.values_list("key", flat=True)})
    return render(request, "studio/content.html", {
        "blocks": blocks, "query": query, "page": page, "pages": pages, "fonts": FONT_ROLES, "weights": WEIGHTS,
    })


@staff_required
@require_POST
def content_save(request):
    """Save one text block. Used by the Content screen and the on-page editor."""
    block = get_object_or_404(ContentBlock, key=request.POST.get("key", ""))
    if request.POST.get("reset"):
        block.text = block.default
        block.color, block.size, block.font, block.weight, block.italic = "", None, "", "", False
        block.save()
    else:
        form = ContentBlockForm(request.POST, instance=block)
        if not form.is_valid():
            errors = "; ".join(e for errs in form.errors.values() for e in errs)
            return JsonResponse({"ok": False, "error": errors}, status=400)
        block = form.save()
    if request.headers.get("x-requested-with") != "XMLHttpRequest":
        messages.success(request, f"Saved “{block.key}”.")
        return redirect(request.POST.get("next") or "studio:content")
    return JsonResponse({
        "ok": True, "text": block.text, "style": block.style,
        "block": {"text": block.text, "color": block.color, "size": block.size, "font": block.font,
                  "weight": block.weight, "italic": block.italic, "default": block.default},
    })


@staff_required
def content_blocks(request):
    """Current values for the keys on a page, so the on-page editor can fill its form."""
    keys = request.GET.getlist("key")
    blocks = ContentBlock.objects.filter(key__in=keys)
    return JsonResponse({b.key: {
        "text": b.text, "color": b.color, "size": b.size, "font": b.font, "weight": b.weight,
        "italic": b.italic, "default": b.default,
    } for b in blocks})


@staff_required
def layout(request):
    return render(request, "studio/layout.html", {"pages": {"home": sections_for("home")}})


@staff_required
@require_POST
def sections_save(request):
    body = _json_body(request)
    page = body.get("page", "")
    with transaction.atomic():
        for position, key in enumerate(body.get("order", [])):
            PageSection.objects.filter(page=page, key=key).update(sort_order=position)
        for key, visible in (body.get("visible") or {}).items():
            PageSection.objects.filter(page=page, key=key).update(is_visible=bool(visible))
    return JsonResponse({"ok": True})


@staff_required
def edit_mode(request):
    request.session["cms_edit"] = request.GET.get("on") == "1"
    target = request.GET.get("next", "/")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = "/"
    return redirect(target)
