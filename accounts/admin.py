from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from accounts.models import PagePermission

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('phone_number', 'full_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active')
    search_fields = ('phone_number', 'full_name')
    ordering = ('-date_joined',)
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        ('Personal Info', {'fields': ('full_name',)}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'page_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'full_name', 'role', 'password1', 'password2'),
        }),
    )
    filter_horizontal = ('page_permissions',)


@admin.register(PagePermission)
class PagePermissionAdmin(admin.ModelAdmin):
    list_display = ('page_key', 'display_name', 'section')
    list_filter = ('section',)
    ordering = ('section', 'display_name')
