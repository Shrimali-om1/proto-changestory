from changestory_sample.pricing import calculate_total


def test_calculate_total_includes_tax() -> None:
    assert calculate_total(100, 0.1) == 110
