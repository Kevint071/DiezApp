"""Human-readable byte sizes for the UI."""


def format_bytes(value) -> str:
    if value is None or value == "":
        return "Tamaño desconocido"
    try:
        size = int(value)
    except TypeError, ValueError:
        return "Tamaño desconocido"
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{max(1, size // 1024)} KB"
    return f"{size / (1024 * 1024):.1f} MB".replace(".", ",")


def total_bytes(files) -> int:
    total = 0
    for file in files:
        try:
            total += int(file.get("size") or 0)
        except TypeError, ValueError:
            continue
    return total
