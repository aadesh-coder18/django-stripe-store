from django.contrib import admin
from django.urls import path
from store import views as store_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', store_views.index, name='index'),
    path('create-checkout-session/', store_views.create_checkout_session, name='create_checkout_session'),
    path('success/', store_views.checkout_success, name='success'),
    path('cancel/', store_views.checkout_cancel, name='cancel'),
    path('webhooks/stripe/', store_views.stripe_webhook, name='stripe_webhook'),
]
