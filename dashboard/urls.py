from django.urls import path
from dashboard import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard-home'),
    path('reports/sessions/', views.report_sessions, name='report-sessions'),
    path('reports/revenue/', views.report_revenue, name='report-revenue'),
]
