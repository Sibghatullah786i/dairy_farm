from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import RegexValidator


PAKISTANI_MOBILE_VALIDATOR = RegexValidator(
    r'^03\d{9}$',
    'Enter an 11-digit Pakistani mobile number.',
)


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, default='')
    locality = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=50, blank=True)
    mobile = models.CharField(
        max_length=11,
        blank=True,
        default='',
        validators=[PAKISTANI_MOBILE_VALIDATOR],
    )
    zipcode = models.CharField(
        max_length=5,
        blank=True,
        default='',
        validators=[RegexValidator(r'^\d{5}$', 'Enter a 5-digit postal code.')],
    )

    def __str__(self):
        return self.name or self.user.username


def get_customer_for_user(user):
    customer, _ = Customer.objects.get_or_create(
        user=user,
        defaults={'name': user.username},
    )
    return customer


@receiver(post_save, sender=User)
def create_or_update_customer_profile(sender, instance, created, **kwargs):
    if created:
        get_customer_for_user(instance)