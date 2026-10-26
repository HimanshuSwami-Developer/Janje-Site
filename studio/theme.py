"""Fonts and colours the shop owner can pick in Studio › Appearance."""
from urllib.parse import quote_plus

# family -> (Google Fonts weight spec, CSS fallback)
FONTS = {
    "Caveat": ("wght@400;500;600;700", "cursive"),
    "Dancing Script": ("wght@400;500;600;700", "cursive"),
    "Pacifico": ("", "cursive"),
    "Great Vibes": ("", "cursive"),
    "Satisfy": ("", "cursive"),
    "Patrick Hand": ("", "cursive"),
    "Shadows Into Light": ("", "cursive"),
    "Playfair Display": ("wght@400;500;600;700;800", "serif"),
    "Fraunces": ("wght@400;500;600;700;800", "serif"),
    "Lora": ("wght@400;500;600;700", "serif"),
    "Nunito": ("wght@400;500;600;700;800", "sans-serif"),
    "Quicksand": ("wght@400;500;600;700", "sans-serif"),
    "Poppins": ("wght@400;500;600;700;800", "sans-serif"),
    "DM Sans": ("wght@400;500;600;700;800", "sans-serif"),
    "Inter": ("wght@400;500;600;700;800", "sans-serif"),
    "Montserrat": ("wght@400;500;600;700;800", "sans-serif"),
    "Lato": ("wght@400;700;900", "sans-serif"),
}
FONT_CHOICES = [(name, name) for name in FONTS]

# field name on SiteSettings -> (CSS variable, label, default)
COLORS = [
    ("color_primary", "--c-primary", "Buttons & accents", "#B4485F"),
    ("color_primary_dark", "--c-primary-dark", "Accent hover", "#8E3448"),
    ("color_text", "--c-text", "Text", "#4A2C26"),
    ("color_muted", "--c-muted", "Soft text", "#7A5A52"),
    ("color_background", "--c-bg", "Page background", "#FFF7F2"),
    ("color_soft", "--c-soft", "Pink panels", "#F9DDE1"),
    ("color_line", "--c-line", "Borders & dashes", "#EBC3CA"),
    ("color_yellow", "--c-yellow", "Yellow notes", "#FCF0B9"),
    ("color_lilac", "--c-lilac", "Lilac notes", "#E9E1F7"),
    ("color_blue", "--c-blue", "Blue tags", "#DCEAF7"),
]


def font_stack(name):
    return f"'{name}', {FONTS.get(name, ('', 'sans-serif'))[1]}"


def google_fonts_url(*names):
    families = []
    for name in dict.fromkeys(n for n in names if n in FONTS):
        spec = FONTS[name][0]
        families.append("family=" + quote_plus(name) + (f":{spec}" if spec else ""))
    return "https://fonts.googleapis.com/css2?" + "&".join(families) + "&display=swap"


def hex_to_rgb(value):
    value = (value or "").lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    try:
        return " ".join(str(int(value[i:i + 2], 16)) for i in (0, 2, 4))
    except ValueError:
        return "0 0 0"
