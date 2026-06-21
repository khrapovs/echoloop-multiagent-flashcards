from echoloop.dummy import dummy


def test_dummy() -> None:
    assert dummy(a=2, b=3) == 5
