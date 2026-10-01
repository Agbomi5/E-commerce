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

## Vercel deployment

Vercel's function filesystem is temporary. Configure these project environment variables in Vercel before deploying this Django app:

- `DATABASE_URL`: the connection URL for a persistent PostgreSQL database. The admin panel and storefront API must use the same database.
- `USE_CLOUDINARY=true`
- `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET`: credentials for a Cloudinary account used to store admin-uploaded product and category images.

Redeploy after setting the variables. The app deliberately refuses to start on Vercel without the persistent database and media-storage configuration rather than silently saving changes to temporary local files. Existing images stored only in the deployment's local `media/` directory must be uploaded to Cloudinary again.
