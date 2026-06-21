from echoloop.add import add


def test_add() -> None:
    assert add(a=2, b=3) == 5
