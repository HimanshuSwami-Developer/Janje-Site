from django.conf import settings

from .cart import Bag, wishlist_ids
from .models import Category


def boutique(request):
    cfg = settings.JANJE
    whatsapp = cfg["WHATSAPP_NUMBER"]
    handle = cfg["INSTAGRAM_HANDLE"]
    wishlist = wishlist_ids(request)
    return {
        "bag_count": Bag(request).count,
        "wishlist_ids": wishlist,
        "wishlist_count": len(wishlist),
        "nav_categories": Category.objects.filter(is_active=True),
        "instagram_handle": handle,
        "instagram_url": f"https://instagram.com/{handle}",
        "whatsapp_url": f"https://wa.me/{whatsapp}" if whatsapp else "https://wa.me/",
        "free_shipping_threshold": cfg["FREE_SHIPPING_THRESHOLD"],
    }
