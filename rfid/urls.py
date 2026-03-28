from django.urls import path
from rfid import views

urlpatterns = [
    path('', views.card_list, name='card-list'),
    path('tap-log/', views.tap_log, name='rfid-tap-log'),
    path('create/', views.card_create, name='card-create'),
    path('<int:pk>/', views.card_detail, name='card-detail'),
    path('<int:pk>/edit/', views.card_update, name='card-update'),
    path('<int:pk>/assign/', views.card_assign, name='card-assign'),
    path('<int:pk>/block/', views.card_block, name='card-block'),
    path('<int:pk>/unassign/', views.card_unassign, name='card-unassign'),
]
