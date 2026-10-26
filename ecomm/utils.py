from django.conf import settings


def get_client_ip(request):
    remote_addr = request.META.get('REMOTE_ADDR', 'unknown')
    if settings.SECURE_PROXY_SSL_HEADER:
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        forwarded_addresses = [
            address.strip()
            for address in forwarded_for.split(',')
            if address.strip()
        ]
        if forwarded_addresses:
            return forwarded_addresses[-1]
    return remote_addr
