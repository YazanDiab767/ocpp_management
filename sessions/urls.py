from django.urls import path
from sessions import views

urlpatterns = [
    path('', views.session_list, name='session-list'),
    path('active/', views.active_sessions, name='session-active'),
    path('<int:transaction_id>/', views.session_detail, name='session-detail'),
]
