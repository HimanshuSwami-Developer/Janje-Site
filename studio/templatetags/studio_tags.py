from django import template
from django.template.defaultfilters import linebreaksbr
from django.utils.html import format_html

from studio.models import ContentBlock

register = template.Library()


def get_block(context, key, default):
    """Look a block up once per request; create it with the template's default text on first sight."""
    request = context.get("request")
    cache = getattr(request, "_cms_blocks", None) if request else None
    if cache is None:
        cache = {b.key: b for b in ContentBlock.objects.all()}
        if request:
            request._cms_blocks = cache
    block = cache.get(key)
    if block is None:
        block, _ = ContentBlock.objects.get_or_create(key=key, defaults={"default": default, "text": default})
        cache[key] = block
    elif block.default != default:
        # The template's default changed; keep it current so "Reset" restores the new text.
        ContentBlock.objects.filter(pk=block.pk).update(default=default)
        block.default = default
    return block


@register.simple_tag(takes_context=True)
def txt(context, key, default=""):
    """Editable text: {% txt "home.hero.title" "Blush & Bow" %}."""
    block = get_block(context, key, default)
    body = linebreaksbr(block.text, autoescape=True)
    if block.style:
        return format_html('<span data-cms="{}" style="{}">{}</span>', key, block.style, body)
    return format_html('<span data-cms="{}">{}</span>', key, body)


@register.simple_tag(takes_context=True)
def txt_plain(context, key, default=""):
    """The same text without the editable wrapper, for attributes and <title>."""
    return get_block(context, key, default).text
