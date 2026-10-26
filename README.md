# Almeer Dairy Products

A Django storefront for browsing dairy products, managing a shopping cart, and placing orders with cash on delivery or bank transfer.

## Requirements

- Python 3.12 or newer
- Dependencies pinned in `requirements.txt`

## Setup

From the project directory, create and activate a virtual environment, then install the dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Configure development settings before running Django. `DJANGO_DEBUG` must be
explicitly set to `true`; a local-only fallback secret is used if the secret
environment variable is omitted:

```powershell
$env:DJANGO_SECRET_KEY = "replace-with-a-long-random-secret"
$env:DJANGO_DEBUG = "true"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
Copy-Item .env.example .env
```

Development mode must be explicitly enabled; `DJANGO_DEBUG` defaults to
`false`. Copy `.env.example` to `.env` and set the values for your environment.
Email is sent through Django's SMTP backend in both development and production.
In production, keep `DJANGO_DEBUG=false`, set a strong `DJANGO_SECRET_KEY`,
configure `DJANGO_ALLOWED_HOSTS` and SMTP settings, and serve uploaded media
through your web server or storage service. WhiteNoise serves collected static
assets; run `python manage.py collectstatic --noinput` as part of deployment.

For Gmail, configure the SMTP values in `.env`:

```dotenv
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your-address@gmail.com
EMAIL_HOST_PASSWORD=your-16-character-app-password
DEFAULT_FROM_EMAIL=your-address@gmail.com
```

Use a [Google App Password](https://support.google.com/accounts/answer/185833)
for `EMAIL_HOST_PASSWORD`, not your Google account password. Enable 2-Step
Verification on the Google account, open **Google Account → Security → App
passwords**, create an app password, and copy it into `.env`. If the App
passwords option is unavailable, the account may not meet Google's eligibility
requirements. Never commit `.env`; it is ignored by Git.

For production HTTPS settings, configure `DJANGO_SECURE_HSTS_SECONDS` only
after HTTPS is configured:
```powershell
$env:DJANGO_SECURE_HSTS_SECONDS = "31536000"
# Set these only if every subdomain is HTTPS-only and you want HSTS preload.
$env:DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS = "true"
$env:DJANGO_SECURE_HSTS_PRELOAD = "true"
```

Only enable HSTS after HTTPS is configured for the entire site/domain; it is
cached by browsers and can be difficult to undo. Include subdomains or preload
only when every relevant subdomain is HTTPS-only and you intend to opt in.
Production redirects to HTTPS and marks session/CSRF cookies secure. If TLS
terminates at a trusted reverse proxy, set `DJANGO_TRUST_PROXY_SSL_HEADER=true`
only when that proxy overwrites the `X-Forwarded-Proto` header.

Apply database migrations and create an administrator account:

```powershell
python manage.py migrate
python manage.py seed_store
python manage.py createsuperuser
```

## Run locally

```powershell
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in a browser. The Django admin is available at <http://127.0.0.1:8000/admin/>.

## Payments

Checkout accepts cash on delivery and bank transfer. In development only, the
"Pay now (simulated)" option is available for demonstrations; it does not
process or collect real payments. Cash on delivery and bank transfer orders
remain pending until confirmed. Contact the store for bank-transfer instructions.

## Notes

- The local SQLite database is created as `db.sqlite3` and is ignored by Git.
- Product uploads are stored under `media/`; this directory is ignored by Git.
- `python manage.py seed_store` creates the starter categories and products and
  copies the bundled images from `products/seed_images/` into `media/`.
- Password reset uses a 6-digit email code that expires after five minutes;
  codes are single-use and limited to five incorrect attempts. Resending has a
  60-second cooldown, and reset requests are rate-limited per IP. Login
  attempts are limited per IP and username, and contact submissions are
  limited per IP. Configure a shared Django cache backend in multi-process or
  multi-host deployments so these limits are consistent across app workers.
  When using a trusted reverse proxy, set `DJANGO_TRUST_PROXY_SSL_HEADER=true`;
  the app then uses the rightmost address in `X-Forwarded-For` for these limits.
  Configure the proxy to append the connecting client address and do not expose
  the application directly to untrusted clients.
- Production startup requires `DJANGO_SECRET_KEY`, `EMAIL_HOST`,
  `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL`.
- Set `DJANGO_SECURE_HSTS_SECONDS` only after confirming HTTPS and subdomain
  coverage appropriate for your deployment; enable the include-subdomains and
  preload flags only when they are appropriate for your whole domain.
- Never commit `DJANGO_SECRET_KEY`; configure it through the deployment
  environment.
