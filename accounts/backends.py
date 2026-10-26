from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Let customers sign in with their email address (or the admin username)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        User = get_user_model()
        user = (
            User.objects.filter(email__iexact=username).order_by("id").first()
            or User.objects.filter(username__iexact=username).first()
        )
        if user is None:
            User().set_password(password)  # equalise timing with the found-user path
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
