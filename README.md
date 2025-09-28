# Django Stripe Store

A minimal Django app that sells 3 fixed products using Stripe Checkout (test mode) and stores paid orders. Built for a demo assignment.

## Features
- Django views + templates (Bootstrap) with a single public page
- 3 products seeded via migration
- Stripe Checkout Session flow (test mode)
- Order persistence and "My Orders" list
- Double-charge prevention via:
  - Idempotency key based on cart contents
  - Reuse of existing Checkout Session URL for resubmits
  - Verification of session status on success redirect
  - Optional Stripe webhook to mark paid
- Postgres via `DATABASE_URL` (fallback to SQLite for quick start)

## Why Stripe Checkout?
Stripe Checkout is simpler than directly orchestrating Payment Intents. It handles payment UI, card validation, SCA, and redirects back to the app. For this demo, Checkout reduces surface area and improves robustness.

## Assumptions
- No user auth; a per-session token identifies the "demo user"
- We use a single demo email address for Checkout (`DEMO_CUSTOMER_EMAIL`)
- Prices are hardcoded via migration and stored in cents

## Double-Charge Prevention
- We compute a deterministic idempotency key from the cart contents and session token.
- If an Order with the same key exists, we reuse the same Stripe Checkout Session (redirect to the stored session URL).
- On success redirect, we fetch the session from Stripe and mark the order as paid only if `payment_status == 'paid'`.
- A Stripe webhook endpoint (`/webhooks/stripe/`) is included. If you use Stripe CLI to forward events, it will also mark sessions paid redundantly, providing defense-in-depth.

## Tech Stack
- Django 4.2
- Stripe Python SDK
- Postgres via `dj-database-url` (with `psycopg2-binary`)
- `python-dotenv` for `.env`
- `whitenoise` for static files

## Setup
1. Clone and enter the project directory
2. Create and activate a virtual environment
3. Install dependencies
4. Copy `.env.example` to `.env` and set your values
5. Run migrations and start the server

### Commands (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

Then open http://127.0.0.1:8000/

### Environment Variables
- `STRIPE_SECRET_KEY` (required)
- `STRIPE_PUBLISHABLE_KEY` (required for client-side if used; not strictly necessary here but exposed for completeness)
- `STRIPE_WEBHOOK_SECRET` (optional, if using Stripe CLI forwarding)
- `DATABASE_URL` (Postgres recommended; falls back to SQLite if absent)
- `DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- `CURRENCY`, `DEMO_CUSTOMER_EMAIL`

### Postgres Example
```
DATABASE_URL=postgres://postgres:postgres@localhost:5432/stripe_store
```

## Using Stripe Test Mode
- Use test keys from your Stripe dashboard or Stripe CLI
- Test card: 4242 4242 4242 4242, any future expiry, any CVC

## Webhooks (Optional but Recommended)
To forward webhooks locally with Stripe CLI:
```bash
stripe listen --forward-to localhost:8000/webhooks/stripe/
```
Set `STRIPE_WEBHOOK_SECRET` from the listen command output.

## Repo Structure
- `config/` Django project settings and URLs
- `store/` App with models, views, admin, migrations
- `templates/` HTML templates
- `static/` static assets

## Notes
- If you refresh the success page or go back and re-submit, the app will reuse the existing Checkout Session (no duplicate charges)
- Admin is available at `/admin/` (create a superuser if needed).

## Time Spent
Approximately 10-12 hours including scaffolding, coding, and docs.

## What Works
- 3 products are displayed on the main page (seeded via migration).
- Quantities can be selected and a Stripe Checkout Session is created in test mode.
- After successful payment, the app verifies the session with Stripe and marks the order as paid.
- Paid orders appear under "My Orders" on the main page.
- Duplicate submissions/refreshes reuse the same Checkout Session URL to avoid double charges.
- Optional Stripe webhook endpoint supports additional confirmation when enabled via Stripe CLI.

## Submission
- To run locally, follow "Setup" and "Commands" above. Provide Stripe test keys in `.env`.
- What we expect to see:
  - Working Stripe test payment and a paid order visible on the main page
  - Clear assumptions and reasoning (see sections above)
  - Basic robustness against duplicates/refresh (idempotency + verification)
  - AI usage documented in `AI-assist.md`
