from django.conf import settings
from django.db import migrations


def create_missing_customer_profiles(apps, schema_editor):
    Customer = apps.get_model('accounts', 'Customer')
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    database = schema_editor.connection.alias
    existing_user_ids = Customer.objects.using(database).values_list(
        'user_id',
        flat=True,
    )
    Customer.objects.using(database).bulk_create([
        Customer(user_id=user.pk, name=user.username)
        for user in User.objects.using(database).exclude(
            pk__in=existing_user_ids,
        ).iterator()
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_alter_customer_mobile_alter_customer_zipcode'),
    ]

    operations = [
        migrations.RunPython(
            create_missing_customer_profiles,
            migrations.RunPython.noop,
        ),
    ]
