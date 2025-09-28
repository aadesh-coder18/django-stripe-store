from __future__ import annotations

from django.db import models
from django.utils import timezone


class Product(models.Model):
    name = models.CharField(max_length=200)
    price_cents = models.PositiveIntegerField(help_text="Price in cents")
    currency = models.CharField(max_length=10, default="usd")
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.price_cents/100:.2f} {self.currency.upper()})"


class Order(models.Model):
    STATUS_CREATED = "created"
    STATUS_PAID = "paid"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = [
        (STATUS_CREATED, "Created"),
        (STATUS_PAID, "Paid"),
        (STATUS_CANCELED, "Canceled"),
    ]

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    customer_token = models.CharField(max_length=64, db_index=True)
    email = models.EmailField(blank=True, default="")
    total_cents = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=10, default="usd")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CREATED)
    stripe_checkout_session_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    checkout_url = models.URLField(max_length=500, blank=True, null=True)
    idempotency_key = models.CharField(max_length=200, blank=True, default="", db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order #{self.id} - {self.status} - {self.total_cents/100:.2f} {self.currency.upper()}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price_cents = models.PositiveIntegerField()

    @property
    def line_total_cents(self) -> int:
        return self.quantity * self.unit_price_cents

    def __str__(self) -> str:
        return f"{self.product.name} x {self.quantity}"
