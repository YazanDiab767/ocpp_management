from django.urls import path
from billing import views

urlpatterns = [
    path('tariffs/', views.tariff_list, name='tariff-list'),
    path('tariffs/create/', views.tariff_create, name='tariff-create'),
    path('tariffs/<int:pk>/edit/', views.tariff_update, name='tariff-update'),
    path('tariffs/<int:pk>/activate/', views.tariff_activate, name='tariff-activate'),
    path('policy/', views.billing_policy, name='billing-policy'),
]
