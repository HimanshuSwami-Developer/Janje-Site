from django import forms
from django.forms import inlineformset_factory

from shop.models import Order, Product, ProductColor, ProductImage, ProductSize

from .models import ContentBlock, SiteSettings
from .theme import COLORS


class ColorInput(forms.TextInput):
    input_type = "color"


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = (
            ["show_announcement"] + [field for field, _, _, _ in COLORS]
            + ["font_heading", "font_body", "font_logo", "base_font_size", "custom_css"]
        )
        widgets = {field: ColorInput() for field, _, _, _ in COLORS}
        widgets["custom_css"] = forms.Textarea(attrs={"rows": 5, "class": "font-mono text-sm"})

    def clean_base_font_size(self):
        size = self.cleaned_data["base_font_size"]
        if not 12 <= size <= 22:
            raise forms.ValidationError("Pick a size between 12 and 22 px.")
        return size


class ContentBlockForm(forms.ModelForm):
    class Meta:
        model = ContentBlock
        fields = ["text", "color", "size", "font", "weight", "italic"]
        widgets = {"text": forms.Textarea(attrs={"rows": 2})}

    def clean_size(self):
        size = self.cleaned_data.get("size")
        if size is not None and not 8 <= size <= 200:
            raise forms.ValidationError("Size must be between 8 and 200 px.")
        return size


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name", "category", "short_description", "description", "price", "compare_at_price", "stock",
            "image", "image_url", "badge", "badge_style", "sticker", "swatches",
            "is_active", "is_bestseller", "is_hero", "slug",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}
        help_texts = {"slug": "The web address. Leave blank to make one from the name."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False

    def clean(self):
        data = super().clean()
        if not data.get("image") and not data.get("image_url") and not (self.instance and self.instance.image):
            self.add_error("image", "Upload a photo or paste an image link.")
        return data


ImageFormSet = inlineformset_factory(
    Product, ProductImage, fields=["image", "image_url", "label", "sort_order"], extra=0, can_delete=True,
    widgets={"sort_order": forms.HiddenInput()},
)
SizeFormSet = inlineformset_factory(
    Product, ProductSize, fields=["name", "subtitle", "price", "compare_at_price", "badge", "is_default", "sort_order"],
    extra=0, can_delete=True, widgets={"sort_order": forms.HiddenInput()},
)
ColorFormSet = inlineformset_factory(
    Product, ProductColor, fields=["name", "emoji", "hex", "sort_order"], extra=0, can_delete=True,
    widgets={"sort_order": forms.HiddenInput(), "hex": ColorInput()},
)


class OrderUpdateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["status", "status_note", "is_paid", "payment_reference"]
