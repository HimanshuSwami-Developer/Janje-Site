import re

from django.core.validators import RegexValidator
from django.db import models

from .theme import COLORS, FONT_CHOICES, font_stack, google_fonts_url, hex_to_rgb

hex_color = RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Use a colour like #B4485F.")


class SiteSettings(models.Model):
    """One row of site-wide appearance settings."""

    show_announcement = models.BooleanField("Show the announcement bar", default=True)
    font_heading = models.CharField("Headings font", max_length=40, choices=FONT_CHOICES, default="Caveat")
    font_body = models.CharField("Body font", max_length=40, choices=FONT_CHOICES, default="Nunito")
    font_logo = models.CharField("Logo font", max_length=40, choices=FONT_CHOICES, default="Dancing Script")
    base_font_size = models.PositiveSmallIntegerField("Base text size (px)", default=16)
    custom_css = models.TextField(blank=True, help_text="Extra CSS added to every page. For advanced tweaks.")
    updated_at = models.DateTimeField(auto_now=True)

    # Keep in step with theme.COLORS
    color_primary = models.CharField("Buttons & accents", max_length=7, default="#B4485F", validators=[hex_color])
    color_primary_dark = models.CharField("Accent hover", max_length=7, default="#8E3448", validators=[hex_color])
    color_text = models.CharField("Text", max_length=7, default="#4A2C26", validators=[hex_color])
    color_muted = models.CharField("Soft text", max_length=7, default="#7A5A52", validators=[hex_color])
    color_background = models.CharField("Page background", max_length=7, default="#FFF7F2", validators=[hex_color])
    color_soft = models.CharField("Pink panels", max_length=7, default="#F9DDE1", validators=[hex_color])
    color_line = models.CharField("Borders & dashes", max_length=7, default="#EBC3CA", validators=[hex_color])
    color_yellow = models.CharField("Yellow notes", max_length=7, default="#FCF0B9", validators=[hex_color])
    color_lilac = models.CharField("Lilac notes", max_length=7, default="#E9E1F7", validators=[hex_color])
    color_blue = models.CharField("Blue tags", max_length=7, default="#DCEAF7", validators=[hex_color])

    class Meta:
        verbose_name = verbose_name_plural = "site settings"

    def __str__(self):
        return "Site settings"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @property
    def fonts_url(self):
        return google_fonts_url(self.font_heading, self.font_body, self.font_logo)

    @property
    def css_variables(self):
        lines = [f"{var}: {hex_to_rgb(getattr(self, field))};" for field, var, _, _ in COLORS]
        lines += [
            f"--font-heading: {font_stack(self.font_heading)};",
            f"--font-body: {font_stack(self.font_body)};",
            f"--font-logo: {font_stack(self.font_logo)};",
        ]
        return " ".join(lines)

    @property
    def safe_custom_css(self):
        return self.custom_css.replace("</", "<\\/")


FONT_ROLES = [("heading", "Headings font"), ("body", "Body font"), ("logo", "Logo font")]
WEIGHTS = [("400", "Regular"), ("600", "Semibold"), ("700", "Bold"), ("800", "Extra bold")]


class ContentBlock(models.Model):
    """A piece of site copy, editable in place. Created the first time its page renders."""

    key = models.CharField(max_length=120, unique=True)
    default = models.TextField(blank=True, help_text="The text the template ships with")
    text = models.TextField(blank=True)
    color = models.CharField(max_length=7, blank=True, validators=[hex_color])
    size = models.PositiveSmallIntegerField("Size (px)", null=True, blank=True)
    font = models.CharField(max_length=10, choices=FONT_ROLES, blank=True)
    weight = models.CharField(max_length=3, choices=WEIGHTS, blank=True)
    italic = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key

    @property
    def page(self):
        return self.key.split(".", 1)[0]

    @property
    def is_styled(self):
        return bool(self.color or self.size or self.font or self.weight or self.italic)

    @property
    def style(self):
        rules = []
        if self.color and re.fullmatch(r"#[0-9A-Fa-f]{6}", self.color):
            rules.append(f"color:{self.color}")
        if self.size:
            rules.append(f"font-size:{max(8, min(self.size, 200))}px")
        if self.font in dict(FONT_ROLES):
            rules.append(f"font-family:var(--font-{self.font})")
        if self.weight in dict(WEIGHTS):
            rules.append(f"font-weight:{self.weight}")
        if self.italic:
            rules.append("font-style:italic")
        return ";".join(rules)


class PageSection(models.Model):
    """A block of a page that can be reordered or hidden."""

    page = models.CharField(max_length=30)
    key = models.CharField(max_length=40)
    label = models.CharField(max_length=60)
    sort_order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["page", "sort_order", "id"]
        unique_together = [("page", "key")]

    def __str__(self):
        return f"{self.page}: {self.label}"

    @property
    def template(self):
        return f"shop/{self.page}/{self.key}.html"


HOME_SECTIONS = [
    ("hero", "Hero"),
    ("categories", "Category circles"),
    ("offers", "Offer cards"),
    ("products", "Product grid"),
    ("about", "About us"),
    ("reels", "Reels"),
    ("reviews", "Love notes"),
]
PAGE_SECTIONS = {"home": HOME_SECTIONS}


def sections_for(page):
    """All sections of a page in order, adding any the code knows about but the database doesn't yet."""
    known = PAGE_SECTIONS[page]
    existing = {s.key: s for s in PageSection.objects.filter(page=page)}
    missing = [
        PageSection(page=page, key=key, label=label, sort_order=i)
        for i, (key, label) in enumerate(known) if key not in existing
    ]
    if missing:
        PageSection.objects.bulk_create(missing, ignore_conflicts=True)
    valid = {key for key, _ in known}
    return [s for s in PageSection.objects.filter(page=page) if s.key in valid]
