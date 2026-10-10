"""A note's rich body, stored as a Quill Delta.

``content`` keeps the plain text (search, list previews, conflicts and old
backups rely on it) and ``format`` keeps the Delta as JSON. Plain notes store
``format=None`` and their Delta is rebuilt from ``content``.

Older builds stored ``format`` as a list with one style per line; those notes
are converted on the fly the first time they are opened.
"""

import json

# Families the editor offers; legacy per-line fonts map onto them.
LEGACY_FONTS = {
    "rounded": "Nunito",
    "serif": "Lora",
    "mono": "JetBrains Mono",
    "hand": "Caveat",
}
_LEGACY_BLOCKS = {
    "h1": {"header": 1},
    "h2": {"header": 2},
    "bullet": {"list": "bullet"},
    "number": {"list": "ordered"},
}
BLOCK_KEYS = {"header", "list", "blockquote", "code-block", "indent", "align"}


def _plain_delta(content: str) -> list[dict]:
    return [{"insert": f"{content}\n"}]


def _legacy_delta(content: str, styles: list) -> list[dict]:
    ops: list[dict] = []
    for index, text in enumerate(content.split("\n")):
        style = styles[index] if index < len(styles) else {}
        style = style if isinstance(style, dict) else {}
        inline = {}
        if style.get("b"):
            inline["bold"] = True
        if style.get("i"):
            inline["italic"] = True
        if style.get("u"):
            inline["underline"] = True
        if style.get("f") in LEGACY_FONTS:
            inline["font"] = LEGACY_FONTS[style["f"]]
        if text:
            ops.append({"insert": text, **({"attributes": inline} if inline else {})})
        kind = style.get("k")
        if kind == "check":
            block = {"list": "checked" if style.get("c") else "unchecked"}
        else:
            block = _LEGACY_BLOCKS.get(kind, {})
        ops.append({"insert": "\n", **({"attributes": block} if block else {})})
    return ops


def to_delta(content: str | None, fmt: str | None) -> list[dict]:
    """The Delta for a stored note, whatever version wrote it."""
    content = content or ""
    if not fmt:
        return _plain_delta(content)
    try:
        decoded = json.loads(fmt)
    except ValueError, TypeError:
        return _plain_delta(content)
    if isinstance(decoded, dict) and isinstance(decoded.get("delta"), list):
        return decoded["delta"]
    if isinstance(decoded, list):
        return _legacy_delta(content, decoded)
    return _plain_delta(content)


def plain_text(delta: list[dict]) -> str:
    text = "".join(op["insert"] for op in delta if isinstance(op.get("insert"), str))
    return text.removesuffix("\n")


def serialize(delta: list[dict]) -> tuple[str, str | None]:
    """``(content, format)`` to store; ``format`` is None when nothing is styled."""
    content = plain_text(delta)
    if not any(op.get("attributes") for op in delta):
        return content, None
    return content, json.dumps({"v": 2, "delta": delta}, separators=(",", ":"))


def lines(delta: list[dict]) -> list[tuple[str, dict]]:
    """Split a Delta into ``(text, block attributes)`` per line."""
    result = []
    current = ""
    for op in delta:
        insert = op.get("insert")
        if not isinstance(insert, str):
            continue
        attributes = op.get("attributes") or {}
        block = {k: v for k, v in attributes.items() if k in BLOCK_KEYS}
        parts = insert.split("\n")
        for part in parts[:-1]:
            result.append((current + part, block))
            current = ""
        current += parts[-1]
    if current:
        result.append((current, {}))
    return result


def preview(delta: list[dict]) -> str:
    """Text for the list card, keeping bullets, numbers and check boxes."""
    parts = []
    number = 0
    for text, block in lines(delta):
        kind = block.get("list")
        number = number + 1 if kind == "ordered" else 0
        if kind == "bullet":
            parts.append(f"• {text}")
        elif kind == "ordered":
            parts.append(f"{number}. {text}")
        elif kind == "checked":
            parts.append(f"☑ {text}")
        elif kind == "unchecked":
            parts.append(f"☐ {text}")
        else:
            parts.append(text)
    return "\n".join(parts)
