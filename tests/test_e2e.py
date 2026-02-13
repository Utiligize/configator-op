"""Integration test for Configator load_config.

Relies on a real token and a properly set up 1Password item.
"""

from decimal import Decimal
from os import getenv

from pydantic import BaseModel
from pytest import approx, mark

from configator.core import load_config
from configator.models import SentryConfig

OP_TOKEN = getenv("OP_TOKEN")


@mark.skipif(OP_TOKEN is None, reason="no 1Password token provided")
@mark.asyncio
async def test_load_config():
    class ValuesConfig(BaseModel):
        a_string: str
        an_integer: int
        a_reference: str
        a_complex: complex
        a_decimal: Decimal
        a_float: float
        a_bool: bool
        another_bool: bool
        a_dict: dict
        a_list: list
        a_set: set
        a_tuple: tuple

    class E2ETestConfig(BaseModel):
        """Full end-to-end test configuration schema."""

        VALUES: ValuesConfig
        MIXIN: SentryConfig
        outside_sections: str = "overridden_default_value"
        not_set: str = "default_value"

    vault = "REPO configator"
    item = "configator-test-e2e"

    expected_config = E2ETestConfig(
        VALUES=ValuesConfig(
            a_string="foo",
            an_integer=42,
            a_reference="mixpanel",
            a_complex=complex(real=-1.23, imag=4.5),
            a_decimal=Decimal("0.1"),
            a_float=0.1,
            a_bool=True,
            another_bool=False,
            a_dict={"baz": "quux", "xyzzy": 42, "foo": "bar"},
            a_list=[1, 2, 3],
            a_set={"diamonds", "clubs", "hearts", "spades"},
            a_tuple=("hearts", "diamonds", "clubs", "spades", "hearts"),
        ),
        MIXIN=SentryConfig(dsn="https://this.url.is.invalid/"),
        outside_sections=(
            "This value is just a string but it could be anything. Just like you. "
            "Believe in yourself. Worry not what others think. Buy that extra chunk of cheese."
        ),
        not_set="default_value",
    )

    actual_config: E2ETestConfig = await load_config(
        schema=E2ETestConfig,
        token=OP_TOKEN,
        vault=vault,
        item=item,
    )

    assert actual_config == expected_config
    assert actual_config.MIXIN.traces_sample_rate == approx(0.0)
    assert isinstance(actual_config.VALUES.a_decimal, Decimal)
