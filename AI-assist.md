I used AI (Cascade) as a light pair‑programming helper. I designed the solution and wrote the core models, views, and the payment flow myself. I leaned on AI in a few targeted spots to speed things up and sanity‑check details:

Generate some initial scaffolding/boilerplate (settings/urls structure).
Cross‑check Stripe Checkout usage patterns from the docs, which I adapted to this codebase (including idempotency and session‑reuse).
Tidy up templates and add a small “prevent double submit” JS snippet.
Polish documentation (README sections, .env.example) and Windows command tips.
Sanity‑check environment configuration and dependency pinning.