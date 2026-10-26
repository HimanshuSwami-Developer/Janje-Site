from django.contrib import admin
from django.utils.html import format_html

from .models import (
    AddOn, Category, Coupon, NewsletterSubscriber, Order, OrderItem, Product, ProductColor, ProductImage,
    ProductSize, Reel, Review,
)


def thumb(obj, size=48):
    src = getattr(obj, "image_src", "")
    if not src:
        return "—"
    return format_html('<img src="{}" style="width:{}px;height:{}px;object-fit:cover;border-radius:10px">', src, size, size)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["preview", "name", "emoji", "slug", "sort_order", "is_active"]
    list_editable = ["sort_order", "is_active"]
    prepopulated_fields = {"slug": ["name"]}

    @admin.display(description="")
    def preview(self, obj):
        return thumb(obj)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 0


class ProductColorInline(admin.TabularInline):
    model = ProductColor
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["preview", "name", "category", "price", "compare_at_price", "stock", "badge", "is_bestseller", "is_hero", "is_active"]
    list_editable = ["price", "stock", "is_bestseller", "is_hero", "is_active"]
    list_filter = ["category", "is_active", "is_bestseller", "is_hero"]
    search_fields = ["name", "short_description"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [ProductImageInline, ProductSizeInline, ProductColorInline]
    fieldsets = [
        (None, {"fields": ["category", "name", "slug", "short_description", "description"]}),
        ("Pricing & stock", {"fields": ["price", "compare_at_price", "stock"]}),
        ("Images", {"fields": ["image", "image_url"], "description": "Upload a photo, or paste an image URL."}),
        ("Display", {"fields": ["badge", "badge_style", "sticker", "swatches", "rating", "review_count",
                                "is_bestseller", "is_hero", "is_active", "sort_order"]}),
    ]

    @admin.display(description="")
    def preview(self, obj):
        return thumb(obj)


@admin.register(AddOn)
class AddOnAdmin(admin.ModelAdmin):
    list_display = ["preview", "name", "price", "show_on_product", "show_in_bag", "is_active", "sort_order"]
    list_editable = ["price", "show_on_product", "show_in_bag", "is_active", "sort_order"]

    @admin.display(description="")
    def preview(self, obj):
        return thumb(obj)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["name", "product", "rating", "is_verified", "is_featured", "is_approved", "created_at"]
    list_editable = ["is_featured", "is_approved"]
    list_filter = ["is_approved", "is_featured", "rating", "product"]
    search_fields = ["name", "text"]


@admin.register(Reel)
class ReelAdmin(admin.ModelAdmin):
    list_display = ["preview", "title", "product", "views", "likes", "sort_order", "is_active"]
    list_editable = ["sort_order", "is_active"]

    @admin.display(description="")
    def preview(self, obj):
        return thumb(obj)


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ["code", "kind", "value", "min_subtotal", "max_discount", "is_active", "valid_until"]
    list_editable = ["is_active"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ["name", "options", "unit_price", "quantity"]
    readonly_fields = fields
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["number", "created_at", "recipient_name", "phone", "city", "total", "payment_method", "is_paid", "status"]
    list_editable = ["is_paid", "status"]
    list_filter = ["status", "is_paid", "payment_method", "delivery_mode", "created_at"]
    search_fields = ["number", "recipient_name", "email", "phone", "pincode"]
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
    readonly_fields = ["number", "created_at", "subtotal", "coupon_code", "coupon_discount", "prepaid_discount",
                       "shipping_fee", "cod_fee", "total"]
    fieldsets = [
        ("Order", {"fields": ["number", "created_at", "user", "status", "status_note"]}),
        ("Payment", {"fields": ["payment_method", "upi_id", "is_paid", "payment_reference"]}),
        ("Customer & delivery", {"fields": ["email", "phone", "recipient_name", "address_line1", "address_line2",
                                            "city", "state", "pincode", "delivery_mode", "scheduled_date"]}),
        ("Gift note", {"fields": ["gift_note", "gift_from"]}),
        ("Totals", {"fields": ["subtotal", "coupon_code", "coupon_discount", "prepaid_discount", "shipping_fee",
                               "cod_fee", "total"]}),
    ]


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ["email", "created_at"]
    search_fields = ["email"]
