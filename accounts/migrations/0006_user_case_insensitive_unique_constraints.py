from django.conf import settings
from django.db import migrations, models
from django.db.models import Count, Q
from django.db.models.functions import Lower


USERNAME_CONSTRAINT = models.UniqueConstraint(
    Lower('username'),
    name='accounts_user_username_ci_unique',
)
EMAIL_CONSTRAINT = models.UniqueConstraint(
    Lower('email'),
    condition=~Q(email=''),
    name='accounts_user_email_ci_unique',
)


def check_for_case_insensitive_duplicates(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    database = schema_editor.connection.alias
    duplicate_usernames = (
        User.objects.using(database)
        .annotate(normalized=Lower('username'))
        .values('normalized')
        .annotate(total=Count('pk'))
        .filter(total__gt=1)
        .exists()
    )
    duplicate_emails = (
        User.objects.using(database)
        .exclude(email='')
        .annotate(normalized=Lower('email'))
        .values('normalized')
        .annotate(total=Count('pk'))
        .filter(total__gt=1)
        .exists()
    )
    if duplicate_usernames or duplicate_emails:
        raise RuntimeError(
            'Cannot add case-insensitive user uniqueness constraints while '
            'duplicate usernames or email addresses exist. Resolve duplicates '
            'before retrying this migration.'
        )


def add_case_insensitive_constraints(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    schema_editor.add_constraint(User, USERNAME_CONSTRAINT)
    schema_editor.add_constraint(User, EMAIL_CONSTRAINT)


def remove_case_insensitive_constraints(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    schema_editor.remove_constraint(User, EMAIL_CONSTRAINT)
    schema_editor.remove_constraint(User, USERNAME_CONSTRAINT)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_create_missing_customer_profiles'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(
            check_for_case_insensitive_duplicates,
            migrations.RunPython.noop,
        ),
        migrations.RunPython(
            add_case_insensitive_constraints,
            remove_case_insensitive_constraints,
        ),
    ]
