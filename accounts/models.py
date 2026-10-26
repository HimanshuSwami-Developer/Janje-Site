from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="profile", on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True)
    city = models.CharField(max_length=60, blank=True)

    def __str__(self):
        return f"Profile of {self.user}"


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="addresses", on_delete=models.CASCADE)
    label = models.CharField(max_length=30, default="Personal", help_text="e.g. Personal, Birthday / Bestie ♡")
    recipient_name = models.CharField(max_length=80)
    phone = models.CharField(max_length=15)
    line1 = models.CharField("Flat / building", max_length=160)
    line2 = models.CharField("Street / area", max_length=160)
    city = models.CharField(max_length=60)
    state = models.CharField(max_length=60)
    pincode = models.CharField(max_length=6)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "-id"]
        verbose_name_plural = "addresses"

    def __str__(self):
        return f"{self.recipient_name}, {self.city}"

    @property
    def one_line(self):
        return f"{self.line1}, {self.line2}, {self.city}, {self.state} - {self.pincode}"
