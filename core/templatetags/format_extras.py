from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter(name='format_moeda')
def format_moeda(value, decimals=2):
    """Format number using space as thousands separator and comma as decimal separator.

    Examples:
        1234567.89 -> '1 234 567,89'
    """
    if value is None:
        return ''

    try:
        # Use Decimal for better formatting precision when possible
        num = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        try:
            num = Decimal(str(float(value)))
        except Exception:
            return ''

    # Ensure we have the required number of decimals
    try:
        decimals = int(decimals)
    except Exception:
        decimals = 2

    # Use Python's grouping with comma, then replace characters to get desired format
    q = f"{{0:,.{decimals}f}}".format(num)
    # q is like '1,234,567.89' — convert to '1 234 567,89'
    formatted = q.replace(',', 'X').replace('.', ',').replace('X', ' ')
    return formatted


@register.filter(name='format_num')
def format_num(value, decimals=2):
    """Alias for format_moeda (numbers without currency symbol)."""
    return format_moeda(value, decimals)
