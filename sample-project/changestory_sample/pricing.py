def calculate_total(price: float, tax_rate: float) -> float:
    """Return a tax-inclusive price rounded for customer display."""
    return round(price + (price * tax_rate), 2)
