from django.urls import path

from . import views

app_name = "shop"

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.product_list, name="product_list"),
    path("shop/<slug:slug>/", views.product_list, name="category"),
    path("product/<slug:slug>/", views.product_detail, name="product"),
    path("product/<slug:slug>/review/", views.review_create, name="review_create"),
    path("our-story/", views.our_story, name="our_story"),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/toggle/", views.wishlist_toggle, name="wishlist_toggle"),
    path("cart/", views.cart, name="cart"),
    path("bag/", views.bag_drawer, name="bag"),
    path("bag/add/", views.bag_add, name="bag_add"),
    path("bag/add-on/", views.bag_add_addon, name="bag_add_addon"),
    path("bag/update/", views.bag_update, name="bag_update"),
    path("bag/note/", views.bag_note, name="bag_note"),
    path("bag/coupon/", views.bag_coupon, name="bag_coupon"),
    path("checkout/", views.checkout, name="checkout"),
    path("checkout/summary/", views.checkout_summary, name="checkout_summary"),
    path("track-order/", views.track_order, name="track_order"),
    path("order/<str:number>/", views.order_detail, name="order_detail"),
    path("newsletter/", views.newsletter_signup, name="newsletter"),
]
