from django.urls import path

from . import views

app_name = "studio"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("orders/", views.orders, name="orders"),
    path("orders/<int:pk>/", views.order_detail, name="order"),
    path("appearance/", views.appearance, name="appearance"),
    path("text/", views.content, name="content"),
    path("text/save/", views.content_save, name="content_save"),
    path("text/blocks/", views.content_blocks, name="content_blocks"),
    path("layout/", views.layout, name="layout"),
    path("layout/save/", views.sections_save, name="sections_save"),
    path("edit-mode/", views.edit_mode, name="edit_mode"),
    path("products/<int:pk>/duplicate/", views.product_duplicate, name="duplicate"),
    path("<slug:slug>/", views.resource_list, name="list"),
    path("<slug:slug>/new/", views.resource_edit, name="new"),
    path("<slug:slug>/reorder/", views.resource_reorder, name="reorder"),
    path("<slug:slug>/<int:pk>/", views.resource_edit, name="edit"),
    path("<slug:slug>/<int:pk>/toggle/", views.resource_toggle, name="toggle"),
    path("<slug:slug>/<int:pk>/delete/", views.resource_delete, name="delete"),
]
