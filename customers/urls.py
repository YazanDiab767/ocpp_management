from django.urls import path
from customers import views

urlpatterns = [
    path('', views.customer_list, name='customer-list'),
    path('create/', views.customer_create, name='customer-create'),
    path('<int:pk>/', views.customer_detail, name='customer-detail'),
    path('<int:pk>/edit/', views.customer_update, name='customer-update'),
    path('<int:pk>/wallet/topup/', views.wallet_topup, name='wallet-topup'),
    path('<int:pk>/wallet/ledger/', views.wallet_ledger, name='wallet-ledger'),
]
