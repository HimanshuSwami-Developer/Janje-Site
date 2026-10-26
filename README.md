# Janjé – Blush & Bow

Django storefront for Janjé's handcrafted pipe-cleaner bouquets, claw clips and hair accessories.
The UI is the Google Stitch design ("Shoppable Reels E-Commerce Store"), rebuilt as Django templates
with Tailwind CSS and jQuery.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_shop          # starter catalogue from the design
.venv/bin/python manage.py createsuperuser    # for /admin/
.venv/bin/python manage.py runserver
```

Open http://127.0.0.1:8000 for the shop and http://127.0.0.1:8000/admin/ to manage it.

Settings come from environment variables (see `.env.example`). Copy it to `.env` and Django loads it on
startup; variables set in your shell or hosting dashboard take priority.
Set `JANJE_WHATSAPP_NUMBER` and `JANJE_UPI_ID` before going live.

## What's included

| Area | Details |
| --- | --- |
| Storefront | Home (hero, categories, bestseller filter, reels, love notes), shop/category listing with search and sort, product page, wishlist, Our Story |
| Product page | Size variants with their own prices, colour swatches, gallery, gifting add-ons, quantity, live price, Express Buy Now, reviews (signed-in customers) |
| Bag | Slide-over drawer (AJAX). Quantities, add-on upsells, a gift note, and free-shipping progress |
| Checkout | Address validation (Indian phone/pincode), NCR vs pan-India detection, scheduled delivery date, coupons, live summary, UPI (₹50 off) or COD (+₹49) |
| Orders | Confirmation page with a live status timeline, an email receipt, and a UPI scan-to-pay QR/deep link when `JANJE_UPI_ID` is set |
| Accounts | Email signup/login, order history with progress, saved addresses (these pre-fill checkout), saved gift notes, Blossom points |
| Admin | Products (with images, sizes and colours inline), categories, add-ons, reels, reviews, coupons, orders, newsletter |

### Studio (the shop owner's dashboard) — `/studio/`
Sign in with a staff account (`createsuperuser`, or tick *staff status* on a user in `/admin/`).
- **Edit site live**: turns on edit mode on the shop. Click any heading, button or sentence to change its words,
  colour, size, font, weight or italics. On the home page, drag sections by their blue bar or hide them.
- **Products**: add, edit, duplicate, delete; drag rows to reorder; switch *active / bestseller / hero* inline.
  The product form holds photos, sizes (each with a price) and colours, all drag-to-reorder.
- **Categories, Reels, Reviews, Gift add-ons, Coupons**: the same list / edit / delete screens.
- **Orders**: filter by status, update status and payment, WhatsApp the customer.
- **Colours & fonts**: the site palette, Google fonts for headings / body / logo, text size, announcement bar,
  custom CSS, with a live preview.
- **All text**: every editable piece of copy in one searchable list (a page's text appears after it's opened once).

### Managing the shop (Django admin)
- **Products**: upload a photo or paste an image URL. Add sizes/colours inline. Tick *is hero* for the two home hero cards.
- **Orders**: change **status** (Order Received → Handcrafting → Packaging → Out for Delivery → Delivered) and
  tick **is paid** once a UPI payment lands. Customers see the change on their order page and account.
  *Status note* appears under the progress bar.
- **Coupons**: seeded with `BOWLOVE` (₹100 off over ₹999) and `WELCOME10` (10% off, max ₹200).
- The seeded product photos are the images hosted by the Stitch design. Swap them for your own uploads.

### Payments
UPI works without a payment gateway. After the order is placed, the customer gets a QR code and a UPI app
link for the exact amount, with the order number in the note. You check your UPI app, then mark the order
as paid in the admin. Card and NetBanking are shown as "Coming soon". Connecting a gateway such as Razorpay
would be the next step.

## Project layout

```
janje/        settings & root urls
shop/         catalogue, bag (session), checkout, orders, reviews, reels, coupons
accounts/     email login, profile, saved addresses
templates/    base layout + partials + page templates (Stitch markup)
static/js/    app.js (jQuery interactions), tailwind.config.js (Stitch theme tokens)
```

## Tests

```bash
.venv/bin/python manage.py test
```

## Production notes
- Set `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`.
  Run `collectstatic` and serve `staticfiles/` and `media/`.
- Tailwind loads from the Play CDN, as in the Stitch export. For production, compile it with the
  Tailwind CLI using `static/js/tailwind.config.js` as the theme.
- Configure a real email backend so customers receive their receipts.
