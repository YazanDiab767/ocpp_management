from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from accounts.managers import UserManager


# Every page in the system that can be controlled by permissions.
# The key is stored in the database, the tuple is (display name, section group).
PAGE_REGISTRY = {
    'dashboard':        ('Dashboard',        'Dashboard'),
    'customers':        ('Customers',        'Management'),
    'rfid_cards':       ('RFID Cards',       'Management'),
    'tap_log':          ('Tap Log',          'Management'),
    'chargers':         ('Chargers',         'Management'),
    'sessions':         ('Sessions',         'Operations'),
    'active_sessions':  ('Active Sessions',  'Operations'),
    'session_report':   ('Session Report',   'Reports'),
    'revenue_report':   ('Revenue Report',   'Reports'),
    'tariffs':          ('Tariffs',          'Settings'),
    'billing_policy':   ('Billing Policy',   'Settings'),
    'users':            ('Users',            'Settings'),
}

# Maps a URL name to the page key it belongs to, so the decorator
# can figure out which permission to check for any given view.
URL_TO_PAGE = {
    'dashboard-home':    'dashboard',
    'customer-list':     'customers',
    'customer-create':   'customers',
    'customer-detail':   'customers',
    'customer-update':   'customers',
    'wallet-topup':      'customers',
    'wallet-ledger':     'customers',
    'card-list':         'rfid_cards',
    'card-create':       'rfid_cards',
    'card-detail':       'rfid_cards',
    'card-update':       'rfid_cards',
    'card-assign':       'rfid_cards',
    'card-block':        'rfid_cards',
    'card-unassign':     'rfid_cards',
    'rfid-tap-log':      'tap_log',
    'charger-list':      'chargers',
    'charger-create':    'chargers',
    'charger-detail':    'chargers',
    'charger-update':    'chargers',
    'charger-command':   'chargers',
    'charger-messages':  'chargers',
    'session-list':      'sessions',
    'session-detail':    'sessions',
    'session-remote-stop':  'sessions',
    'session-force-close':  'sessions',
    'session-reset-charger': 'sessions',
    'session-active':    'active_sessions',
    'report-sessions':   'session_report',
    'report-revenue':    'revenue_report',
    'tariff-list':       'tariffs',
    'tariff-create':     'tariffs',
    'tariff-update':     'tariffs',
    'tariff-activate':   'tariffs',
    'billing-policy':    'billing_policy',
    'user-list':         'users',
    'user-create':       'users',
    'user-detail':       'users',
    'user-update':       'users',
    'user-toggle-active': 'users',
    'user-permissions': 'users',
}


class User(AbstractBaseUser, PermissionsMixin):

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        STAFF = 'staff', 'Staff'

    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAFF)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    # Pages this user is allowed to access. Admins bypass this entirely.
    page_permissions = models.ManyToManyField(
        'PagePermission',
        blank=True,
        related_name='users',
        help_text='Pages this staff user can access. Admins have access to everything.',
    )

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['full_name']

    objects = UserManager()

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f'{self.full_name} ({self.phone_number})'

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    def has_page_access(self, page_key):
        """Check if this user can access a given page. Admins can access everything."""
        if self.is_admin:
            return True
        return self.page_permissions.filter(page_key=page_key).exists()

    def get_allowed_pages(self):
        """Return the set of page keys this user can access."""
        if self.is_admin:
            return set(PAGE_REGISTRY.keys())
        return set(self.page_permissions.values_list('page_key', flat=True))


class PagePermission(models.Model):
    """Represents a single page/section that can be granted to users."""

    page_key = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    section = models.CharField(max_length=50)

    class Meta:
        db_table = 'accounts_page_permission'
        ordering = ['section', 'display_name']

    def __str__(self):
        return f'{self.section} / {self.display_name}'
