from django.urls import path

from accounts import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('users/', views.user_list, name='user-list'),
    path('users/create/', views.user_create, name='user-create'),
    path('users/<int:pk>/', views.user_detail, name='user-detail'),
    path('users/<int:pk>/edit/', views.user_update, name='user-update'),
    path('users/<int:pk>/permissions/', views.user_permissions, name='user-permissions'),
    path('users/<int:pk>/toggle-active/', views.user_toggle_active, name='user-toggle-active'),
]
