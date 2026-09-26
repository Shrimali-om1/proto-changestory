from changestory_sample.catalog import catalog_label
from changestory_sample.notifications import notification_label


def test_catalog_label() -> None:
    assert catalog_label("  summer   sale ") == "Summer Sale"


def test_notification_label() -> None:
    assert notification_label("summer sale") == "Order for Summer Sale"
