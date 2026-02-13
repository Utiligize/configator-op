"""Unit tests for Configator core functionality."""

from unittest.mock import AsyncMock, patch

from onepassword.types import Item, ItemField, ItemOverview, ItemSection, VaultOverview
from pydantic import BaseModel
from pytest import fixture, mark, raises

from configator.core import (
    _field_matcher,
    _get_client,
    _get_item_overview,
    _get_sections,
    _get_vault_overview,
    _hydrate_model,
    _op_field_name_to_lower_snake_case,
    _parse_bool,
    _resolve_op_link,
    load_config,
)


# Test schemas
class SimpleConfig(BaseModel):
    """Simple configuration schema."""

    field_one: str
    field_two: int


class SectionConfig(BaseModel):
    """Section configuration schema."""

    debug: bool
    timeout: int


class ComplexConfig(BaseModel):
    """Complex configuration schema with nested sections."""

    simple_field: str
    section: SectionConfig
    optional_field: str = "default_value"


# Fixtures
@fixture
def mock_vault():
    """Mock VaultOverview."""
    return VaultOverview(
        id="vault123",
        title="TestVault",
        createdAt="2024-01-01T00:00:00Z",
        updatedAt="2024-01-01T00:00:00Z",
    )


@fixture
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


@fixture
def mock_item_field():
    """Mock ItemField."""
    return ItemField(
        id="field1",
        title="Field-One",
        fieldType="Text",
        value="test_value",
        sectionId=None,
    )


@fixture
def mock_item_section():
    """Mock ItemSection."""
    return ItemSection(id="section1", title="Section")


@fixture
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


@fixture
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
@mark.asyncio
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
@mark.asyncio
async def test_get_vault_overview_found(mock_op_client, mock_vault):
    """Test retrieving existing vault."""
    mock_op_client.vaults.list.return_value = [mock_vault]
    result = await _get_vault_overview(mock_op_client, "TestVault")
    assert result == mock_vault


@mark.asyncio
async def test_get_vault_overview_not_found(mock_op_client, mock_vault):
    """Test retrieving non-existing vault."""
    mock_op_client.vaults.list.return_value = [mock_vault]
    result = await _get_vault_overview(mock_op_client, "NonExistentVault")
    assert result is None


@mark.asyncio
async def test_get_vault_overview_empty_list(mock_op_client):
    """Test retrieving vault from empty vault list."""
    mock_op_client.vaults.list.return_value = []
    result = await _get_vault_overview(mock_op_client, "TestVault")
    assert result is None


# Tests for _get_item_overview
@mark.asyncio
async def test_get_item_overview_found(mock_op_client, mock_item_overview):
    """Test retrieving existing item."""
    mock_op_client.items.list.return_value = [mock_item_overview]
    result = await _get_item_overview(mock_op_client, "vault123", "TestItem")
    assert result == mock_item_overview


@mark.asyncio
async def test_get_item_overview_not_found(mock_op_client, mock_item_overview):
    """Test retrieving non-existing item."""
    mock_op_client.items.list.return_value = [mock_item_overview]
    result = await _get_item_overview(mock_op_client, "vault123", "NonExistentItem")
    assert result is None


@mark.asyncio
async def test_get_item_overview_empty_list(mock_op_client):
    """Test retrieving item from empty item list."""
    mock_op_client.items.list.return_value = []
    result = await _get_item_overview(mock_op_client, "vault123", "TestItem")
    assert result is None


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
    with raises(ValueError, match="cannot parse 'invalid' as boolean"):
        _parse_bool("invalid")


# Tests for _resolve_op_link
@mark.asyncio
async def test_resolve_op_link_no_link(mock_op_client):
    """Test resolving non-op:// link."""
    result = await _resolve_op_link(mock_op_client, "plain_value")
    assert result == "plain_value"
    mock_op_client.secrets.resolve.assert_not_called()


@mark.asyncio
async def test_resolve_op_link_single_link(mock_op_client):
    """Test resolving single op:// link."""
    mock_op_client.secrets.resolve.return_value = "resolved_value"
    result = await _resolve_op_link(mock_op_client, "op://vault/item/field")
    assert result == "resolved_value"
    mock_op_client.secrets.resolve.assert_called_once_with("op://vault/item/field")


@mark.asyncio
async def test_resolve_op_link_nested_links(mock_op_client):
    """Test resolving nested op:// links."""
    mock_op_client.secrets.resolve.side_effect = [
        "op://vault2/item2/field2",
        "final_value",
    ]
    result = await _resolve_op_link(mock_op_client, "op://vault1/item1/field1")
    assert result == "final_value"
    assert mock_op_client.secrets.resolve.call_count == 2


@mark.asyncio
async def test_resolve_op_link_too_deep(mock_op_client):
    """Test resolving op:// link with too many levels raises RuntimeError."""
    mock_op_client.secrets.resolve.return_value = "op://vault/item/field"
    with raises(RuntimeError, match="the dwarves delved too greedily and too deep"):
        await _resolve_op_link(mock_op_client, "op://vault/item/field")


# Tests for _hydrate_model
@mark.asyncio
async def test_hydrate_model_simple(mock_op_client):
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
            ItemField(
                id="f2", title="field-two", fieldType="Text", value="42", sectionId=None
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
    mock_op_client.secrets.resolve.side_effect = lambda x: x
    result = await _hydrate_model(op_client=mock_op_client, schema=SimpleConfig, item=item)
    assert result.field_one == "test"
    assert result.field_two == 42


@mark.asyncio
async def test_hydrate_model_with_bool(mock_op_client):
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
    mock_op_client.secrets.resolve.side_effect = lambda x: x
    result = await _hydrate_model(op_client=mock_op_client, schema=SectionConfig, item=item, section_id="sec1")
    assert result.debug is True
    assert result.timeout == 30


@mark.asyncio
async def test_hydrate_model_with_default_value(mock_op_client):
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
            ItemField(
                id="f2", title="debug", fieldType="Text", value="false", sectionId="sec1"
            ),
            ItemField(
                id="f3", title="timeout", fieldType="Text", value="60", sectionId="sec1"
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
    mock_op_client.secrets.resolve.side_effect = lambda x: x
    result = await _hydrate_model(op_client=mock_op_client, schema=ComplexConfig, item=item)
    assert result.simple_field == "value"
    assert result.section.debug is False
    assert result.section.timeout == 60
    assert result.optional_field == "default_value"


@mark.asyncio
async def test_hydrate_model_missing_required_field(mock_op_client):
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
    mock_op_client.secrets.resolve.side_effect = lambda x: x
    # StopIteration in async context is wrapped in RuntimeError (PEP 479)
    with raises(RuntimeError, match="coroutine raised StopIteration"):
        await _hydrate_model(op_client=mock_op_client, schema=SimpleConfig, item=item)


@mark.asyncio
async def test_hydrate_model_with_op_link(mock_op_client):
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
            ItemField(
                id="f2", title="field-two", fieldType="Text", value="42", sectionId=None
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
    mock_op_client.secrets.resolve.return_value = "resolved_value"
    result = await _hydrate_model(op_client=mock_op_client, schema=SimpleConfig, item=item)
    assert result.field_one == "resolved_value"
    assert result.field_two == 42


@mark.asyncio
async def test_hydrate_model_nested_sections(mock_op_client):
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
            ItemField(
                id="f2", title="debug", fieldType="Text", value="yes", sectionId="sec1"
            ),
            ItemField(
                id="f3", title="timeout", fieldType="Text", value="100", sectionId="sec1"
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
    mock_op_client.secrets.resolve.side_effect = lambda x: x
    result = await _hydrate_model(op_client=mock_op_client, schema=ComplexConfig, item=item)
    assert result.simple_field == "test"
    assert isinstance(result.section, SectionConfig)
    assert result.section.debug is True
    assert result.section.timeout == 100


# Tests for load_config
@mark.asyncio
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
            ItemField(
                id="f2", title="field-two", fieldType="Text", value="123", sectionId=None
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

    with patch("configator.core._get_client", return_value=mock_op_client):
        mock_op_client.vaults.list.return_value = [mock_vault]
        mock_op_client.items.list.return_value = [mock_item_overview]
        mock_op_client.items.get.return_value = item
        mock_op_client.secrets.resolve.side_effect = lambda x: x

        result = await load_config(
            token="test_token", vault="TestVault", item="TestItem", schema=SimpleConfig
        )

        assert isinstance(result, SimpleConfig)
        assert result.field_one == "test_value"
        assert result.field_two == 123


@mark.asyncio
async def test_load_config_vault_not_found(mock_op_client):
    """Test config loading with non-existent vault."""
    with patch("configator.core._get_client", return_value=mock_op_client):
        mock_op_client.vaults.list.return_value = []

        with raises(RuntimeError, match="vault 'NonExistentVault' not found"):
            await load_config(
                token="test_token",
                vault="NonExistentVault",
                item="TestItem",
                schema=SimpleConfig,
            )


@mark.asyncio
async def test_load_config_item_not_found(mock_op_client, mock_vault):
    """Test config loading with non-existent item."""
    with patch("configator.core._get_client", return_value=mock_op_client):
        mock_op_client.vaults.list.return_value = [mock_vault]
        mock_op_client.items.list.return_value = []

        with raises(
            RuntimeError, match="item 'NonExistentItem' not found in vault TestVault"
        ):
            await load_config(
                token="test_token",
                vault="TestVault",
                item="NonExistentItem",
                schema=SimpleConfig,
            )


@mark.asyncio
async def test_load_config_complex_schema(mock_op_client, mock_vault, mock_item_overview):
    """Test config loading with complex nested schema."""
    item = Item(
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
            ItemField(
                id="f2", title="debug", fieldType="Text", value="on", sectionId="sec1"
            ),
            ItemField(
                id="f3", title="timeout", fieldType="Text", value="200", sectionId="sec1"
            ),
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

    with patch("configator.core._get_client", return_value=mock_op_client):
        mock_op_client.vaults.list.return_value = [mock_vault]
        mock_op_client.items.list.return_value = [mock_item_overview]
        mock_op_client.items.get.return_value = item
        mock_op_client.secrets.resolve.side_effect = lambda x: x

        result = await load_config(
            token="test_token", vault="TestVault", item="TestItem", schema=ComplexConfig
        )

        assert isinstance(result, ComplexConfig)
        assert result.simple_field == "simple"
        assert isinstance(result.section, SectionConfig)
        assert result.section.debug is True
        assert result.section.timeout == 200
        assert result.optional_field == "custom"

    with patch("configator.core._get_client", return_value=mock_op_client):
        mock_op_client.vaults.list.return_value = [mock_vault]
        mock_op_client.items.list.return_value = [mock_item_overview]
        mock_op_client.items.get.return_value = item
        mock_op_client.secrets.resolve.side_effect = lambda x: x

        result = await load_config(
            token="test_token", vault="TestVault", item="TestItem", schema=ComplexConfig
        )

        assert isinstance(result, ComplexConfig)
        assert result.simple_field == "simple"
        assert isinstance(result.section, SectionConfig)
        assert result.section.debug is True
        assert result.section.timeout == 200
        assert result.optional_field == "custom"
