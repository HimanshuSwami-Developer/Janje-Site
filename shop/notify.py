"""Customer messages about an order (email and WhatsApp share text)."""
from urllib.parse import quote

import segno
from django.conf import settings

from .templatetags.shop_tags import rupees


def _item_lines(order):
    return "\n".join(
        f"• {i.quantity} × {i.name}{f' ({i.options})' if i.options else ''} - {rupees(i.line_total)}"
        for i in order.items.all()
    )


# Opening line of the customer message for each order status.
STATUS_HEADLINES = {
    "placed": "Your Janjé order *#{number}* is confirmed ✓ Thank you!",
    "crafting": "Our artisans have started handcrafting your order *#{number}* 🌸",
    "packing": "Your order *#{number}* is being wrapped in keepsake packaging 🎁",
    "shipped": "Your order *#{number}* is out for delivery 🚚",
    "delivered": "Your order *#{number}* has been delivered ♡ We hope you love it!",
    "cancelled": "Your order *#{number}* has been cancelled.",
}

WHATSAPP_ACTIONS = {
    "placed": "Confirm order on WhatsApp",
    "crafting": "Send “Handcrafting” update",
    "packing": "Send “Packaging” update",
    "shipped": "Send “Out for delivery” update",
    "delivered": "Send “Delivered” message",
    "cancelled": "Send cancellation message",
}


def _payment_line(order):
    if order.is_paid:
        return f"Payment of {rupees(order.total)} received, thank you ✓\nTrack your order here:"
    if order.payment_method == "cod":
        return f"Please keep {rupees(order.total)} ready to pay in cash on delivery.\nTrack your order here:"
    payment = f"Total to pay: *{rupees(order.total)}* by UPI"
    if settings.JANJE["UPI_ID"]:
        payment += f" to *{settings.JANJE['UPI_ID']}* (add {order.number} in the note)"
    return payment + ".\nScan the QR or tap “Pay with a UPI app” here:"


def order_whatsapp_text(order, share_url):
    """The message the shop sends the customer, worded for the order's current status."""
    eta = order.estimated_delivery
    headline = STATUS_HEADLINES.get(order.status, STATUS_HEADLINES["placed"]).format(number=order.number)
    parts = [f"Hi {order.gift_from or order.recipient_name} ♡\n{headline}"]
    if order.status == "placed":
        parts.append(_item_lines(order))
    if order.status_note and order.is_active_order:
        parts.append(order.status_note)
    if order.status == "cancelled":
        parts.append(f"If you've already paid, your refund of {rupees(order.total)} is on its way. "
                     f"Questions? Just reply here.\n{share_url}" if order.is_paid
                     else f"Questions? Just reply here.\n{share_url}")
    elif order.status == "delivered":
        parts.append(f"We'd love a photo or a review ♡\n{share_url}")
    else:
        parts.append(f"{_payment_line(order)}\n{share_url}")
        if order.is_active_order:
            parts.append(f"Arriving by {eta:%a}, {eta.day} {eta:%b}")
    return "\n\n".join(parts) + "\nHandcrafted with love, Janjé 🎀"


def whatsapp_action_label(order):
    return WHATSAPP_ACTIONS.get(order.status, "Send on WhatsApp")


def customer_whatsapp_url(order, share_url):
    """wa.me link that opens a chat with the customer, message pre-filled."""
    return f"https://wa.me/91{order.phone}?text={quote(order_whatsapp_text(order, share_url))}"


def customer_whatsapp_url_for(request, order):
    return customer_whatsapp_url(order, request.build_absolute_uri(order.get_share_url()))


def shop_whatsapp_url(order, share_url):
    """wa.me link the customer taps to send their order to the shop's WhatsApp."""
    number = settings.JANJE["WHATSAPP_NUMBER"]
    if not number:
        return ""
    payment = (
        "Paid ✓" if order.is_paid
        else "Cash on delivery" if order.payment_method == "cod"
        else "Paying by UPI"
    )
    text = (
        f"Hi Janjé! I just placed order *#{order.number}* ♡\n\n"
        f"{_item_lines(order)}\n\n"
        f"Total: *{rupees(order.total)}* ({payment})\n"
        f"Deliver to: {order.recipient_name}, {order.city} {order.pincode}\n\n"
        f"Order & UPI QR: {share_url}"
    )
    return f"https://wa.me/{number}?text={quote(text)}"


def upi_qr_svg(upi_link):
    """Inline SVG QR for a upi:// link, drawn on the server so it never depends on a CDN script."""
    if not upi_link:
        return ""
    return segno.make(upi_link, error="m").svg_inline(scale=4, border=0, dark="#4A2C26", omitsize=True)
