from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('customers/', include('customers.urls')),
    path('rfid/', include('rfid.urls')),
    path('chargers/', include('chargers.urls')),
    path('sessions/', include('sessions.urls')),
    path('billing/', include('billing.urls')),
    path('', include('dashboard.urls')),
]
