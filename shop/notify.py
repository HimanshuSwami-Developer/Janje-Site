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


def order_whatsapp_text(order, share_url):
    eta = order.estimated_delivery
    lines = _item_lines(order)
    if order.is_paid:
        payment = f"Payment of {rupees(order.total)} received, thank you ✓\nTrack your order here:"
    elif order.payment_method == "cod":
        payment = f"Please keep {rupees(order.total)} ready to pay in cash on delivery.\nTrack your order here:"
    else:
        payment = f"Total to pay: *{rupees(order.total)}* by UPI"
        if settings.JANJE["UPI_ID"]:
            payment += f" to *{settings.JANJE['UPI_ID']}* (add {order.number} in the note)"
        payment += ".\nScan the QR or tap “Pay with a UPI app” here:"
    return (
        f"Hi {order.gift_from or order.recipient_name} ♡\n"
        f"Thank you for your Janjé order *#{order.number}*!\n\n"
        f"{lines}\n\n"
        f"{payment}\n{share_url}\n\n"
        f"Status: {order.get_status_display()}"
        + (f" · arriving by {eta:%a}, {eta.day} {eta:%b}" if order.is_active_order else "")
        + "\nHandcrafted with love, Janjé 🎀"
    )


def customer_whatsapp_url(order, share_url):
    """wa.me link that opens a chat with the customer, message pre-filled."""
    return f"https://wa.me/91{order.phone}?text={quote(order_whatsapp_text(order, share_url))}"


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
