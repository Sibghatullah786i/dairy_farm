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

Configure the required application secret before running Django:

```powershell
$env:DJANGO_SECRET_KEY = "replace-with-a-long-random-secret"
$env:DJANGO_DEBUG = "true"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
```

`DJANGO_DEBUG` defaults to `true` for local development, which also enables
Django's development media server for product images. In production, set
`DJANGO_DEBUG=false`, configure `DJANGO_ALLOWED_HOSTS` to your production host
names, and serve uploaded media through your web server or storage service.

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

Checkout accepts cash on delivery and bank transfer. The "Pay now (simulated)"
option marks an order paid for demonstration only; it does not process or collect
real payments. Cash on delivery and bank transfer orders remain pending until
confirmed. Contact the store for bank-transfer instructions.

## Notes

- The local SQLite database is created as `db.sqlite3` and is ignored by Git.
- Product uploads are stored under `media/`; this directory is ignored by Git.
- `python manage.py seed_store` creates the starter categories and products using
  the bundled sample images.
- Never commit `DJANGO_SECRET_KEY`; configure it through the deployment
  environment.
