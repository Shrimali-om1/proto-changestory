def normalize_label(value: str) -> str:
    return " ".join(value.strip().split()).title()
