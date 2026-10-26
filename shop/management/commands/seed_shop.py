"""Load the boutique's starter catalogue (products, add-ons, reels, reviews, coupons).

    python manage.py seed_shop           # create anything missing (safe to re-run)
    python manage.py seed_shop --reset   # wipe catalogue data first (orders are kept)
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from shop.models import AddOn, Category, Coupon, Product, ProductColor, ProductImage, ProductSize, Reel, Review

from ._design_images import IMAGES as I

CATEGORIES = [
    ("Flower Bouquets", "flower-bouquets", "🌸", "Bouquets", "Everlasting craft stems", "cat_bouquets"),
    ("Hair Claw Clips", "hair-claw-clips", "✨", "Clips", "Plush & high-grip hold", "cat_clips"),
    ("Floral Hairbands", "floral-hairbands", "🎀", "Hairbands", "Pinch-free satin bands", "cat_bands"),
    ("Festive Collection", "festive-collection", "🪔", "Festive", "Navratri & Diwali drops", "cat_festive"),
]

# name, category slug, price, compare, image key, badge, badge style, rating, reviews, short description, swatches, extra
PRODUCTS = [
    ("Eternal Petal Bloom Bouquet", "flower-bouquets", 899, 1199, "bouquet_pdp", "Bestseller", "primary", "4.9", 128,
     "Forever in bloom with baby's breath", "#f472b6,#e4e0f5,#c3ecd7",
     {"hero": True, "sticker": "Handmade with love ♡",
      "description": "Meticulously sculpted from ultra-plush velvet pipe cleaners with luminous faux pearl stamens, "
                     "wrapped in Korean frosted paper and crowned with our signature satin bow. An everlasting "
                     "expression of warmth that never wilts."}),
    ("Fluffy Bunny Ears Claw Clip", "hair-claw-clips", 349, 499, "bunny_clip", "Trending", "secondary", "5.0", 88,
     "Ultra-soft plush finish with strong hold", "#a43073,#ffffff",
     {"hero": True, "sticker": "Super soft & cozy ♡",
      "description": "A cloud-soft velvet claw clip topped with fluffy handmade bunny ears. Strong-hold spring keeps "
                     "thick or wavy hair in place all day — through lectures, meetings and everything in between."}),
    ("Cherry Blossom Floral Clip", "hair-claw-clips", 329, 420, "cherry_clip", "", "primary", "4.8", 19,
     "Delicate pastel pink wire petals", "#ffafd3,#e4e0f5", {}),
    ("Sunny Daisy Mini Hairpins", "hair-claw-clips", 249, 350, "daisy_pins", "", "primary", "4.7", 31,
     "Set of 2 cute floral bobby pins", "#ffffff,#ffd8e7", {}),
    ("Pastel Star Clips (Set of 5)", "hair-claw-clips", 299, 399, "star_clips", "College Hit", "tertiary", "4.9", 64,
     "Rainbow candy snap clips", "#ffd8e7,#c3ecd7,#e4e0f5", {}),
    ("Velvet Flower Bands (3-Pack)", "floral-hairbands", 399, 549, "velvet_bands", "", "primary", "5.0", 27,
     "Pain-free everyday comfort headbands", "#f472b6,#e4e0f5", {}),
    ("Festive Bloom Ties / Brooch", "festive-collection", 449, 599, "festive_brooch", "Festive Special", "secondary", "4.8", 15,
     "Ethnic touch for garba & pooja outfits", "#a43073,#416656", {}),
    ("Sunshine Forever Bouquet", "flower-bouquets", 949, 1250, "sunshine_bouquet", "New Drop", "soft", "5.0", 36,
     "Bright cheerful decor keepsake", "#e4e0f5,#ffafd3", {}),
    # Pairings shown on product pages
    ("Velvet Ribbon Hairband", "floral-hairbands", 399, None, "ribbon_hairband", "", "primary", "4.9", 22,
     "Hand-tied coquette bow", "#ffd8e7", {"bestseller": False}),
    ("Pastel Sparkle Clips (Pair)", "hair-claw-clips", 299, None, "sparkle_clips", "", "primary", "4.8", 17,
     "Strong grip clamp", "#fde047,#ffd8e7", {"bestseller": False}),
    ("Blossom Hairpins (Set of 2)", "hair-claw-clips", 249, None, "blossom_pins", "New", "tertiary", "4.9", 9,
     "Hand-bent petals", "#c084fc,#ffafd3", {"bestseller": False}),
    ("Pastel Bloom Ties (3-Pack)", "floral-hairbands", 399, None, "bloom_ties", "", "primary", "5.0", 41,
     "Lavender, soft peach & cream pearls", "#c084fc,#fb923c,#fbf9f5", {"bestseller": False}),
]

BOUQUET_SIZES = [
    ("1 Bloom Solo", "Cute Single", 349, 449, ""),
    ("3-Bloom Petite", "Tender Trio", 599, 799, ""),
    ("5-Bloom Classic", "Signature Wrap", 899, 1199, "Bestseller"),
    ("7-Bloom Deluxe", "Grand Hamper", 1399, 1799, ""),
]

BOUQUET_COLORS = [
    ("Pink Blossom", "🌸", "#f472b6"), ("Lilac Lavender", "💜", "#c084fc"), ("Sunshine Yellow", "💛", "#fde047"),
    ("Cherry Red", "❤️", "#f43f5e"), ("Baby Sky Blue", "🩵", "#7dd3fc"), ("Cloud White", "🤍", "#ffffff"),
    ("Peach Coral", "🍑", "#fb923c"), ("Royal Violet", "🔮", "#7c3aed"), ("Hot Magenta Fuchsia", "🌺", "#db2777"),
]

CLIP_COLORS = [("Hot Pink & White", "🐰", "#a43073"), ("Cloud White", "🤍", "#ffffff"), ("Blush Pink", "🌸", "#ffafd3")]

ADDONS = [
    ("Add Matching Bunny Claw Clip", "Matching Bunny Clip", "Special bundle discount", 299, 399, "", "addon_bunny", True, False),
    ("French Lavender Mist Infusion", "French Bouquet Mist", "Scented petals that smell like fresh blooms", 49, None, "air", "addon_mist", True, True),
    ("Luxury Acrylic Gift Box with Bow", "Pink Keepsake Box", "Dustproof keepsake presentation", 99, None, "featured_seasonal_and_gifts", "addon_box", True, True),
]

REELS = [
    ("5 Ways to Style Star Clips for College! 🌟", "Trending Audio", "graphic_eq", "48.2K", "4.3k", "star_clips", "Pastel Star Clips (Set of 5)", "Shop Clip"),
    ("Handcrafting a pipe cleaner daisy from scratch 🌸", "DIY Process", "handshake", "82.5K", "8.9k", "daisy_pins", "Sunny Daisy Mini Hairpins", "Shop Daisy"),
    ("All 9 color variants of our eternal bouquet! 💐", "All 9 Shades", "palette", "125K", "12.1k", "cat_bouquets", "Eternal Petal Bloom Bouquet", "Pick Color"),
    ("POV: The softest bunny claw clip you will ever own 🐰", "Bunny Fluff", "pets", "64.1K", "5.7k", "bunny_clip", "Fluffy Bunny Ears Claw Clip", "Get Clip"),
]

LOVE_NOTES = [
    ("Tanya S.", "New Delhi", "primary", "Fluffy Bunny Ears Claw Clip",
     "The cutest hair accessory ever! The bunny claw clip holds my thick wavy hair comfortably all day during lectures without slipping. Received so many compliments at college!"),
    ("Ananya K.", "Gurgaon", "secondary", "Eternal Petal Bloom Bouquet",
     "Gifted the purple forever flower bouquet to my best friend for her 21st birthday. She was literally in tears! It sits permanently on her study table. The packaging was top tier!"),
    ("Meher R.", "Noida", "tertiary", "Sunshine Forever Bouquet",
     "Ordered customized yellow & pink bouquets for our bridesmaid hamper box. The seller was super kind on WhatsApp and dispatched everything within 2 days. 10/10 recommend Janjé!"),
]

PRODUCT_REVIEWS = [
    ("Ananya S.", "Cyber Hub, Gurgaon", "Eternal Petal Bloom Bouquet",
     "Ordered the Pink Blossom 5-bloom bouquet for my bestie's birthday! She cried happy tears. The petals are so soft and fuzzy, and the pearl centers give it such a rich vintage vibe."),
    ("Rhea Kapoor", "South Extension, Delhi", "Eternal Petal Bloom Bouquet",
     "I was worried it might get squished in courier, but the box packaging was so sturdy! The Korean wrapping paper was pristine and the handwritten note card was so pretty."),
]


class Command(BaseCommand):
    help = "Seed the Janjé boutique with the starter catalogue from the design."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing catalogue data first")

    @transaction.atomic
    def handle(self, *args, reset=False, **options):
        if reset:
            for model in (Review, Reel, ProductImage, ProductSize, ProductColor, AddOn, Coupon):
                model.objects.all().delete()
            Product.objects.filter(orderitem__isnull=True).delete()
            Category.objects.filter(products__isnull=True).delete()

        cats = {}
        for order, (name, slug, emoji, short, tagline, img) in enumerate(CATEGORIES):
            cats[slug], _ = Category.objects.update_or_create(
                slug=slug,
                defaults=dict(name=name, emoji=emoji, short_name=short, tagline=tagline, image_url=I[img], sort_order=order),
            )

        products = {}
        for order, row in enumerate(PRODUCTS):
            name, cat, price, compare, img, badge, style, rating, count, short, swatches, extra = row
            p, created = Product.objects.get_or_create(
                name=name,
                defaults=dict(
                    category=cats[cat], price=Decimal(price), compare_at_price=Decimal(compare) if compare else None,
                    image_url=I[img], badge=badge, badge_style=style, rating=Decimal(rating), review_count=count,
                    short_description=short, swatches=swatches, sort_order=order,
                    description=extra.get("description", ""), sticker=extra.get("sticker", ""),
                    is_hero=extra.get("hero", False), is_bestseller=extra.get("bestseller", True),
                ),
            )
            products[name] = p

        bouquet = products["Eternal Petal Bloom Bouquet"]
        if not bouquet.sizes.exists():
            for i, (n, sub, price, compare, badge) in enumerate(BOUQUET_SIZES):
                ProductSize.objects.create(product=bouquet, name=n, subtitle=sub, price=price, compare_at_price=compare,
                                           badge=badge, is_default=(badge == "Bestseller"), sort_order=i)
        if not bouquet.colors.exists():
            for i, (n, emoji, hex_) in enumerate(BOUQUET_COLORS):
                ProductColor.objects.create(product=bouquet, name=n, emoji=emoji, hex=hex_, sort_order=i)
        if not bouquet.images.exists():
            for i, (key, label) in enumerate([("bouquet_macro", "Details"), ("bouquet_yellow_pdp", "Yellow"), ("bouquet_lavender", "Lavender")]):
                ProductImage.objects.create(product=bouquet, image_url=I[key], label=label, sort_order=i)

        bunny = products["Fluffy Bunny Ears Claw Clip"]
        if not bunny.colors.exists():
            for i, (n, emoji, hex_) in enumerate(CLIP_COLORS):
                ProductColor.objects.create(product=bunny, name=n, emoji=emoji, hex=hex_, sort_order=i)

        for i, (name, short, desc, price, compare, icon, img, on_product, in_bag) in enumerate(ADDONS):
            AddOn.objects.get_or_create(
                name=name,
                defaults=dict(short_name=short, description=desc, price=price, compare_at_price=compare, icon=icon,
                              image_url=I[img], show_on_product=on_product, show_in_bag=in_bag, sort_order=i),
            )

        for i, (title, tag, icon, views, likes, img, product, cta) in enumerate(REELS):
            Reel.objects.get_or_create(
                title=title,
                defaults=dict(tag=tag, tag_icon=icon, views=views, likes=likes, image_url=I[img],
                              product=products.get(product), cta_label=cta, sort_order=i),
            )

        for name, city, tint, product, text in LOVE_NOTES:
            Review.objects.get_or_create(
                name=name, text=text,
                defaults=dict(location=city, tint=tint, product=products.get(product), is_featured=True),
            )
        for name, city, product, text in PRODUCT_REVIEWS:
            Review.objects.get_or_create(name=name, text=text, defaults=dict(location=city, product=products[product]))

        Coupon.objects.get_or_create(code="BOWLOVE", defaults=dict(kind=Coupon.FLAT, value=100, min_subtotal=999))
        Coupon.objects.get_or_create(code="WELCOME10", defaults=dict(kind=Coupon.PERCENT, value=10, max_discount=200))

        if options.get("verbosity", 1):
            self.stdout.write(self.style.SUCCESS(
                f"Boutique ready: {Category.objects.count()} categories, {Product.objects.count()} products, "
                f"{AddOn.objects.count()} add-ons, {Reel.objects.count()} reels, {Review.objects.count()} reviews, "
                f"{Coupon.objects.count()} coupons."
            ))
