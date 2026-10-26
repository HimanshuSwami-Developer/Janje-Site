from django.contrib import admin

from .models import ContentBlock, PageSection, SiteSettings


@admin.register(ContentBlock)
class ContentBlockAdmin(admin.ModelAdmin):
    list_display = ["key", "text", "updated_at"]
    search_fields = ["key", "text"]


@admin.register(PageSection)
class PageSectionAdmin(admin.ModelAdmin):
    list_display = ["page", "label", "sort_order", "is_visible"]
    list_editable = ["sort_order", "is_visible"]


admin.site.register(SiteSettings)
