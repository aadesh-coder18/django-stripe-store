from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, List, Tuple

import stripe
import logging
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from .models import Order, OrderItem, Product

logger = logging.getLogger(__name__)

def _get_customer_token(request: HttpRequest) -> str:
    token = request.session.get("customer_token")
    if not token:
        # Simple per-session token; sufficient for demo without auth
        token = hashlib.sha256(os.urandom(32)).hexdigest()
        request.session["customer_token"] = token
    return token


def _build_cart_from_post(request: HttpRequest) -> List[Tuple[Product, int]]:
    items: List[Tuple[Product, int]] = []
    for product in Product.objects.filter(active=True).order_by("id"):
        qty_str = request.POST.get(f"qty_{product.id}", "0").strip()
        try:
            qty = int(qty_str)
        except ValueError:
            qty = 0
        if qty > 0:
            items.append((product, qty))
    return items


def _cart_idempotency_key(customer_token: str, items: List[Tuple[Product, int]]) -> str:
    payload = {
        "customer_token": customer_token,
        "items": [(p.id, q) for p, q in items],
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def index(request: HttpRequest) -> HttpResponse:
    customer_token = _get_customer_token(request)
    products = Product.objects.filter(active=True).order_by("id")
    orders = Order.objects.filter(customer_token=customer_token, status=Order.STATUS_PAID).prefetch_related("items", "items__product")
    context = {
        "products": products,
        "orders": orders,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, "store/index.html", context)


def create_checkout_session(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method")

    customer_token = _get_customer_token(request)
    items = _build_cart_from_post(request)
    if not items:
        return redirect("index")

    cart_key = _cart_idempotency_key(customer_token, items)

    # If a recent order exists with the same idempotency_key and not canceled, reuse its session
    existing = Order.objects.filter(idempotency_key=cart_key).exclude(status=Order.STATUS_CANCELED).order_by("-created_at").first()
    if existing and existing.stripe_checkout_session_id:
        # Reuse existing Checkout URL when available to prevent duplicate sessions
        if getattr(existing, "checkout_url", None):
            return redirect(existing.checkout_url)
        # Otherwise retrieve session to get URL (in case of reuse)
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            session = stripe.checkout.Session.retrieve(existing.stripe_checkout_session_id)
            # Cache URL for subsequent uses
            try:
                existing.checkout_url = session.url
                existing.save(update_fields=["checkout_url"]) 
            except Exception:
                pass
            return redirect(session.url)
        except Exception:
            pass  # Fallback to create a new session

    # Create order and items in DB (status created)
    order = Order.objects.create(
        customer_token=customer_token,
        email=settings.DEMO_CUSTOMER_EMAIL,
        currency=settings.CURRENCY,
        status=Order.STATUS_CREATED,
        idempotency_key=cart_key,
    )
    total_cents = 0
    for product, qty in items:
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=qty,
            unit_price_cents=product.price_cents,
        )
        total_cents += product.price_cents * qty
    order.total_cents = total_cents
    order.save(update_fields=["total_cents"])

    # Create Stripe Checkout Session
    stripe.api_key = settings.STRIPE_SECRET_KEY
    line_items: List[Dict] = []
    for product, qty in items:
        line_items.append({
            "price_data": {
                "currency": product.currency,
                "product_data": {"name": product.name},
                "unit_amount": product.price_cents,
            },
            "quantity": qty,
        })

    success_url = request.build_absolute_uri(reverse("success")) + "?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = request.build_absolute_uri(reverse("cancel")) + f"?order_id={order.id}"

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(order.id),
            customer_email=settings.DEMO_CUSTOMER_EMAIL,
            metadata={
                "order_id": str(order.id),
                "customer_token": customer_token,
            },
            idempotency_key=cart_key,
        )
    except Exception as e:
        # Log full details to console for debugging
        logger.exception("Error creating Stripe Checkout session for order %s", order.id)
        # In case of error, keep order as created; show simple error
        return HttpResponseBadRequest(f"Error creating checkout session: {e}")

    order.stripe_checkout_session_id = session.id
    try:
        order.checkout_url = session.url
        order.save(update_fields=["stripe_checkout_session_id", "checkout_url"]) 
    except Exception:
        order.save(update_fields=["stripe_checkout_session_id"]) 

    return redirect(session.url)


def checkout_success(request: HttpRequest) -> HttpResponse:
    session_id = request.GET.get("session_id")
    if not session_id:
        return redirect("index")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent", "customer_details"])
    except Exception:
        return redirect("index")

    # Verify and mark order paid
    order = Order.objects.filter(stripe_checkout_session_id=session.id).first()
    if not order and session.client_reference_id:
        order = Order.objects.filter(id=session.client_reference_id).first()

    if order and order.status != Order.STATUS_PAID and getattr(session, "payment_status", "") == "paid":
        email = getattr(session, "customer_details", {}).get("email") if isinstance(session.customer_details, dict) else None
        order.status = Order.STATUS_PAID
        if email:
            order.email = email
        order.save(update_fields=["status", "email", "updated_at"])

    return render(request, "store/success.html", {"session_id": session.id})


def checkout_cancel(request: HttpRequest) -> HttpResponse:
    order_id = request.GET.get("order_id")
    if order_id:
        try:
            order = Order.objects.get(id=order_id)
            if order.status == Order.STATUS_CREATED:
                order.status = Order.STATUS_CANCELED
                order.save(update_fields=["status", "updated_at"])
        except Order.DoesNotExist:
            pass
    return render(request, "store/cancel.html")


@csrf_exempt
def stripe_webhook(request: HttpRequest) -> HttpResponse:
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if webhook_secret:
        try:
            event = stripe.Webhook.construct_event(
                payload=payload, sig_header=sig_header, secret=webhook_secret
            )
        except Exception as e:
            return HttpResponse(status=400)
    else:
        try:
            event = json.loads(payload)
        except Exception:
            return HttpResponse(status=400)

    if event.get("type") == "checkout.session.completed":
        data = event.get("data", {}).get("object", {})
        session_id = data.get("id")
        client_reference_id = data.get("client_reference_id")
        email = data.get("customer_details", {}).get("email")
        try:
            order = None
            if session_id:
                order = Order.objects.filter(stripe_checkout_session_id=session_id).first()
            if not order and client_reference_id:
                order = Order.objects.filter(id=client_reference_id).first()
            if order and order.status != Order.STATUS_PAID:
                order.status = Order.STATUS_PAID
                if email:
                    order.email = email
                order.save(update_fields=["status", "email", "updated_at"])
        except Exception:
            pass

    return HttpResponse(status=200)
