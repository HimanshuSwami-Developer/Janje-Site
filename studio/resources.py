"""The shop models Studio can list, edit, reorder and delete."""
from dataclasses import dataclass, field

from django import forms
from django.forms import modelform_factory

from shop.models import AddOn, Category, Coupon, Product, Reel, Review


@dataclass
class Resource:
    slug: str
    model: type
    title: str
    singular: str
    fields: list
    columns: list  # (heading, attribute)
    toggles: list = field(default_factory=list)  # boolean fields switchable from the list
    search: list = field(default_factory=list)
    sortable: bool = False
    widgets: dict = field(default_factory=dict)

    def form_class(self):
        return modelform_factory(self.model, fields=self.fields, widgets=self.widgets)


RESOURCES = {r.slug: r for r in [
    Resource(
        "products", Product, "Products", "product", fields=[],  # edited by the custom product form
        columns=[("Price", "price"), ("Stock", "stock"), ("Category", "category")],
        toggles=["is_active", "is_bestseller", "is_hero"], search=["name", "short_description"], sortable=True,
    ),
    Resource(
        "categories", Category, "Categories", "category",
        fields=["name", "slug", "short_name", "emoji", "tagline", "image", "image_url", "is_active"],
        columns=[("Short name", "short_name"), ("Tagline", "tagline")],
        toggles=["is_active"], search=["name"], sortable=True,
    ),
    Resource(
        "reels", Reel, "Reels", "reel",
        fields=["title", "video", "video_url", "image", "image_url", "reel_url", "product", "tag", "views", "likes", "cta_label", "is_active"],
        columns=[("Product", "product"), ("Views", "views")],
        toggles=["is_active"], search=["title"], sortable=True,
    ),
    Resource(
        "reviews", Review, "Reviews", "review",
        fields=["name", "location", "rating", "text", "product", "is_verified", "is_featured", "is_approved", "tint"],
        columns=[("Rating", "stars"), ("Product", "product"), ("Note", "text")],
        toggles=["is_approved", "is_featured"], search=["name", "text"],
        widgets={"text": forms.Textarea(attrs={"rows": 4})},
    ),
    Resource(
        "addons", AddOn, "Gift add-ons", "add-on",
        fields=["name", "short_name", "description", "price", "compare_at_price", "icon", "image", "image_url",
                "show_on_product", "show_in_bag", "is_active"],
        columns=[("Price", "price")], toggles=["is_active", "show_in_bag"], search=["name"], sortable=True,
    ),
    Resource(
        "coupons", Coupon, "Coupons", "coupon",
        fields=["code", "kind", "value", "min_subtotal", "max_discount", "valid_until", "is_active"],
        columns=[("Type", "get_kind_display"), ("Value", "value"), ("Min order", "min_subtotal")],
        toggles=["is_active"], search=["code"],
        widgets={"valid_until": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")},
    ),
]}
