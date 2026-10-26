from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()

BADGE_CLASSES = {
    "primary": "bg-primary text-on-primary",
    "secondary": "bg-secondary text-on-secondary",
    "tertiary": "bg-tertiary text-on-tertiary",
    "soft": "bg-primary-fixed text-on-primary-fixed",
}

NOTE_TINTS = {
    "primary": ("bg-primary-fixed/40", "border-primary/10"),
    "secondary": ("bg-secondary-fixed/50", "border-secondary/10"),
    "tertiary": ("bg-tertiary-fixed/40", "border-tertiary/10"),
}


def _indian_grouping(n):
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


@register.filter
def rupees(value):
    """1199 -> ₹1,199 ; 1234.50 -> ₹1,234.50 (Indian digit grouping)."""
    if value in (None, ""):
        return ""
    try:
        amount = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    sign = "-" if amount < 0 else ""
    amount = abs(amount)
    whole = int(amount)
    paise = int((amount - whole) * 100)
    text = _indian_grouping(whole)
    if paise:
        text += f".{paise:02d}"
    return f"{sign}₹{text}"


@register.filter
def badge_classes(style):
    return BADGE_CLASSES.get(style, BADGE_CLASSES["primary"])


@register.filter
def note_bg(tint):
    return NOTE_TINTS.get(tint, NOTE_TINTS["primary"])[0]


@register.filter
def note_border(tint):
    return NOTE_TINTS.get(tint, NOTE_TINTS["primary"])[1]


@register.filter
def times(n):
    try:
        return range(int(n))
    except (TypeError, ValueError):
        return range(0)
