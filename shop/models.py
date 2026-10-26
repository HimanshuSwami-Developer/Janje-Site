import random
from datetime import timedelta
from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.signing import Signer
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ImageSourceMixin:
    """Models with both an uploaded `image` and a fallback `image_url`."""

    @property
    def image_src(self):
        if getattr(self, "image", None):
            return self.image.url
        return getattr(self, "image_url", "") or ""


class Category(ImageSourceMixin, models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    emoji = models.CharField(max_length=8, blank=True)
    short_name = models.CharField(max_length=40, blank=True, help_text="Used on filter pills, e.g. 'Clips'")
    tagline = models.CharField(max_length=120, blank=True)
    image = models.ImageField(upload_to="categories/", blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        return f"{self.name} {self.emoji}".strip()

    @property
    def pill_name(self):
        return self.short_name or self.name

    def get_absolute_url(self):
        return reverse("shop:category", args=[self.slug])


BADGE_STYLES = [
    ("primary", "Berry"),
    ("secondary", "Lilac grey"),
    ("tertiary", "Sage"),
    ("soft", "Blush"),
]


class ProductQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Product(ImageSourceMixin, TimeStamped):
    category = models.ForeignKey(Category, related_name="products", on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, blank=True)
    short_description = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    compare_at_price = models.DecimalField(
        max_digits=9, decimal_places=2, null=True, blank=True, help_text="Original price shown struck-through"
    )
    image = models.ImageField(upload_to="products/", blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    badge = models.CharField(max_length=40, blank=True, help_text="e.g. Bestseller, Trending, New Drop")
    badge_style = models.CharField(max_length=12, choices=BADGE_STYLES, default="primary")
    sticker = models.CharField(max_length=40, blank=True, help_text="Small scrapbook sticker, e.g. 'Handmade with love ♡'")
    swatches = models.CharField(
        max_length=120, blank=True, help_text="Comma separated hex colours shown as dots on product cards"
    )
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=Decimal("5.0"))
    review_count = models.PositiveIntegerField(default=0)
    stock = models.PositiveIntegerField(default=25)
    is_active = models.BooleanField(default=True)
    is_bestseller = models.BooleanField(default=True, help_text="Show in the home page bestseller grid")
    is_hero = models.BooleanField(default=False, help_text="Feature in the home page hero")
    sort_order = models.PositiveIntegerField(default=0)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:45] or "product"
            slug, n = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("shop:product", args=[self.slug])

    @property
    def swatch_list(self):
        return [c.strip() for c in self.swatches.split(",") if c.strip()]

    @property
    def discount_percent(self):
        if self.compare_at_price and self.compare_at_price > self.price:
            return int(round((1 - self.price / self.compare_at_price) * 100))
        return 0

    @property
    def in_stock(self):
        return self.stock > 0

    def default_size(self):
        sizes = list(self.sizes.all())
        return next((s for s in sizes if s.is_default), sizes[0] if sizes else None)

    def add_rating(self, stars):
        total = self.rating * self.review_count + Decimal(stars)
        self.review_count += 1
        self.rating = (total / self.review_count).quantize(Decimal("0.1"))
        self.save(update_fields=["rating", "review_count", "updated_at"])


class ProductImage(ImageSourceMixin, models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/gallery/", blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    label = models.CharField(max_length=30, blank=True, help_text="Tiny caption on the thumbnail, e.g. 'Details'")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.label or f"Image {self.pk}"


class ProductSize(models.Model):
    """Arrangement size / variant with its own price (e.g. 1 Bloom Solo, 5-Bloom Classic)."""

    product = models.ForeignKey(Product, related_name="sizes", on_delete=models.CASCADE)
    name = models.CharField(max_length=40)
    subtitle = models.CharField(max_length=40, blank=True)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    badge = models.CharField(max_length=20, blank=True)
    is_default = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "price"]

    def __str__(self):
        return self.name


class ProductColor(models.Model):
    product = models.ForeignKey(Product, related_name="colors", on_delete=models.CASCADE)
    name = models.CharField(max_length=40)
    emoji = models.CharField(max_length=8, blank=True)
    hex = models.CharField(max_length=7, default="#f472b6")
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name

    @property
    def label(self):
        return f"{self.name} {self.emoji}".strip()


class AddOn(ImageSourceMixin, models.Model):
    """Gifting extras: fragrance mist, keepsake box, matching clip..."""

    name = models.CharField(max_length=80)
    short_name = models.CharField(max_length=40, blank=True, help_text="Shorter name for the bag upsell rail")
    description = models.CharField(max_length=140, blank=True)
    price = models.DecimalField(max_digits=9, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    icon = models.CharField(max_length=40, blank=True, help_text="Material Symbols icon name, e.g. 'spa'")
    image = models.ImageField(upload_to="addons/", blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    show_on_product = models.BooleanField(default=True)
    show_in_bag = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


REVIEW_TINTS = [("primary", "Blush"), ("secondary", "Lilac"), ("tertiary", "Mint")]


class Review(models.Model):
    product = models.ForeignKey(Product, related_name="reviews", null=True, blank=True, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=60)
    location = models.CharField(max_length=60, blank=True)
    rating = models.PositiveSmallIntegerField(default=5)
    text = models.TextField()
    is_verified = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, help_text="Show as a love note on the home page")
    is_approved = models.BooleanField(default=True)
    tint = models.CharField(max_length=10, choices=REVIEW_TINTS, default="primary")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} – {self.rating}★"

    @property
    def stars(self):
        return "★" * self.rating + "☆" * (5 - self.rating)


def video_storage():
    """Cloudinary keeps videos apart from images, so reels need its video storage when it's on."""
    if getattr(settings, "CLOUDINARY_ENABLED", False):
        from cloudinary_storage.storage import VideoMediaCloudinaryStorage
        return VideoMediaCloudinaryStorage()
    return default_storage


class Reel(ImageSourceMixin, models.Model):
    title = models.CharField(max_length=120)
    tag = models.CharField(max_length=30, blank=True, help_text="Top-left pill, e.g. 'Trending Audio'")
    tag_icon = models.CharField(max_length=30, default="graphic_eq")
    views = models.CharField(max_length=12, blank=True, help_text="e.g. 48.2K")
    likes = models.CharField(max_length=12, blank=True, help_text="e.g. 4.3k")
    image = models.ImageField(upload_to="reels/", blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    video = models.FileField(
        upload_to="reels/videos/", storage=video_storage, blank=True,
        validators=[FileExtensionValidator(["mp4", "webm", "mov"])],
        help_text="The reel's video (MP4). It plays silently on the home page; visitors tap for sound.",
    )
    video_url = models.URLField(max_length=500, blank=True, help_text="Or a direct link to an .mp4 file")
    reel_url = models.URLField(blank=True, help_text="Instagram reel link, opened by the Instagram button")
    product = models.ForeignKey(Product, null=True, blank=True, related_name="reels", on_delete=models.SET_NULL)
    cta_label = models.CharField(max_length=20, default="Shop Now")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title

    @property
    def video_src(self):
        return self.video.url if self.video else self.video_url


class Coupon(models.Model):
    FLAT, PERCENT = "flat", "percent"
    code = models.CharField(max_length=30, unique=True)
    kind = models.CharField(max_length=10, choices=[(FLAT, "Flat ₹ off"), (PERCENT, "% off")], default=FLAT)
    value = models.DecimalField(max_digits=9, decimal_places=2)
    min_subtotal = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    max_discount = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def evaluate(self, subtotal):
        """Return (discount, error_message)."""
        if not self.is_active or (self.valid_until and self.valid_until < timezone.now()):
            return Decimal("0"), "This code has expired."
        if subtotal < self.min_subtotal:
            return Decimal("0"), f"Add items worth ₹{self.min_subtotal - subtotal:,.0f} more to use {self.code}."
        if self.kind == self.PERCENT:
            discount = (subtotal * self.value / 100).quantize(Decimal("1"))
            if self.max_discount:
                discount = min(discount, self.max_discount)
        else:
            discount = self.value
        return min(discount, subtotal), ""


def generate_order_number():
    while True:
        number = f"JJ-{random.randint(10000, 99999)}"
        if not Order.objects.filter(number=number).exists():
            return number


class Order(TimeStamped):
    STATUS_CHOICES = [
        ("placed", "Order Received"),
        ("crafting", "Handcrafting"),
        ("packing", "Keepsake Packaging"),
        ("shipped", "Out for Delivery"),
        ("delivered", "Delivered with Love"),
        ("cancelled", "Cancelled"),
    ]
    PAYMENT_CHOICES = [
        ("upi", "Instant UPI"),
        ("card", "Credit / Debit Card"),
        ("netbanking", "NetBanking & Wallets"),
        ("cod", "Cash on Delivery"),
    ]
    DELIVERY_CHOICES = [("express", "Express NCR"), ("scheduled", "Scheduled Surprise"), ("standard", "Pan-India Courier")]

    number = models.CharField(max_length=12, unique=True, default=generate_order_number, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="orders", on_delete=models.SET_NULL)

    email = models.EmailField()
    phone = models.CharField(max_length=15)
    recipient_name = models.CharField(max_length=80)
    address_line1 = models.CharField("Flat / building", max_length=160)
    address_line2 = models.CharField("Street / area", max_length=160)
    city = models.CharField(max_length=60)
    state = models.CharField(max_length=60)
    pincode = models.CharField(max_length=6)

    delivery_mode = models.CharField(max_length=12, choices=DELIVERY_CHOICES, default="express")
    scheduled_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=12, choices=PAYMENT_CHOICES, default="upi")
    upi_id = models.CharField(max_length=60, blank=True)
    payment_reference = models.CharField(max_length=60, blank=True)
    is_paid = models.BooleanField(default=False)

    gift_note = models.CharField(max_length=200, blank=True)
    gift_from = models.CharField(max_length=40, blank=True)
    coupon_code = models.CharField(max_length=30, blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prepaid_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cod_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="placed")
    status_note = models.CharField(
        max_length=140, blank=True, help_text="Shown under the progress bar, e.g. 'Artisan Pooja is shaping petal #4'"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.number

    def get_absolute_url(self):
        return reverse("shop:order_detail", args=[self.number])

    @property
    def access_token(self):
        """Opens the order page without a login or session, for links sent by email or WhatsApp."""
        return Signer(salt="shop.order-access").signature(self.number)

    def get_share_url(self):
        return f"{self.get_absolute_url()}?k={self.access_token}"

    @property
    def upi_link(self):
        cfg = settings.JANJE
        if self.payment_method != "upi" or self.is_paid or not cfg["UPI_ID"]:
            return ""
        return (
            f"upi://pay?pa={quote(cfg['UPI_ID'])}&pn={quote(cfg['UPI_PAYEE_NAME'])}"
            f"&am={self.total:.2f}&cu=INR&tn={quote('Janje order ' + self.number)}"
        )

    TRACK_STEPS = ["placed", "crafting", "packing", "shipped", "delivered"]

    @property
    def step_index(self):
        return self.TRACK_STEPS.index(self.status) if self.status in self.TRACK_STEPS else -1

    @property
    def progress_percent(self):
        return {0: 12, 1: 40, 2: 65, 3: 85, 4: 100}.get(self.step_index, 0)

    @property
    def track_steps(self):
        labels = dict(self.STATUS_CHOICES)
        current = self.step_index
        return [
            {"label": labels[key], "done": i <= current, "current": i == current}
            for i, key in enumerate(self.TRACK_STEPS)
        ]

    @property
    def is_active_order(self):
        return self.status not in ("delivered", "cancelled")

    @property
    def total_discount(self):
        return self.coupon_discount + self.prepaid_discount

    @property
    def item_count(self):
        return sum(i.quantity for i in self.items.all())

    @property
    def estimated_delivery(self):
        if self.delivery_mode == "scheduled" and self.scheduled_date:
            return self.scheduled_date
        days = 2 if self.delivery_mode == "express" else 5
        return (self.created_at + timedelta(days=days)).date()

    @property
    def is_ncr(self):
        prefixes = settings.JANJE["NCR_PINCODE_PREFIXES"]
        return any(self.pincode.startswith(p) for p in prefixes)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL)
    addon = models.ForeignKey(AddOn, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    options = models.CharField(max_length=160, blank=True, help_text="Size • colour")
    category_label = models.CharField(max_length=40, blank=True)
    image_url = models.CharField(max_length=500, blank=True)
    icon = models.CharField(max_length=40, blank=True)
    unit_price = models.DecimalField(max_digits=9, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} × {self.name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    @property
    def is_addon(self):
        return self.addon_id is not None and self.product_id is None


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
