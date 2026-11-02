import smtplib

from celery import shared_task
from django.core.mail import send_mail


def send_reset_otp_email(email, otp):
    send_mail(
        'Your password reset verification code',
        (
            f'Your password reset verification code is {otp}.\n\n'
            'This code expires in 5 minutes. If you did not request a '
            'password reset, you can ignore this email.'
        ),
        None,
        [email],
        fail_silently=False,
    )


@shared_task(
    autoretry_for=(smtplib.SMTPException, OSError),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    ignore_result=True,
)
def send_reset_otp_task(email, otp):
    send_reset_otp_email(email, otp)
