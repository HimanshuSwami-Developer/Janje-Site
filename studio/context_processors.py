from .models import SiteSettings
from .resources import RESOURCES


def studio(request):
    user = getattr(request, "user", None)
    is_staff = bool(user and user.is_authenticated and user.is_staff)
    return {
        "site": SiteSettings.load(),
        "is_studio_user": is_staff,
        "cms_edit": is_staff and request.session.get("cms_edit", False),
        "studio_nav": [(r.slug, r.title) for r in RESOURCES.values()] if is_staff else [],
    }
