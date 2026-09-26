from .formatting import normalize_label


def catalog_label(name: str) -> str:
    return normalize_label(name)
