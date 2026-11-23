from toy import add, clamp, slugify


def test_add() -> None:
    assert add(2, 3) == 5


def test_clamp() -> None:
    assert clamp(9, 0, 5) == 5 and clamp(-1, 0, 5) == 0 and clamp(3, 0, 5) == 3


def test_slugify() -> None:
    assert slugify("Hello World  Again") == "hello-world-again"
