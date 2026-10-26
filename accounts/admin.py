from django.contrib import admin

from .models import Address, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "phone", "city"]
    search_fields = ["user__email", "user__first_name", "phone"]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["recipient_name", "user", "label", "city", "pincode", "is_default"]
    search_fields = ["recipient_name", "user__email", "pincode"]
