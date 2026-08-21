# Agbomi Shop

Run locally with the included environment:

```bash
cp .env.example .env
source Ecom/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Serve the static frontend from the project root (for example, `python -m http.server 3000`) and open `http://127.0.0.1:3000`. Django serves the API on port 8000.

Core routes include `/auth/register/`, `/auth/login/`, `/auth/me/`, `/cart/`, `/addresses/`, `/checkout/quote/`, `/orders/create/`, and `/payments/paystack/webhook/`. The current login is email-only identification for this prototype; use email verification/magic links before production. Payment completion is webhook-only; configure Paystack keys in `.env` before using live payments. Add shipping rates and products through `/admin/`.

For production set a strong `DJANGO_SECRET_KEY`, set `DJANGO_DEBUG=false`, configure allowed hosts/CSRF origins, use HTTPS, a managed database, and production static/media storage.
