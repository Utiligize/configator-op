"""Unit tests for Configator core functionality."""

from typing import Any
from unittest.mock import AsyncMock, patch

from onepassword.errors import RateLimitExceededException
from onepassword.types import (
    Item,
    ItemField,
    ItemOverview,
    ItemSection,
    ResolveAllResponse,
    ResolvedReference,
    ResolveReferenceError,
    ResolveReferenceErrorVaultNotFound,
    Response,
    VaultOverview,
)

try:
    from onepassword.types import VaultType
except ImportError:
    # onepassword-sdk<0.4
    VaultType = None
import pytest
import stamina
from pydantic import BaseModel

from configator.core import (
    _MAX_REFERENCE_DEPTH,
    _RETRY_ATTEMPTS,
    _field_matcher,
    _get_client,
    _get_item,
    _get_item_overview,
    _get_sections,
    _get_vault_overview,
    _hydrate_model,
    _is_transient,
    _op_field_name_to_lower_snake_case,
    _parse_bool,
    _resolve_references,
    load_config,
)


@pytest.fixture(autouse=True)
def _instant_retries():
    """Keep the retry attempt count but drop the backoff waits."""
    with stamina.set_testing(True, attempts=_RETRY_ATTEMPTS):
        yield


# Test schemas
class SimpleConfig(BaseModel):
    """Simple configuration schema."""

    field_one: str
    field_two: int


class SectionConfig(BaseModel):
    """Section configuration schema."""

    debug: bool
    timeout: int


class GenericConfig(BaseModel):
    """Schema with a parameterized generic field."""

    price_areas: list[str]


class ComplexConfig(BaseModel):
    """Complex configuration schema with nested sections."""

    simple_field: str
    section: SectionConfig
    optional_field: str = "default_value"


# Fixtures
@pytest.fixture
def mock_vault():
    """Mock VaultOverview."""
    kwargs: dict[str, Any] = {"id": "vault123", "title": "TestVault"}
    if VaultType is not None:
        kwargs.update(
            description="",
            vaultType=VaultType.USERCREATED,
            activeItemCount=0,
            contentVersion=1,
            attributeVersion=1,
            createdAt="2024-01-01T00:00:00Z",
            updatedAt="2024-01-01T00:00:00Z",
        )
    # pyrefly: ignore[missing-argument]  # extra fields only exist on onepassword-sdk>=0.4
    return VaultOverview(**kwargs)


@pytest.fixture
def mock_item_overview():
    """Mock ItemOverview."""
    return ItemOverview(
        id="item456",
        title="TestItem",
        vaultId="vault123",
        category="Login",
        websites=[],
        tags=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
        state="active",
    )


@pytest.fixture
def mock_item_field():
    """Mock ItemField."""
    return ItemField(
        id="field1",
        title="Field-One",
        fieldType="Text",
        value="test_value",
        sectionId=None,
    )


@pytest.fixture
def mock_item_section():
    """Mock ItemSection."""
    return ItemSection(id="section1", title="Section")


@pytest.fixture
def mock_item():
    """Mock Item with fields and sections."""
    return Item(
        id="item456",
        title="TestItem",
        vaultId="vault123",
        category="Login",
        fields=[
            ItemField(
                id="f1",
                title="simple-field",
                fieldType="Text",
                value="simple_value",
                sectionId=None,
            ),
            ItemField(
                id="f2", title="debug", fieldType="Text", value="true", sectionId="section1"
            ),
            ItemField(
                id="f3", title="timeout", fieldType="Text", value="30", sectionId="section1"
            ),
        ],
        sections=[ItemSection(id="section1", title="Section")],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )


@pytest.fixture
def mock_op_client():
    """Mock 1Password client."""
    client = AsyncMock()
    client.items = AsyncMock()
    client.vaults = AsyncMock()
    client.secrets = AsyncMock()
    return client


# Tests for _field_matcher
def test_field_matcher_title_match(mock_item_field):
    """Test field matcher with matching title."""
    assert _field_matcher(mock_item_field, title="field_one") is True


def test_field_matcher_title_no_match(mock_item_field):
    """Test field matcher with non-matching title."""
    assert _field_matcher(mock_item_field, title="other_field") is False


def test_field_matcher_with_section_id():
    """Test field matcher with section ID."""
    field = ItemField(id="f1", title="test", fieldType="Text", value="val", sectionId="sec1")
    assert _field_matcher(field, title="test", section_id="sec1") is True
    assert _field_matcher(field, title="test", section_id="sec2") is False


def test_field_matcher_normalizes_field_name():
    """Test field matcher normalizes field names."""
    field = ItemField(id="f1", title="Field-Name", fieldType="Text", value="val", sectionId=None)
    assert _field_matcher(field, title="field_name") is True


# Tests for _get_client
@pytest.mark.asyncio
async def test_get_client():
    """Test client initialization."""
    with patch("configator.core.OnePasswordClient.authenticate") as mock_auth:
        mock_auth.return_value = AsyncMock()
        client = await _get_client("test_token")
        assert client is not None
        mock_auth.assert_called_once()
        call_args = mock_auth.call_args
        assert call_args.kwargs["auth"] == "test_token"
        assert "integration_name" in call_args.kwargs
        assert "integration_version" in call_args.kwargs


# Tests for _get_vault_overview
@pytest.mark.asyncio
async def test_get_vault_overview_found(mock_op_client, mock_vault):
    """Test retrieving existing vault."""
    mock_op_client.vaults.list.return_value = [mock_vault]
    result = await _get_vault_overview(mock_op_client, "TestVault")
    assert result == mock_vault


@pytest.mark.asyncio
async def test_get_vault_overview_not_found(mock_op_client, mock_vault):
    """Test retrieving non-existing vault."""
    mock_op_client.vaults.list.return_value = [mock_vault]
    result = await _get_vault_overview(mock_op_client, "NonExistentVault")
    assert result is None


@pytest.mark.asyncio
async def test_get_vault_overview_empty_list(mock_op_client):
    """Test retrieving vault from empty vault list."""
    mock_op_client.vaults.list.return_value = []
    result = await _get_vault_overview(mock_op_client, "TestVault")
    assert result is None


# Tests for _get_item_overview
@pytest.mark.asyncio
async def test_get_item_overview_found(mock_op_client, mock_item_overview):
    """Test retrieving existing item."""
    mock_op_client.items.list.return_value = [mock_item_overview]
    result = await _get_item_overview(mock_op_client, "vault123", "TestItem")
    assert result == mock_item_overview


@pytest.mark.asyncio
async def test_get_item_overview_not_found(mock_op_client, mock_item_overview):
    """Test retrieving non-existing item."""
    mock_op_client.items.list.return_value = [mock_item_overview]
    result = await _get_item_overview(mock_op_client, "vault123", "NonExistentItem")
    assert result is None


@pytest.mark.asyncio
async def test_get_item_overview_empty_list(mock_op_client):
    """Test retrieving item from empty item list."""
    mock_op_client.items.list.return_value = []
    result = await _get_item_overview(mock_op_client, "vault123", "TestItem")
    assert result is None


# Tests for retry behavior
def test_is_transient_rate_limit():
    """Test that a rate-limit error is terminal."""
    assert _is_transient(RateLimitExceededException("Too many requests")) is False


def test_is_transient_other_error():
    """Test that any other error is retried."""
    assert _is_transient(Exception("connection reset")) is True


@pytest.mark.asyncio
async def test_get_client_rate_limit_is_not_retried():
    """Test that a rate-limited authentication costs exactly one request."""
    with patch("configator.core.OnePasswordClient.authenticate") as mock_auth:
        mock_auth.side_effect = RateLimitExceededException("Too many requests")

        with pytest.raises(RateLimitExceededException):
            await _get_client("test_token")

        assert mock_auth.call_count == 1


@pytest.mark.asyncio
async def test_get_vault_overview_retries_transient_error(mock_op_client, mock_vault):
    """Test that a transient vault listing failure is retried."""
    mock_op_client.vaults.list.side_effect = [Exception("connection reset"), [mock_vault]]

    result = await _get_vault_overview(mock_op_client, "TestVault")

    assert result == mock_vault
    assert mock_op_client.vaults.list.await_count == 2


@pytest.mark.asyncio
async def test_get_vault_overview_rate_limit_is_not_retried(mock_op_client):
    """Test that a rate-limited vault listing costs exactly one request."""
    mock_op_client.vaults.list.side_effect = RateLimitExceededException("Too many requests")

    with pytest.raises(RateLimitExceededException):
        await _get_vault_overview(mock_op_client, "TestVault")

    assert mock_op_client.vaults.list.await_count == 1


@pytest.mark.asyncio
async def test_get_item_overview_retries_transient_error(mock_op_client, mock_item_overview):
    """Test that a transient item listing failure is retried."""
    mock_op_client.items.list.side_effect = [Exception("connection reset"), [mock_item_overview]]

    result = await _get_item_overview(mock_op_client, "vault123", "TestItem")

    assert result == mock_item_overview
    assert mock_op_client.items.list.await_count == 2


@pytest.mark.asyncio
async def test_get_item_overview_rate_limit_is_not_retried(mock_op_client):
    """Test that a rate-limited item listing costs exactly one request."""
    mock_op_client.items.list.side_effect = RateLimitExceededException("Too many requests")

    with pytest.raises(RateLimitExceededException):
        await _get_item_overview(mock_op_client, "vault123", "TestItem")

    assert mock_op_client.items.list.await_count == 1


@pytest.mark.asyncio
async def test_get_item_retries_transient_error(mock_op_client, mock_item):
    """Test that a transient item retrieval failure is retried."""
    mock_op_client.items.get.side_effect = [Exception("connection reset"), mock_item]

    result = await _get_item(mock_op_client, "vault123", "item456")

    assert result == mock_item
    assert mock_op_client.items.get.await_count == 2


@pytest.mark.asyncio
async def test_get_item_rate_limit_is_not_retried(mock_op_client):
    """Test that a rate-limited item retrieval costs exactly one request."""
    mock_op_client.items.get.side_effect = RateLimitExceededException("Too many requests")

    with pytest.raises(RateLimitExceededException):
        await _get_item(mock_op_client, "vault123", "item456")

    assert mock_op_client.items.get.await_count == 1


# Tests for _get_sections
def test_get_sections():
    """Test extracting section mapping from item."""
    item = Item(
        id="item1",
        title="Test",
        vaultId="vault1",
        category="Login",
        fields=[],
        sections=[
            ItemSection(id="sec1", title="Section One"),
            ItemSection(id="sec2", title="Section Two"),
        ],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )
    sections = _get_sections(item)
    assert sections == {"section one": "sec1", "section two": "sec2"}


def test_get_sections_empty():
    """Test extracting sections from item with no sections."""
    item = Item(
        id="item1",
        title="Test",
        vaultId="vault1",
        category="Login",
        fields=[],
        sections=[],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )
    sections = _get_sections(item)
    assert sections == {}


def test_get_sections_with_none_title():
    """Test extracting sections when some sections might be filtered."""
    item = Item(
        id="item1",
        title="Test",
        vaultId="vault1",
        category="Login",
        fields=[],
        sections=[
            ItemSection(id="sec1", title="Section One"),
            ItemSection(id="sec2", title=""),
        ],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )
    sections = _get_sections(item)
    # Empty string title is falsy, so it's filtered out
    assert sections == {"section one": "sec1"}


# Tests for _op_field_name_to_lower_snake_case
def test_op_field_name_to_lower_snake_case():
    """Test field name normalization."""
    assert _op_field_name_to_lower_snake_case("Field-Name") == "field_name"
    assert _op_field_name_to_lower_snake_case("Simple") == "simple"
    assert _op_field_name_to_lower_snake_case("Multi-Word-Field") == "multi_word_field"
    assert _op_field_name_to_lower_snake_case("UPPERCASE") == "uppercase"


# Tests for _parse_bool
def test_parse_bool_truthy_values():
    """Test parsing truthy boolean values."""
    assert _parse_bool("true") is True
    assert _parse_bool("True") is True
    assert _parse_bool("TRUE") is True
    assert _parse_bool("1") is True
    assert _parse_bool("yes") is True
    assert _parse_bool("YES") is True
    assert _parse_bool("on") is True
    assert _parse_bool("ON") is True
    assert _parse_bool(" true ") is True


def test_parse_bool_falsy_values():
    """Test parsing falsy boolean values."""
    assert _parse_bool("false") is False
    assert _parse_bool("False") is False
    assert _parse_bool("FALSE") is False
    assert _parse_bool("0") is False
    assert _parse_bool("no") is False
    assert _parse_bool("NO") is False
    assert _parse_bool("off") is False
    assert _parse_bool("OFF") is False
    assert _parse_bool(" false ") is False


def test_parse_bool_invalid_value():
    """Test parsing invalid boolean value raises ValueError."""
    with pytest.raises(ValueError, match="cannot parse 'invalid' as boolean"):
        _parse_bool("invalid")


def _echo_resolve_all(references: list[str]) -> ResolveAllResponse:
    """Resolve every reference to a plain value, so resolution always terminates."""
    return _resolve_all_response(
        {reference: reference.rsplit("/", 1)[-1] for reference in references}
    )


# Tests for _resolve_references
def _item_with_values(*values: str) -> Item:
    """Build an Item whose fields carry the given values."""
    return Item(
        id="item1",
        title="Test",
        vaultId="vault1",
        category="Login",
        fields=[
            ItemField(
                id=f"f{n}", title=f"field-{n}", fieldType="Text", value=value, sectionId=None
            )
            for n, value in enumerate(values)
        ],
        sections=[],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )


def _resolve_all_response(secrets: dict[str, str]) -> ResolveAllResponse:
    """Build a ResolveAllResponse resolving each reference to the given secret."""
    return ResolveAllResponse(
        individualResponses={
            reference: Response[ResolvedReference, ResolveReferenceError](
                content=ResolvedReference(secret=secret, itemId="item1", vaultId="vault1")
            )
            for reference, secret in secrets.items()
        }
    )


def _resolve_all_error(reference: str) -> ResolveAllResponse:
    """Build a ResolveAllResponse where the given reference failed to resolve."""
    return ResolveAllResponse(
        individualResponses={
            reference: Response[ResolvedReference, ResolveReferenceError](
                error=ResolveReferenceErrorVaultNotFound()
            )
        }
    )


@pytest.mark.asyncio
async def test_resolve_references_no_links(mock_op_client):
    """Test that an item without op:// values costs no requests."""
    resolved, requests = await _resolve_references(mock_op_client, _item_with_values("plain"))
    assert resolved == {}
    assert requests == 0
    mock_op_client.secrets.resolve_all.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_references_single_request_for_many_links(mock_op_client):
    """Test that every reference in the item is resolved in one batched request."""
    references = [f"op://vault/item/field{n}" for n in range(50)]
    mock_op_client.secrets.resolve_all.return_value = _resolve_all_response(
        {reference: f"secret-{reference}" for reference in references}
    )

    resolved, requests = await _resolve_references(mock_op_client, _item_with_values(*references))

    assert requests == 1
    assert resolved == {reference: f"secret-{reference}" for reference in references}
    mock_op_client.secrets.resolve_all.assert_awaited_once_with(sorted(references))


@pytest.mark.asyncio
async def test_resolve_references_deduplicates(mock_op_client):
    """Test that a reference repeated across fields is resolved once."""
    mock_op_client.secrets.resolve_all.return_value = _resolve_all_response(
        {"op://vault/item/field": "secret"}
    )

    resolved, requests = await _resolve_references(
        mock_op_client, _item_with_values("op://vault/item/field", "op://vault/item/field")
    )

    assert requests == 1
    assert resolved == {"op://vault/item/field": "secret"}
    mock_op_client.secrets.resolve_all.assert_awaited_once_with(["op://vault/item/field"])


@pytest.mark.asyncio
async def test_resolve_references_chained_links(mock_op_client):
    """Test that a reference pointing at another reference is followed."""
    mock_op_client.secrets.resolve_all.side_effect = [
        _resolve_all_response({"op://vault1/item1/field1": "op://vault2/item2/field2"}),
        _resolve_all_response({"op://vault2/item2/field2": "final_value"}),
    ]

    resolved, requests = await _resolve_references(
        mock_op_client, _item_with_values("op://vault1/item1/field1")
    )

    assert resolved == {"op://vault1/item1/field1": "final_value"}
    assert requests == 2


@pytest.mark.asyncio
async def test_resolve_references_resolution_error(mock_op_client):
    """Test that a failed reference is reported with its own name."""
    mock_op_client.secrets.resolve_all.return_value = _resolve_all_error("op://vault/item/field")
    item = _item_with_values("op://vault/item/field")

    with pytest.raises(
        RuntimeError, match="failed to resolve secret reference 'op://vault/item/field'"
    ):
        await _resolve_references(mock_op_client, item)


@pytest.mark.asyncio
async def test_resolve_references_request_error(mock_op_client):
    """Test that a batch request failing every attempt is reported as a RuntimeError."""
    mock_op_client.secrets.resolve_all.side_effect = Exception("connection reset")
    item = _item_with_values("op://vault/item/field")

    with pytest.raises(RuntimeError, match="failed to resolve 1 secret reference"):
        await _resolve_references(mock_op_client, item)

    assert mock_op_client.secrets.resolve_all.await_count == _RETRY_ATTEMPTS


@pytest.mark.asyncio
async def test_resolve_references_retries_transient_error(mock_op_client):
    """Test that a transient batch failure is retried and the load completes."""
    mock_op_client.secrets.resolve_all.side_effect = [
        Exception("connection reset"),
        _resolve_all_response({"op://vault/item/field": "secret"}),
    ]

    resolved, requests = await _resolve_references(
        mock_op_client, _item_with_values("op://vault/item/field")
    )

    assert resolved == {"op://vault/item/field": "secret"}
    assert requests == 1
    assert mock_op_client.secrets.resolve_all.await_count == 2


@pytest.mark.asyncio
async def test_resolve_references_rate_limit_is_not_retried(mock_op_client):
    """Test that a rate-limited batch request costs exactly one request."""
    mock_op_client.secrets.resolve_all.side_effect = RateLimitExceededException(
        "Too many requests. Your client has been rate-limited. Try again in  seconds"
    )
    item = _item_with_values("op://vault/item/field")

    with pytest.raises(RuntimeError, match="failed to resolve 1 secret reference"):
        await _resolve_references(mock_op_client, item)

    assert mock_op_client.secrets.resolve_all.await_count == 1


@pytest.mark.asyncio
async def test_resolve_references_at_max_depth(mock_op_client):
    """Test that a chain exactly at the documented depth of 10 links resolves."""
    chain = [f"op://vault/item/field{n}" for n in range(_MAX_REFERENCE_DEPTH)]
    mock_op_client.secrets.resolve_all.side_effect = [
        _resolve_all_response({link: next_link})
        for link, next_link in zip(chain, [*chain[1:], "final_value"], strict=True)
    ]

    resolved, requests = await _resolve_references(mock_op_client, _item_with_values(chain[0]))

    assert resolved == {chain[0]: "final_value"}
    assert requests == _MAX_REFERENCE_DEPTH


@pytest.mark.asyncio
async def test_resolve_references_too_deep(mock_op_client):
    """Test that an endless reference chain raises RuntimeError."""
    mock_op_client.secrets.resolve_all.return_value = _resolve_all_response(
        {"op://vault/item/field": "op://vault/item/field"}
    )
    item = _item_with_values("op://vault/item/field")

    with pytest.raises(RuntimeError, match="the dwarves delved too greedily and too deep"):
        await _resolve_references(mock_op_client, item)

    assert mock_op_client.secrets.resolve_all.await_count == _MAX_REFERENCE_DEPTH


@pytest.mark.asyncio
async def test_resolve_references_missing_from_response(mock_op_client):
    """Test that a reference absent from the response is reported, not retried."""
    mock_op_client.secrets.resolve_all.return_value = _resolve_all_response(
        {"op://vault/item/present": "secret"}
    )
    item = _item_with_values("op://vault/item/present", "op://vault/item/absent")

    match = "1Password returned no result for secret reference"
    with pytest.raises(RuntimeError, match=match):
        await _resolve_references(mock_op_client, item)

    assert mock_op_client.secrets.resolve_all.await_count == 1


# Tests for _hydrate_model
def test_hydrate_model_parameterized_generic():
    """Test hydrating model with a parameterized generic field (e.g. list[str])."""
    item = Item(
        id="item1",
        title="Test",
        vaultId="vault1",
        category="Login",
        fields=[
            ItemField(
                id="f1",
                title="price-areas",
                fieldType="Text",
                value='["DK1", "DK2"]',
                sectionId=None,
            ),
        ],
        sections=[],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )
    result = _hydrate_model(resolved={}, schema=GenericConfig, item=item)
    assert result.price_areas == ["DK1", "DK2"]


def test_hydrate_model_simple():
    """Test hydrating simple model."""
    item = Item(
        id="item1",
        title="Test",
        vaultId="vault1",
        category="Login",
        fields=[
            ItemField(
                id="f1",
                title="field-one",
                fieldType="Text",
                value="test",
                sectionId=None,
            ),
            ItemField(id="f2", title="field-two", fieldType="Text", value="42", sectionId=None),
        ],
        sections=[],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )
    result = _hydrate_model(resolved={}, schema=SimpleConfig, item=item)
    assert result.field_one == "test"
    assert result.field_two == 42


def test_hydrate_model_with_bool():
    """Test hydrating model with boolean field."""
    item = Item(
        id="item1",
        title="Test",
        vaultId="vault1",
        category="Login",
        fields=[
            ItemField(id="f1", title="debug", fieldType="Text", value="true", sectionId="sec1"),
            ItemField(id="f2", title="timeout", fieldType="Text", value="30", sectionId="sec1"),
        ],
        sections=[ItemSection(id="sec1", title="Section")],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )
    result = _hydrate_model(resolved={}, schema=SectionConfig, item=item, section_id="sec1")
    assert result.debug is True
    assert result.timeout == 30


def test_hydrate_model_with_default_value():
    """Test hydrating model with default value when field missing."""
    item = Item(
        id="item1",
        title="Test",
        vaultId="vault1",
        category="Login",
        fields=[
            ItemField(
                id="f1",
                title="simple-field",
                fieldType="Text",
                value="value",
                sectionId=None,
            ),
            ItemField(id="f2", title="debug", fieldType="Text", value="false", sectionId="sec1"),
            ItemField(id="f3", title="timeout", fieldType="Text", value="60", sectionId="sec1"),
        ],
        sections=[ItemSection(id="sec1", title="Section")],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )
    result = _hydrate_model(resolved={}, schema=ComplexConfig, item=item)
    assert result.simple_field == "value"
    assert result.section.debug is False
    assert result.section.timeout == 60
    assert result.optional_field == "default_value"


def test_hydrate_model_missing_required_field():
    """Test hydrating model with missing required field raises RuntimeError."""
    item = Item(
        id="item1",
        title="Test",
        vaultId="vault1",
        category="Login",
        fields=[
            ItemField(
                id="f1",
                title="field-one",
                fieldType="Text",
                value="test",
                sectionId=None,
            )
        ],
        sections=[],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )
    match = "field 'field_two' not found and no default value provided"
    with pytest.raises(RuntimeError, match=match):
        _hydrate_model(resolved={}, schema=SimpleConfig, item=item)


def test_hydrate_model_with_op_link():
    """Test hydrating model with op:// reference."""
    item = Item(
        id="item1",
        title="Test",
        vaultId="vault1",
        category="Login",
        fields=[
            ItemField(
                id="f1",
                title="field-one",
                fieldType="Text",
                value="op://vault/item/field",
                sectionId=None,
            ),
            ItemField(id="f2", title="field-two", fieldType="Text", value="42", sectionId=None),
        ],
        sections=[],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )
    result = _hydrate_model(
        resolved={"op://vault/item/field": "resolved_value"},
        schema=SimpleConfig,
        item=item,
    )
    assert result.field_one == "resolved_value"
    assert result.field_two == 42


def test_hydrate_model_nested_sections():
    """Test hydrating model with nested sections."""
    item = Item(
        id="item1",
        title="Test",
        vaultId="vault1",
        category="Login",
        fields=[
            ItemField(
                id="f1", title="simple-field", fieldType="Text", value="test", sectionId=None
            ),
            ItemField(id="f2", title="debug", fieldType="Text", value="yes", sectionId="sec1"),
            ItemField(id="f3", title="timeout", fieldType="Text", value="100", sectionId="sec1"),
        ],
        sections=[ItemSection(id="sec1", title="Section")],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )
    result = _hydrate_model(resolved={}, schema=ComplexConfig, item=item)
    assert result.simple_field == "test"
    assert isinstance(result.section, SectionConfig)
    assert result.section.debug is True
    assert result.section.timeout == 100


# Tests for load_config
@pytest.mark.asyncio
async def test_load_config_success(mock_op_client, mock_vault, mock_item_overview):
    """Test successful config loading."""
    item = Item(
        id="item456",
        title="TestItem",
        vaultId="vault123",
        category="Login",
        fields=[
            ItemField(
                id="f1",
                title="field-one",
                fieldType="Text",
                value="test_value",
                sectionId=None,
            ),
            ItemField(id="f2", title="field-two", fieldType="Text", value="123", sectionId=None),
        ],
        sections=[],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )

    with patch("configator.core._get_client", return_value=mock_op_client):
        mock_op_client.vaults.list.return_value = [mock_vault]
        mock_op_client.items.list.return_value = [mock_item_overview]
        mock_op_client.items.get.return_value = item
        mock_op_client.secrets.resolve_all.side_effect = _echo_resolve_all

        result = await load_config(
            token="test_token", vault="TestVault", item="TestItem", schema=SimpleConfig
        )

        assert isinstance(result, SimpleConfig)
        assert result.field_one == "test_value"
        assert result.field_two == 123


@pytest.mark.asyncio
async def test_load_config_request_count_is_bounded(
    mock_op_client, mock_vault, mock_item_overview
):
    """Test that a schema of many referencing fields costs a bounded number of requests."""
    references = [f"op://vault/item/secret{n}" for n in range(50)]
    item = Item(
        id="item456",
        title="TestItem",
        vaultId="vault123",
        category="Login",
        fields=[
            ItemField(
                id="f1",
                title="field-one",
                fieldType="Text",
                value="op://vault/item/secret0",
                sectionId=None,
            ),
            ItemField(
                id="f2",
                title="field-two",
                fieldType="Text",
                value="op://vault/item/secret1",
                sectionId=None,
            ),
            *[
                ItemField(
                    id=f"x{n}",
                    title=f"unused-{n}",
                    fieldType="Text",
                    value=reference,
                    sectionId=None,
                )
                for n, reference in enumerate(references[2:], start=2)
            ],
        ],
        sections=[],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )

    with patch("configator.core._get_client", return_value=mock_op_client):
        mock_op_client.vaults.list.return_value = [mock_vault]
        mock_op_client.items.list.return_value = [mock_item_overview]
        mock_op_client.items.get.return_value = item
        mock_op_client.secrets.resolve_all.return_value = _resolve_all_response(
            {"op://vault/item/secret0": "first"} | dict.fromkeys(references[1:], "42")
        )

        result = await load_config(
            token="test_token", vault="TestVault", item="TestItem", schema=SimpleConfig
        )

    assert result.field_one == "first"
    assert result.field_two == 42
    assert mock_op_client.secrets.resolve_all.await_count == 1


@pytest.mark.asyncio
async def test_load_config_vault_not_found(mock_op_client):
    """Test config loading with non-existent vault."""
    with patch("configator.core._get_client", return_value=mock_op_client):
        mock_op_client.vaults.list.return_value = []

        with pytest.raises(RuntimeError, match="vault 'NonExistentVault' not found"):
            await load_config(
                token="test_token",
                vault="NonExistentVault",
                item="TestItem",
                schema=SimpleConfig,
            )


@pytest.mark.asyncio
async def test_load_config_item_not_found(mock_op_client, mock_vault):
    """Test config loading with non-existent item."""
    with patch("configator.core._get_client", return_value=mock_op_client):
        mock_op_client.vaults.list.return_value = [mock_vault]
        mock_op_client.items.list.return_value = []

        match = "item 'NonExistentItem' not found in vault TestVault"
        with pytest.raises(RuntimeError, match=match):
            await load_config(
                token="test_token",
                vault="TestVault",
                item="NonExistentItem",
                schema=SimpleConfig,
            )


@pytest.fixture
def complex_item():
    """Mock Item with fields for ComplexConfig."""
    return Item(
        id="item456",
        title="TestItem",
        vaultId="vault123",
        category="Login",
        fields=[
            ItemField(
                id="f1",
                title="simple-field",
                fieldType="Text",
                value="simple",
                sectionId=None,
            ),
            ItemField(id="f2", title="debug", fieldType="Text", value="on", sectionId="sec1"),
            ItemField(id="f3", title="timeout", fieldType="Text", value="200", sectionId="sec1"),
            ItemField(
                id="f4",
                title="optional-field",
                fieldType="Text",
                value="custom",
                sectionId=None,
            ),
        ],
        sections=[ItemSection(id="sec1", title="Section")],
        notes="",
        tags=[],
        websites=[],
        version=1,
        files=[],
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )


@pytest.mark.asyncio
async def test_load_config_complex_schema(
    mock_op_client, mock_vault, mock_item_overview, complex_item
):
    """Test config loading with complex nested schema."""
    with patch("configator.core._get_client", return_value=mock_op_client):
        mock_op_client.vaults.list.return_value = [mock_vault]
        mock_op_client.items.list.return_value = [mock_item_overview]
        mock_op_client.items.get.return_value = complex_item
        mock_op_client.secrets.resolve_all.side_effect = _echo_resolve_all

        result = await load_config(
            token="test_token", vault="TestVault", item="TestItem", schema=ComplexConfig
        )

        assert isinstance(result, ComplexConfig)
        assert result.simple_field == "simple"
        assert isinstance(result.section, SectionConfig)
        assert result.section.debug is True
        assert result.section.timeout == 200
        assert result.optional_field == "custom"


@pytest.mark.asyncio
async def test_load_config_complex_schema_idempotent(
    mock_op_client, mock_vault, mock_item_overview, complex_item
):
    """Test that loading complex schema twice yields the same result."""
    with patch("configator.core._get_client", return_value=mock_op_client):
        mock_op_client.vaults.list.return_value = [mock_vault]
        mock_op_client.items.list.return_value = [mock_item_overview]
        mock_op_client.items.get.return_value = complex_item
        mock_op_client.secrets.resolve_all.side_effect = _echo_resolve_all

        first = await load_config(
            token="test_token", vault="TestVault", item="TestItem", schema=ComplexConfig
        )
        second = await load_config(
            token="test_token", vault="TestVault", item="TestItem", schema=ComplexConfig
        )

        assert first == second
