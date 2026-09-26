from changestory_sample.orders import checkout_total, invoice_total


def test_checkout_uses_pricing() -> None:
    assert checkout_total(50, 0.1) == 55


def test_invoice_uses_pricing() -> None:
    assert invoice_total(50, 0.2) == 60
