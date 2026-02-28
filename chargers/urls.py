from django.urls import path
from chargers import views

urlpatterns = [
    path('', views.charger_list, name='charger-list'),
    path('create/', views.charger_create, name='charger-create'),
    path('<uuid:pk>/', views.charger_detail, name='charger-detail'),
    path('<uuid:pk>/edit/', views.charger_update, name='charger-update'),
    path('<uuid:pk>/messages/', views.charger_messages, name='charger-messages'),
]
