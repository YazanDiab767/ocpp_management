from django.db import migrations


def seed_topup_report(apps, schema_editor):
    PagePermission = apps.get_model('accounts', 'PagePermission')
    perm, created = PagePermission.objects.get_or_create(
        page_key='topup_report',
        defaults={'display_name': 'Top-Up Report', 'section': 'Reports'},
    )
    # Grant to all existing users so nobody gets locked out
    User = apps.get_model('accounts', 'User')
    for user in User.objects.all():
        user.page_permissions.add(perm)


def remove_topup_report(apps, schema_editor):
    PagePermission = apps.get_model('accounts', 'PagePermission')
    PagePermission.objects.filter(page_key='topup_report').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_grant_existing_users_all_permissions'),
    ]

    operations = [
        migrations.RunPython(seed_topup_report, remove_topup_report),
    ]
