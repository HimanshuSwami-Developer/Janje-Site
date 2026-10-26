import re

from django import forms
from django.utils import timezone

from .models import Order, Review

INPUT = (
    "w-full px-4 py-3 rounded-2xl bg-surface-container-low text-on-surface font-body-md text-body-md "
    "focus:outline-none focus:bg-surface-container-lowest focus:ring-2 focus:ring-primary-container transition-all"
)


def clean_indian_phone(value):
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) != 10 or digits[0] not in "6789":
        raise forms.ValidationError("Please enter a valid 10-digit Indian mobile number.")
    return digits


class CheckoutForm(forms.Form):
    phone = forms.CharField(max_length=16)
    email = forms.EmailField()
    recipient_name = forms.CharField(max_length=80)
    pincode = forms.CharField(max_length=6)
    address_line1 = forms.CharField(max_length=160)
    address_line2 = forms.CharField(max_length=160)
    city = forms.CharField(max_length=60)
    state = forms.CharField(max_length=60)
    delivery_mode = forms.ChoiceField(choices=[("express", "Express"), ("scheduled", "Scheduled")], initial="express")
    scheduled_date = forms.DateField(required=False)
    payment_method = forms.ChoiceField(choices=[("upi", "UPI"), ("cod", "Cash on Delivery")], initial="upi")
    upi_id = forms.CharField(max_length=60, required=False)
    gift_note = forms.CharField(max_length=200, required=False)
    gift_from = forms.CharField(max_length=40, required=False)
    save_address = forms.BooleanField(required=False)

    def clean_phone(self):
        return clean_indian_phone(self.cleaned_data["phone"])

    def clean_pincode(self):
        pincode = self.cleaned_data["pincode"].strip()
        if not re.fullmatch(r"[1-9]\d{5}", pincode):
            raise forms.ValidationError("Please enter a valid 6-digit pincode.")
        return pincode

    def clean_upi_id(self):
        upi = self.cleaned_data.get("upi_id", "").strip()
        if upi and not re.fullmatch(r"[\w.\-]{2,}@[a-zA-Z]{2,}", upi):
            raise forms.ValidationError("That UPI ID doesn't look right (e.g. name@okaxis).")
        return upi

    def clean(self):
        data = super().clean()
        if data.get("delivery_mode") == "scheduled":
            date = data.get("scheduled_date")
            if not date:
                self.add_error("scheduled_date", "Pick the celebration date for your surprise.")
            elif date <= timezone.localdate():
                self.add_error("scheduled_date", "Please choose a date from tomorrow onwards.")
        return data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "location", "text"]
        widgets = {
            "rating": forms.Select(choices=[(i, f"{i} ★") for i in range(5, 0, -1)]),
            "text": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_rating(self):
        rating = self.cleaned_data["rating"]
        if not 1 <= rating <= 5:
            raise forms.ValidationError("Rating must be between 1 and 5.")
        return rating


class NewsletterForm(forms.Form):
    email = forms.EmailField()


class TrackOrderForm(forms.Form):
    """Lets guests find an order with its number plus the email or phone used at checkout."""

    number = forms.CharField(max_length=20)
    contact = forms.CharField(max_length=254)

    def clean_number(self):
        number = re.sub(r"\s", "", self.cleaned_data["number"]).upper().lstrip("#")
        if number.isdigit():
            number = f"JJ-{number}"
        if not re.fullmatch(r"JJ-?\d{5}", number):
            raise forms.ValidationError("Order numbers look like JJ-12345.")
        return number if "-" in number else f"JJ-{number[2:]}"

    def clean(self):
        data = super().clean()
        number, contact = data.get("number"), data.get("contact", "").strip()
        if not number or not contact:
            return data
        order = Order.objects.filter(number=number).first()
        if order and "@" in contact:
            matched = order.email.lower() == contact.lower()
        elif order:
            try:
                matched = order.phone == clean_indian_phone(contact)
            except forms.ValidationError:
                matched = False
        else:
            matched = False
        if not matched:
            raise forms.ValidationError(
                "We couldn't find an order with those details. Check the order number and use the "
                "email or phone you gave at checkout."
            )
        self.order = order
        return data


def order_from_form(form, user=None):
    d = form.cleaned_data
    return Order(
        user=user if user and user.is_authenticated else None,
        email=d["email"],
        phone=d["phone"],
        recipient_name=d["recipient_name"],
        address_line1=d["address_line1"],
        address_line2=d["address_line2"],
        city=d["city"],
        state=d["state"],
        pincode=d["pincode"],
        delivery_mode=d["delivery_mode"],
        scheduled_date=d.get("scheduled_date") if d["delivery_mode"] == "scheduled" else None,
        payment_method=d["payment_method"],
        upi_id=d.get("upi_id", ""),
        gift_note=d.get("gift_note", ""),
        gift_from=d.get("gift_from", ""),
    )
