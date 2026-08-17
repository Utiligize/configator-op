"""Test canary."""


def test_tautology():
    """This test always passes."""
    expected = 4
    actual = 2 + 2
    assert actual == expected
