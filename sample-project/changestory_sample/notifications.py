from .formatting import normalize_label


def notification_label(name: str) -> str:
    return f"Order for {normalize_label(name)}"
