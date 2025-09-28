from django.contrib import admin
from .models import Product, Order, OrderItem


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "price_cents", "currency", "active")
    list_filter = ("active", "currency")
    search_fields = ("name",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "total_cents", "currency", "email", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("email", "stripe_checkout_session_id")
    inlines = [OrderItemInline]
