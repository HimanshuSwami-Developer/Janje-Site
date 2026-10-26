from django import forms
from django.contrib.auth import get_user_model, password_validation

from shop.forms import clean_indian_phone

from .models import Address

User = get_user_model()


class SignupForm(forms.Form):
    full_name = forms.CharField(max_length=80)
    email = forms.EmailField()
    phone = forms.CharField(max_length=16)
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists — try signing in.")
        return email

    def clean_phone(self):
        return clean_indian_phone(self.cleaned_data["phone"])

    def clean(self):
        data = super().clean()
        if data.get("password"):
            user = User(username=data.get("email", ""), email=data.get("email", ""), first_name=data.get("full_name", ""))
            try:
                password_validation.validate_password(data["password"], user)
            except forms.ValidationError as e:
                self.add_error("password", e)
        return data

    def save(self):
        d = self.cleaned_data
        first, _, last = d["full_name"].strip().partition(" ")
        user = User.objects.create_user(
            username=d["email"], email=d["email"], password=d["password"], first_name=first, last_name=last
        )
        user.profile.phone = d["phone"]
        user.profile.save()
        return user


class LoginForm(forms.Form):
    email = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["label", "recipient_name", "phone", "line1", "line2", "city", "state", "pincode", "is_default"]

    def clean_phone(self):
        return clean_indian_phone(self.cleaned_data["phone"])


class ProfileForm(forms.Form):
    full_name = forms.CharField(max_length=80)
    phone = forms.CharField(max_length=16)

    def clean_phone(self):
        return clean_indian_phone(self.cleaned_data["phone"])
