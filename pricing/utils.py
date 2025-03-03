from functools import lru_cache
from decimal import Decimal, ROUND_HALF_UP

@lru_cache(maxsize=128)
def format_category_id(category_id):
    """Cached category ID formatter"""
    if not category_id:
        return ''
    return str(category_id).split('.')[0]

@lru_cache(maxsize=128)
def format_price(price):
    """Cached price formatter"""
    if not price:
        return '₹ 0.00'
    return f'₹ {Decimal(str(price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP):,.2f}'

def clean_decimal_string(value):
    """Clean decimal strings from input"""
    if not value:
        return ''
    return str(value).strip().replace('₹', '').replace(',', '')
