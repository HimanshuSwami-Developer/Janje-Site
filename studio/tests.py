import html
import json
import re
import tempfile
from datetime import timedelta
from decimal import Decimal
from urllib.parse import unquote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from shop.models import Category, Order, Product, Reel

from .models import ContentBlock, PageSection, SiteSettings


class StudioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_shop", verbosity=0)
        User = get_user_model()
        cls.staff = User.objects.create_user("owner", "owner@example.com", "pink-bows-2026", is_staff=True)
        cls.customer = User.objects.create_user("buyer", "buyer@example.com", "pink-bows-2026")

    def setUp(self):
        self.client.force_login(self.staff)

    def test_only_staff_get_in(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("studio:dashboard")).status_code, 302)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("studio:dashboard")).status_code, 404)
        self.assertEqual(self.client.post(reverse("studio:content_save"), {"key": "x"}).status_code, 404)

    def test_every_screen_renders(self):
        self.client.get(reverse("shop:home"))  # registers the home page text
        product = Product.objects.first()
        order = self._order()
        urls = [
            reverse("studio:dashboard"), reverse("studio:orders"), reverse("studio:reports"), reverse("studio:order", args=[order.pk]),
            reverse("studio:appearance"), reverse("studio:content"), reverse("studio:layout"),
            reverse("studio:edit", args=["products", product.pk]), reverse("studio:new", args=["products"]),
        ]
        for slug in ["products", "categories", "reels", "reviews", "addons", "coupons"]:
            urls += [reverse("studio:list", args=[slug]), reverse("studio:new", args=[slug])]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def _order(self):
        return Order.objects.create(
            email="a@b.co", phone="9810234891", recipient_name="Sanvi", address_line1="Flat 1", address_line2="Road",
            city="Gurugram", state="Haryana", pincode="122002", total=Decimal("899"),
        )

    def test_create_product_with_size_and_colour(self):
        category = Category.objects.first()
        data = {
            "name": "Tulip Bouquet", "category": category.pk, "price": "799", "stock": "10",
            "image_url": "https://example.com/tulip.jpg", "badge_style": "primary", "is_active": "on",
            "images-TOTAL_FORMS": "0", "images-INITIAL_FORMS": "0",
            "sizes-TOTAL_FORMS": "1", "sizes-INITIAL_FORMS": "0",
            "sizes-0-name": "3 stems", "sizes-0-price": "799", "sizes-0-sort_order": "0", "sizes-0-is_default": "on",
            "colors-TOTAL_FORMS": "1", "colors-INITIAL_FORMS": "0",
            "colors-0-name": "Blush", "colors-0-hex": "#F4B6C2", "colors-0-sort_order": "0",
        }
        res = self.client.post(reverse("studio:new", args=["products"]), data)
        self.assertRedirects(res, reverse("studio:list", args=["products"]))
        product = Product.objects.get(name="Tulip Bouquet")
        self.assertEqual(product.slug, "tulip-bouquet")
        self.assertEqual(product.sizes.get().name, "3 stems")
        self.assertEqual(product.colors.get().hex, "#F4B6C2")

    def test_product_needs_a_photo(self):
        res = self.client.post(reverse("studio:new", args=["products"]), {
            "name": "No photo", "category": Category.objects.first().pk, "price": "10", "stock": "1",
            "badge_style": "primary",
            "images-TOTAL_FORMS": "0", "images-INITIAL_FORMS": "0", "sizes-TOTAL_FORMS": "0", "sizes-INITIAL_FORMS": "0",
            "colors-TOTAL_FORMS": "0", "colors-INITIAL_FORMS": "0",
        })
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Product.objects.filter(name="No photo").exists())

    def test_reorder_toggle_duplicate_and_delete(self):
        a, b = Product.objects.all()[:2]
        self.client.post(reverse("studio:reorder", args=["products"]),
                         json.dumps({"ids": [b.pk, a.pk]}), content_type="application/json")
        self.assertEqual(list(Product.objects.order_by("sort_order").values_list("pk", flat=True)[:2]), [b.pk, a.pk])

        res = self.client.post(reverse("studio:toggle", args=["products", a.pk]), {"field": "is_active"})
        self.assertFalse(res.json()["value"])
        self.assertEqual(self.client.post(reverse("studio:toggle", args=["products", a.pk]), {"field": "price"}).status_code, 404)

        self.client.post(reverse("studio:duplicate", args=[b.pk]))
        copy = Product.objects.get(name=f"{b.name} (copy)")
        self.assertFalse(copy.is_active)
        self.assertEqual(copy.sizes.count(), b.sizes.count())

        self.client.post(reverse("studio:delete", args=["products", copy.pk]))
        self.assertFalse(Product.objects.filter(pk=copy.pk).exists())

    def test_category_with_products_is_protected(self):
        category = Category.objects.filter(products__isnull=False).first()
        self.client.post(reverse("studio:delete", args=["categories", category.pk]))
        self.assertTrue(Category.objects.filter(pk=category.pk).exists())

    def test_text_edit_shows_on_the_shop(self):
        self.client.get(reverse("shop:home"))
        block = ContentBlock.objects.get(key="home.hero.title")
        self.assertEqual(block.text, "Blush & Bow")
        res = self.client.post(reverse("studio:content_save"), {
            "key": "home.hero.title", "text": "Spring <Bloom>", "color": "#112233", "size": "70", "weight": "800",
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTrue(res.json()["ok"])
        html = self.client.get(reverse("shop:home")).content.decode()
        self.assertIn('style="color:#112233;font-size:70px;font-weight:800">Spring &lt;Bloom&gt;', html)

        self.client.post(reverse("studio:content_save"), {"key": "home.hero.title", "reset": "1"},
                         HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        block.refresh_from_db()
        self.assertEqual((block.text, block.color, block.size), ("Blush & Bow", "", None))

        bad = self.client.post(reverse("studio:content_save"), {"key": "home.hero.title", "text": "x", "color": "red"},
                               HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(bad.status_code, 400)

    def test_sections_reorder_and_hide(self):
        self.client.get(reverse("shop:home"))
        order = ["reviews", "hero", "categories", "offers", "products", "about", "reels"]
        self.client.post(reverse("studio:sections_save"), json.dumps({
            "page": "home", "order": order, "visible": {"reels": False},
        }), content_type="application/json")
        self.assertEqual([s.key for s in PageSection.objects.filter(page="home")], order)
        html = self.client.get(reverse("shop:home")).content.decode()
        self.assertLess(html.index('id="reviews"'), html.index("home.hero.title"))
        self.assertNotIn('id="reels"', html)

    def test_appearance_changes_theme(self):
        data = {
            "show_announcement": "", "font_heading": "Pacifico", "font_body": "Poppins", "font_logo": "Great Vibes",
            "base_font_size": "17", "custom_css": "", "color_primary": "#123456", "color_primary_dark": "#8E3448",
            "color_text": "#4A2C26", "color_muted": "#7A5A52", "color_background": "#FFF7F2", "color_soft": "#F9DDE1",
            "color_line": "#EBC3CA", "color_yellow": "#FCF0B9", "color_lilac": "#E9E1F7", "color_blue": "#DCEAF7",
        }
        self.assertRedirects(self.client.post(reverse("studio:appearance"), data), reverse("studio:appearance"))
        html = self.client.get(reverse("shop:home")).content.decode()
        self.assertIn("--c-primary: 18 52 86;", html)
        self.assertIn("--font-heading: 'Pacifico', cursive;", html)
        self.assertIn("family=Pacifico", html)
        self.assertNotIn("global.announcement", html)
        self.assertEqual(SiteSettings.load().base_font_size, 17)

    def test_edit_mode_is_staff_only(self):
        self.client.get(reverse("studio:edit_mode") + "?on=1&next=/")
        self.assertContains(self.client.get(reverse("shop:home")), "studio/editor.js")
        self.client.force_login(self.customer)
        session = self.client.session
        session["cms_edit"] = True
        session.save()
        self.assertNotContains(self.client.get(reverse("shop:home")), "studio/editor.js")

    def test_reel_video_upload(self):
        field = Reel._meta.get_field("video")
        original = field.storage
        with tempfile.TemporaryDirectory() as tmp:
            field.storage = FileSystemStorage(location=tmp, base_url="/media/")
            try:
                reel = Reel.objects.first()
                data = {"title": reel.title, "image_url": reel.image_url, "cta_label": "Shop", "is_active": "on",
                        "video": SimpleUploadedFile("daisy.mp4", b"fake-mp4", content_type="video/mp4")}
                res = self.client.post(reverse("studio:edit", args=["reels", reel.pk]), data)
                self.assertEqual(res.status_code, 302)
                reel.refresh_from_db()
                self.assertTrue(reel.video.name.startswith("reels/videos/daisy"))
                self.assertEqual(reel.video_src, reel.video.url)
                self.assertContains(self.client.get(reverse("studio:edit", args=["reels", reel.pk])), "<video")
                bad = dict(data, video=SimpleUploadedFile("notes.txt", b"x", content_type="text/plain"))
                self.assertEqual(self.client.post(reverse("studio:edit", args=["reels", reel.pk]), bad).status_code, 200)
            finally:
                field.storage = original

    def test_whatsapp_message_follows_status(self):
        order = self._order()
        order.items.create(name="Eternal Petal Bloom Bouquet", options="5-Bloom Classic", unit_price=Decimal("899"))

        def wa_text(url):
            page = self.client.get(url).content.decode()
            return unquote(html.unescape(re.search(r'href="https://wa\.me/91\d+\?text=([^"]+)"', page).group(1)))

        self.assertContains(self.client.get(reverse("studio:order", args=[order.pk])), "Confirm order on WhatsApp")
        self.assertIn("is confirmed ✓", wa_text(reverse("studio:order", args=[order.pk])))
        self.client.post(reverse("studio:order", args=[order.pk]), {"status": "shipped", "status_note": ""})
        self.assertIn("out for delivery", wa_text(reverse("studio:order", args=[order.pk])))
        self.assertIn("out for delivery", wa_text(reverse("studio:orders")))
        self.client.force_login(get_user_model().objects.create_superuser("boss", "boss@example.com", "pink-bows-2026"))
        admin_page = self.client.get(reverse("admin:shop_order_changelist"))
        self.assertContains(admin_page, "Send “Out for delivery” update")

    def test_sales_report(self):
        today = timezone.now()
        product = Product.objects.first()
        for status, total, days_ago in [("placed", "500", 0), ("delivered", "300", 2), ("cancelled", "999", 0), ("placed", "200", 40)]:
            order = self._order()
            Order.objects.filter(pk=order.pk).update(status=status, total=Decimal(total), created_at=today - timedelta(days=days_ago))
            order.items.create(product=product, name=product.name, unit_price=Decimal(total), quantity=2)
        res = self.client.get(reverse("studio:reports"))
        self.assertEqual(res.status_code, 200)
        totals = res.context["totals"]
        self.assertEqual((totals["sales"], totals["orders"], totals["items"]), (Decimal("800"), 2, 4))
        self.assertEqual(len(res.context["rows"]), 30)
        self.assertEqual(res.context["products"][0]["qty"], 4)
        today_iso = timezone.localdate().isoformat()
        one_day = self.client.get(reverse("studio:reports") + f"?period=day&on={today_iso}")
        self.assertEqual(one_day.context["products"][0]["revenue"], Decimal("1000"))
        month = self.client.get(reverse("studio:reports") + "?period=month").context
        self.assertEqual((month["totals"]["orders"], len(month["rows"])), (3, 12))
        week = self.client.get(reverse("studio:reports") + "?period=week").context
        self.assertEqual(len(week["rows"]), 12)
        self.assertEqual(week["rows"][-1]["start"].weekday(), 0)

    def test_order_status_update(self):
        order = self._order()
        self.client.post(reverse("studio:order", args=[order.pk]), {"status": "crafting", "is_paid": "on", "status_note": ""})
        order.refresh_from_db()
        self.assertEqual((order.status, order.is_paid), ("crafting", True))

    @override_settings(JANJE={**settings.JANJE, "UPI_ID": "janje@okaxis"})
    def test_send_order_on_whatsapp_button(self):
        order = self._order()
        order.items.create(name="Eternal Petal Bloom Bouquet", options="5-Bloom Classic", unit_price=Decimal("899"))
        page = self.client.get(reverse("studio:order", args=[order.pk])).content.decode()
        link = re.search(r'href="(https://wa\.me/91[^"]+)"', page).group(1)
        number, text = link.split("?text=")
        self.assertEqual(number, f"https://wa.me/91{order.phone}")
        text = unquote(html.unescape(text))
        self.assertIn(f"#{order.number}", text)
        self.assertIn("janje@okaxis", text)
        self.assertIn(f"?k={order.access_token}", text)
        for item in order.items.all():
            self.assertIn(item.name, text)
