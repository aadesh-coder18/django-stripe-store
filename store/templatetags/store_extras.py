from django import template

register = template.Library()


@register.filter()
def cents_to_money(value_cents, currency_symbol: str = "$"):
    try:
        cents = int(value_cents)
    except (TypeError, ValueError):
        return "-"
    dollars = cents / 100.0
    return f"{currency_symbol}{dollars:,.2f}"
