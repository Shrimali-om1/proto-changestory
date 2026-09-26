from .pricing import calculate_total


def get_price_summary(price: float, tax_rate: float) -> dict[str, float]:
    """Small handler-shaped function for the API demo scenario."""
    return {"total": calculate_total(price, tax_rate)}
