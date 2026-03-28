from django.urls import path
from sessions import views

urlpatterns = [
    path('', views.session_list, name='session-list'),
    path('active/', views.active_sessions, name='session-active'),
    path('<int:transaction_id>/', views.session_detail, name='session-detail'),
    path('<int:transaction_id>/remote-stop/', views.session_remote_stop, name='session-remote-stop'),
    path('<int:transaction_id>/force-close/', views.session_force_close, name='session-force-close'),
    path('<int:transaction_id>/reset-charger/', views.session_reset_charger, name='session-reset-charger'),
]
