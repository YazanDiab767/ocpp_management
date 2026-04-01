from django.db import migrations


def grant_all(apps, schema_editor):
    """Give every existing user all page permissions so nobody gets locked out."""
    User = apps.get_model('accounts', 'User')
    PagePermission = apps.get_model('accounts', 'PagePermission')
    all_perms = PagePermission.objects.all()
    for user in User.objects.all():
        user.page_permissions.set(all_perms)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_seed_page_permissions'),
    ]

    operations = [
        migrations.RunPython(grant_all, migrations.RunPython.noop),
    ]
