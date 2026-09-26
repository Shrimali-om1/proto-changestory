from .pricing import calculate_total


def checkout_total(price: float, tax_rate: float) -> float:
    return calculate_total(price, tax_rate)


def invoice_total(price: float, tax_rate: float) -> float:
    return calculate_total(price, tax_rate)
