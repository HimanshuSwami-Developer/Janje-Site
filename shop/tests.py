from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Address
from shop.models import AddOn, Order, Product


class BoutiqueFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_shop", verbosity=0)
        cls.bouquet = Product.objects.get(name="Eternal Petal Bloom Bouquet")
        cls.clip = Product.objects.get(name="Fluffy Bunny Ears Claw Clip")

    def checkout_data(self, **overrides):
        data = {
            "phone": "98102 34891", "email": "sanvi@example.com", "recipient_name": "Sanvi Verma",
            "pincode": "122002", "address_line1": "Tower B, Flat 804", "address_line2": "Golf Course Road",
            "city": "Gurugram", "state": "Haryana", "delivery_mode": "express", "payment_method": "upi",
            "gift_note": "Forever in bloom ♡", "gift_from": "Aryan",
        }
        data.update(overrides)
        return data

    def test_storefront_pages_render(self):
        for url in [
            reverse("shop:home"), reverse("shop:product_list"), reverse("shop:category", args=["hair-claw-clips"]),
            reverse("shop:product_list") + "?q=bunny&sort=price_low", self.bouquet.get_absolute_url(),
            self.clip.get_absolute_url(), reverse("shop:wishlist"), reverse("shop:our_story"),
            reverse("accounts:login"), reverse("accounts:signup"), reverse("shop:cart"),
            reverse("shop:track_order"),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_home_shows_seeded_catalogue(self):
        html = self.client.get(reverse("shop:home")).content.decode()
        self.assertIn("Eternal Petal Bloom Bouquet", html)
        self.assertIn("Fresh from our reels", html)
        self.assertIn("Tanya S.", html)

    def test_search_filters_products(self):
        res = self.client.get(reverse("shop:product_list"), {"q": "bunny"})
        self.assertEqual([p.name for p in res.context["products"]], ["Fluffy Bunny Ears Claw Clip"])

    def test_bag_add_uses_size_price_and_addons(self):
        size = self.bouquet.sizes.get(name="7-Bloom Deluxe")
        mist = AddOn.objects.get(name="French Lavender Mist Infusion")
        res = self.client.post(reverse("shop:bag_add"), {
            "product_id": self.bouquet.pk, "size_id": size.pk, "qty": 2, "addons": [mist.pk], "gift_note": "Hi ♡",
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 4)  # 2 bouquets + 2 mists
        drawer = self.client.get(reverse("shop:bag")).json()["html"]
        self.assertIn("₹2,896", drawer)  # 2 × 1399 + 2 × 49

    def test_cart_page_lists_items_and_totals(self):
        self.assertContains(self.client.get(reverse("shop:cart")), "Your cart is feeling a little empty")
        res = self.client.post(reverse("shop:bag_add"), {"product_id": self.clip.pk, "qty": 2})
        self.assertEqual(res.json()["redirect"], reverse("shop:cart"))
        page = self.client.get(reverse("shop:cart"))
        self.assertContains(page, self.clip.name)
        self.assertContains(page, "₹698")

    def test_bag_quantity_update_and_remove(self):
        self.client.post(reverse("shop:bag_add"), {"product_id": self.clip.pk})
        key = next(iter(self.client.session["bag"]["lines"]))
        self.assertEqual(self.client.post(reverse("shop:bag_update"), {"key": key, "qty": 3}).json()["count"], 3)
        self.assertEqual(self.client.post(reverse("shop:bag_update"), {"key": key, "qty": 0}).json()["count"], 0)

    def test_coupon_rules(self):
        self.client.post(reverse("shop:bag_add"), {"product_id": self.clip.pk})
        res = self.client.post(reverse("shop:bag_coupon"), {"code": "BOWLOVE"})
        self.assertEqual(res.status_code, 400)  # needs ₹999
        res = self.client.post(reverse("shop:bag_coupon"), {"code": "welcome10"})
        self.assertTrue(res.json()["ok"])
        self.assertIn("₹35", res.json()["message"])

    def test_checkout_places_order_and_clears_bag(self):
        self.client.post(reverse("shop:bag_add"), {"product_id": self.bouquet.pk})
        self.client.post(reverse("shop:bag_coupon"), {"code": "WELCOME10"})
        stock_before = Product.objects.get(pk=self.bouquet.pk).stock
        res = self.client.post(reverse("shop:checkout"), self.checkout_data())
        order = Order.objects.get()
        self.assertRedirects(res, order.get_absolute_url())
        # 899 bouquet (5-bloom default) - 90 (10%) - 50 UPI prepaid, free shipping
        self.assertEqual(order.subtotal, Decimal("899"))
        self.assertEqual(order.coupon_discount, Decimal("90"))
        self.assertEqual(order.prepaid_discount, Decimal("50"))
        self.assertEqual(order.total, Decimal("759"))
        self.assertEqual(order.phone, "9810234891")
        self.assertEqual(order.delivery_mode, "express")
        self.assertEqual(order.items.get().options, "5-Bloom Classic • Pink Blossom")
        self.assertEqual(Product.objects.get(pk=self.bouquet.pk).stock, stock_before - 1)
        self.assertEqual(self.client.session["bag"]["lines"], {})
        self.assertEqual(len(mail.outbox), 1)
        page = self.client.get(order.get_absolute_url()).content.decode()
        self.assertIn(order.number, page)
        self.assertIn("Forever in bloom", page)

    def test_cod_and_shipping_fee_and_pan_india(self):
        self.client.post(reverse("shop:bag_add"), {"product_id": self.clip.pk})  # 349 < 499
        self.client.post(reverse("shop:checkout"), self.checkout_data(payment_method="cod", pincode="400001"))
        order = Order.objects.get()
        self.assertEqual(order.shipping_fee, Decimal("79"))
        self.assertEqual(order.cod_fee, Decimal("49"))
        self.assertEqual(order.total, Decimal("477"))
        self.assertEqual(order.delivery_mode, "standard")

    def test_checkout_validation_errors(self):
        self.client.post(reverse("shop:bag_add"), {"product_id": self.clip.pk})
        res = self.client.post(reverse("shop:checkout"), self.checkout_data(
            phone="123", pincode="12", delivery_mode="scheduled", scheduled_date=timezone.localdate().isoformat(),
        ))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(set(res.context["form"].errors), {"phone", "pincode", "scheduled_date"})
        self.assertFalse(Order.objects.exists())
        ok = self.client.post(reverse("shop:checkout"), self.checkout_data(
            delivery_mode="scheduled", scheduled_date=(timezone.localdate() + timedelta(days=3)).isoformat(),
        ))
        self.assertEqual(ok.status_code, 302)

    def test_empty_bag_checkout_redirects(self):
        self.assertRedirects(self.client.get(reverse("shop:checkout")), reverse("shop:product_list"))

    def test_order_page_is_private(self):
        self.client.post(reverse("shop:bag_add"), {"product_id": self.clip.pk})
        self.client.post(reverse("shop:checkout"), self.checkout_data())
        order = Order.objects.get()
        self.client.logout()
        self.client.cookies.clear()
        track_url = reverse("shop:track_order")
        self.assertRedirects(self.client.get(order.get_absolute_url()), f"{track_url}?number={order.number}")
        # Unknown numbers get the same response, so they can't be probed.
        self.assertRedirects(self.client.get(reverse("shop:order_detail", args=["JJ-00000"])), f"{track_url}?number=JJ-00000")

    def test_share_link_opens_order_on_any_device(self):
        self.client.post(reverse("shop:bag_add"), {"product_id": self.clip.pk})
        self.client.post(reverse("shop:checkout"), self.checkout_data())
        order = Order.objects.get()
        self.assertIn(f"?k={order.access_token}", mail.outbox[0].body)
        self.client.cookies.clear()
        res = self.client.get(order.get_share_url())
        self.assertContains(res, order.number)
        self.assertContains(res, 'property="og:image"')
        self.assertEqual(self.client.get(order.get_absolute_url()).status_code, 200)  # remembered
        self.client.cookies.clear()
        self.assertEqual(self.client.get(order.get_absolute_url() + "?k=forged").status_code, 302)

    @override_settings(JANJE={**settings.JANJE, "UPI_ID": "janje@okaxis", "WHATSAPP_NUMBER": "919810000000"})
    def test_order_page_has_upi_qr_and_whatsapp_send(self):
        self.client.post(reverse("shop:bag_add"), {"product_id": self.clip.pk})
        self.client.post(reverse("shop:checkout"), self.checkout_data())
        order = Order.objects.get()
        res = self.client.get(order.get_absolute_url())
        self.assertIn("upi://pay?pa=janje%40okaxis", res.context["upi_link"])
        self.assertContains(res, "UPI QR code")
        self.assertTrue(res.context["upi_qr"].startswith("<svg"))
        self.assertTrue(res.context["send_whatsapp_url"].startswith("https://wa.me/919810000000?text="))
        self.assertContains(res, "Send my order on WhatsApp")
        Order.objects.filter(pk=order.pk).update(is_paid=True)
        res = self.client.get(order.get_absolute_url())
        self.assertEqual(res.context["upi_qr"], "")

    @override_settings(JANJE={**settings.JANJE, "UPI_ID": "", "WHATSAPP_NUMBER": ""})
    def test_order_page_without_upi_or_whatsapp_configured(self):
        self.client.post(reverse("shop:bag_add"), {"product_id": self.clip.pk})
        self.client.post(reverse("shop:checkout"), self.checkout_data())
        res = self.client.get(Order.objects.get().get_absolute_url())
        self.assertEqual(res.context["upi_qr"], "")
        self.assertNotContains(res, "UPI QR code")
        self.assertNotContains(res, "Send my order on WhatsApp")
        self.assertContains(res, "UPI link for")

    def test_guest_can_track_order_with_email_or_phone(self):
        self.client.post(reverse("shop:bag_add"), {"product_id": self.clip.pk})
        self.client.post(reverse("shop:checkout"), self.checkout_data())
        order = Order.objects.get()
        Order.objects.filter(pk=order.pk).update(status="crafting")
        url = reverse("shop:track_order")
        for number, contact in [
            (order.number, "SANVI@example.com"),
            (order.number.removeprefix("JJ-"), "+91 98102 34891"),
            (order.number.lower().replace("-", ""), "9810234891"),
        ]:
            with self.subTest(number=number, contact=contact):
                self.client.cookies.clear()
                self.assertRedirects(self.client.post(url, {"number": number, "contact": contact}), order.get_absolute_url())
                page = self.client.get(order.get_absolute_url()).content.decode()
                self.assertIn("Handcrafting", page)
                self.assertIn('aria-current="step"', page)

    def test_track_order_rejects_wrong_details_and_throttles(self):
        cache.clear()
        self.client.post(reverse("shop:bag_add"), {"product_id": self.clip.pk})
        self.client.post(reverse("shop:checkout"), self.checkout_data())
        order = Order.objects.get()
        self.client.cookies.clear()
        url = reverse("shop:track_order")
        res = self.client.post(url, {"number": order.number, "contact": "someone@else.com"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("couldn", res.context["form"].non_field_errors()[0])
        self.assertEqual(self.client.get(order.get_absolute_url()).status_code, 302)
        for _ in range(10):
            self.client.post(url, {"number": "JJ-00000", "contact": "9810234891"})
        res = self.client.post(url, {"number": order.number, "contact": "sanvi@example.com"})
        self.assertTrue(res.context["throttled"])
        cache.clear()

    def test_wishlist_toggle(self):
        url = reverse("shop:wishlist_toggle")
        self.assertTrue(self.client.post(url, {"product_id": self.clip.pk}).json()["added"])
        self.assertContains(self.client.get(reverse("shop:wishlist")), self.clip.name)
        self.assertFalse(self.client.post(url, {"product_id": self.clip.pk}).json()["added"])

    def test_newsletter(self):
        res = self.client.post(reverse("shop:newsletter"), {"email": "Bow@Example.com"})
        self.assertIn("WELCOME10", res.json()["message"])
        self.assertEqual(self.client.post(reverse("shop:newsletter"), {"email": "nope"}).status_code, 400)


class AccountTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_shop", verbosity=0)

    def signup(self):
        return self.client.post(reverse("accounts:signup"), {
            "full_name": "Aryan Sharma", "email": "aryan@example.com", "phone": "9810234891",
            "password": "pink-bows-2026",
        })

    def test_signup_login_logout(self):
        self.assertRedirects(self.signup(), reverse("accounts:account"))
        account = self.client.get(reverse("accounts:account"))
        self.assertContains(account, "Aryan Sharma")
        self.assertContains(account, "9810234891")
        self.client.post(reverse("accounts:logout"))
        self.assertEqual(self.client.get(reverse("accounts:account")).status_code, 302)
        res = self.client.post(reverse("accounts:login"), {"email": "ARYAN@example.com", "password": "pink-bows-2026"})
        self.assertRedirects(res, reverse("accounts:account"))

    def test_bad_login(self):
        res = self.client.post(reverse("accounts:login"), {"email": "who@example.com", "password": "x"})
        self.assertContains(res, "don&#x27;t match")

    def test_account_orders_addresses_and_prefill(self):
        self.signup()
        product = Product.objects.get(name="Fluffy Bunny Ears Claw Clip")
        self.client.post(reverse("shop:bag_add"), {"product_id": product.pk})
        self.client.post(reverse("shop:checkout"), {
            "phone": "9810234891", "email": "aryan@example.com", "recipient_name": "Sanvi Verma", "pincode": "122002",
            "address_line1": "Tower B", "address_line2": "Sector 54", "city": "Gurugram", "state": "Haryana",
            "delivery_mode": "express", "payment_method": "upi", "gift_note": "Happy Birthday ♡", "save_address": "on",
        })
        user = get_user_model().objects.get(email="aryan@example.com")
        self.assertEqual(user.orders.count(), 1)
        self.assertEqual(Address.objects.filter(user=user).count(), 1)
        page = self.client.get(reverse("accounts:account")).content.decode()
        self.assertIn(user.orders.get().number, page)
        self.assertIn("Happy Birthday", page)
        # address book feeds checkout
        self.client.post(reverse("shop:bag_add"), {"product_id": product.pk})
        form = self.client.get(reverse("shop:checkout")).context["form"]
        self.assertEqual(form.initial["recipient_name"], "Sanvi Verma")
        self.assertEqual(form.initial["phone"], "9810234891")

    def test_review_requires_login_and_updates_rating(self):
        product = Product.objects.get(name="Cherry Blossom Floral Clip")
        url = reverse("shop:review_create", args=[product.slug])
        self.assertEqual(self.client.post(url, {"rating": 5, "text": "Love!"}).status_code, 302)
        self.assertEqual(product.reviews.count(), 0)
        self.signup()
        self.client.post(url, {"rating": 5, "text": "So pretty!", "location": "Noida"})
        product.refresh_from_db()
        self.assertEqual(product.reviews.count(), 1)
        self.assertEqual(product.review_count, 20)


class SettingsHelperTests(TestCase):
    def test_env_file_loading_and_whatsapp_number(self):
        import os
        import tempfile
        from pathlib import Path

        from janje.settings import load_env_file, whatsapp_number

        self.assertEqual(whatsapp_number("97187 51020"), "919718751020")
        self.assertEqual(whatsapp_number("+91 97187 51020"), "919718751020")
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / ".env"
            env.write_text('# note\nJANJE_TEST_A="quoted value"\nJANJE_TEST_B=from-file\n')
            os.environ["JANJE_TEST_B"] = "from-shell"
            try:
                load_env_file(env)
                self.assertEqual(os.environ["JANJE_TEST_A"], "quoted value")
                self.assertEqual(os.environ["JANJE_TEST_B"], "from-shell")
            finally:
                os.environ.pop("JANJE_TEST_A", None)
                os.environ.pop("JANJE_TEST_B", None)
