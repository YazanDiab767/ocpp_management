from django.db import migrations


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


def seed_permissions(apps, schema_editor):
    PagePermission = apps.get_model('accounts', 'PagePermission')
    for key, (name, section) in PAGE_REGISTRY.items():
        PagePermission.objects.get_or_create(
            page_key=key,
            defaults={'display_name': name, 'section': section},
        )


def remove_permissions(apps, schema_editor):
    PagePermission = apps.get_model('accounts', 'PagePermission')
    PagePermission.objects.filter(page_key__in=PAGE_REGISTRY.keys()).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_add_page_permissions'),
    ]

    operations = [
        migrations.RunPython(seed_permissions, remove_permissions),
    ]
