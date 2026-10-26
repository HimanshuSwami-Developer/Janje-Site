from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.account, name="account"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile_update, name="profile"),
    path("addresses/add/", views.address_add, name="address_add"),
    path("addresses/<int:pk>/delete/", views.address_delete, name="address_delete"),
]
