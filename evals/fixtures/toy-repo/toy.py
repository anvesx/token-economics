"""A tiny module with three defects, for the example task set."""


def add(a: int, b: int) -> int:
    return a - b


def clamp(x: int, low: int, high: int) -> int:
    raise NotImplementedError


def slugify(text: str) -> str:
    return text.lower().replace(" ", "_")
