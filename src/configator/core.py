"""Main module for Configator."""

###################################################################################################
# Copyright (c) 2025 Utiligize ApS <contact@utiligize.com>                                        #
# This file is part of Configator: <https://github.com/Utiligize/configator>                      #
# SPDX-License-Identifier: MIT                                                                    #
# License-Filename: LICENSE.md                                                                    #
###################################################################################################

from collections.abc import Mapping
from functools import partial
from importlib.metadata import version
from json import JSONDecodeError, loads
from typing import Any, get_origin

from onepassword.client import Client as OnePasswordClient
from onepassword.errors import RateLimitExceededException
from onepassword.types import Item, ItemField, ItemOverview, ResolveAllResponse, VaultOverview
from pydantic import BaseModel
from pydantic.fields import PydanticUndefined
from stamina import retry

from .log import get_logger

log = get_logger()

# One request each for vaults.list, items.list and items.get.
_LOOKUP_REQUESTS = 3
_MAX_REFERENCE_DEPTH = 10
_OP_SCHEME = "op://"

# Kept well inside a typical container start-up budget (gunicorn's 30 s worker timeout,
# the deploy tooling's 120 s readiness wait) so a partial 1Password outage reads as a slow
# start rather than a failed deploy.
_RETRY_ATTEMPTS = 3
_RETRY_TIMEOUT = 10.0
_RETRY_WAIT_INITIAL = 0.2
_RETRY_WAIT_MAX = 2.0


def _is_transient(exc: Exception) -> bool:
    """Return True for errors worth retrying; a rate limit never is.

    A rate-limited response reports no usable retry-after and the hourly read
    budget can be up to an hour from resetting, so every retry is another
    request spent against a budget that is already empty.
    """
    if isinstance(exc, RateLimitExceededException):
        log.error("1Password rate limit exceeded; not retrying: %s", str(exc))
        return False
    return True


_retry = partial(
    retry,
    on=_is_transient,
    attempts=_RETRY_ATTEMPTS,
    timeout=_RETRY_TIMEOUT,
    wait_initial=_RETRY_WAIT_INITIAL,
    wait_max=_RETRY_WAIT_MAX,
)


async def load_config[T: BaseModel](*, token: str, vault: str, item: str, schema: type[T]) -> T:
    """Return an initialized schema instance."""
    log.debug("loading configuration into schema '%s'", schema.__name__)

    client = await _get_client(token)

    vault_overview = await _get_vault_overview(client, vault)
    if vault_overview is None:
        raise RuntimeError(f"vault '{vault}' not found")

    item_overview = await _get_item_overview(client, vault_overview.id, item)
    if item_overview is None:
        raise RuntimeError(f"item '{item}' not found in vault {vault}")

    cfg_item = await _get_item(client, vault_overview.id, item_overview.id)

    resolved, resolve_requests = await _resolve_references(client, cfg_item)

    config = _hydrate_model(resolved=resolved, schema=schema, item=cfg_item)
    log.info(
        "loaded configuration into schema '%s' using %d 1Password request(s)",
        schema.__name__,
        _LOOKUP_REQUESTS + resolve_requests,
    )
    return config


def _field_matcher(field: ItemField, *, title: str, section_id: str | None = None) -> bool:
    """Return True if the given field matches the title and optional section ID."""
    normalized_title = _op_field_name_to_lower_snake_case(field.title)
    return normalized_title == title and (section_id is None or field.section_id == section_id)


@_retry()
async def _get_client(token: str) -> OnePasswordClient:
    """Initialize 1Password client."""
    pkg_name = "configator_op"
    pkg_version = version(pkg_name)
    log.debug("instantiating 1Password client (%s-%s)", pkg_name, pkg_version)
    op_client = await OnePasswordClient.authenticate(
        auth=token,
        integration_name=pkg_name,
        integration_version=pkg_version,
    )
    log.debug("1Password client authenticated")
    return op_client


@_retry()
async def _get_item(op_client: OnePasswordClient, vault_id: str, item_id: str) -> Item:
    """Retrieve the config item."""
    log.debug("retrieving item '%s' from vault '%s'", item_id, vault_id)
    return await op_client.items.get(vault_id=vault_id, item_id=item_id)


@_retry()
async def _get_item_overview(
    op_client: OnePasswordClient, vault_id: str, item_name: str
) -> ItemOverview | None:
    """Retrieve item overview."""
    log.debug("retrieving item '%s' from vault '%s'", item_name, vault_id)
    available_items = await op_client.items.list(vault_id=vault_id)
    for item in available_items:
        if item.title == item_name:
            return item
    log.warning("item '%s' not found in vault '%s'", item_name, vault_id)
    return None


def _get_sections(item: Item) -> dict[str, str]:
    """Return mapping of section titles to IDs."""
    return {s.title.lower(): s.id for s in item.sections if s.title}


@_retry()
async def _get_vault_overview(
    op_client: OnePasswordClient, vault_name: str
) -> VaultOverview | None:
    """Retrieve vault overview."""
    log.debug("retrieving vault '%s'", vault_name)
    available_vaults = await op_client.vaults.list()
    for vault in available_vaults:
        if vault.title == vault_name:
            return vault
    log.warning("vault '%s' not found", vault_name)
    return None


def _hydrate_field(
    *,
    resolved: Mapping[str, str],
    cls: type,
    item: Item,
    key: str,
    default: Any,
    section_id: str | None = None,
) -> Any:
    """Hydrate single field from 1Password item."""
    wet_fields = item.fields
    # Parameterized generics (e.g. list[str]) are not classes, so resolve them to their
    # origin before any issubclass() check; non-generic annotations are their own origin.
    origin = get_origin(cls) or cls
    if issubclass(origin, BaseModel):
        sections = _get_sections(item)
        return _hydrate_model(
            resolved=resolved, schema=cls, item=item, section_id=sections[key.lower()]
        )

    matcher = partial(_field_matcher, title=key.lower(), section_id=section_id)
    wet_field = next(filter(matcher, wet_fields), None)
    if wet_field is None:
        if default is PydanticUndefined:
            log.error("field '%s' not found and no default value provided", key)
            raise RuntimeError(f"field '{key}' not found and no default value provided")
        log.debug("using default value for field '%s'", key)
        return default

    str_val = resolved.get(wet_field.value, wet_field.value)
    try:
        if issubclass(origin, (dict, list, set, tuple)):
            return cls(loads(str_val))
        if issubclass(origin, bool):
            return _parse_bool(str_val)
        return cls(str_val)  # type: ignore[call-arg]
    except JSONDecodeError as jde:
        log.error("failed to parse field '%s' as JSON: %s", key, str(jde))
        raise


def _hydrate_model[T: BaseModel](
    *,
    resolved: Mapping[str, str],
    schema: type[T],
    item: Item,
    section_id: str | None = None,
) -> T:
    """Hydrate Pydantic model from 1Password item."""
    log.debug("hydrating model '%s'", schema.__name__)
    dry_model = schema.model_fields
    wet_model: dict[str, Any] = {}
    for key in dry_model:
        log.debug("hydrating field '%s'", key)
        cls = dry_model[key].annotation
        if cls is None:
            log.warning("no annotation for field '%s'; skipping", key)
            continue

        wet_model[key] = _hydrate_field(
            resolved=resolved,
            cls=cls,
            item=item,
            key=key,
            default=dry_model[key].default,
            section_id=section_id,
        )

    return schema(**wet_model)


def _op_field_name_to_lower_snake_case(name: str) -> str:
    """Convert 1Password field name to lower_snake_case."""
    return name.replace("-", "_").lower()


def _parse_bool(str_val: str) -> bool:
    """Parse boolean value from string."""
    truthy = {"true", "1", "yes", "on"}
    trumpy = {"false", "0", "no", "off"}
    val_lower = str_val.strip().lower()
    if val_lower in truthy:
        return True
    elif val_lower in trumpy:
        return False
    else:
        raise ValueError(f"cannot parse '{str_val}' as boolean")


@_retry()
async def _resolve_all(op_client: OnePasswordClient, references: list[str]) -> ResolveAllResponse:
    """Resolve a batch of op:// references in a single request."""
    log.debug("resolving %d secret reference(s) in one request", len(references))
    return await op_client.secrets.resolve_all(references)


async def _resolve_references(
    op_client: OnePasswordClient, item: Item
) -> tuple[dict[str, str], int]:
    """Resolve every op:// reference in the item, returning the values and the request count.

    References are deduplicated and resolved one batch at a time, so an item with N
    referencing fields costs one request per level of nesting rather than one per field.
    """
    resolved = {f.value: f.value for f in item.fields if f.value.startswith(_OP_SCHEME)}
    requests = 0
    while True:
        pending = sorted({v for v in resolved.values() if v.startswith(_OP_SCHEME)})
        if not pending:
            return resolved, requests
        if requests == _MAX_REFERENCE_DEPTH:
            log.error("too many nested op:// references when resolving item '%s'", item.title)
            raise RuntimeError("the dwarves delved too greedily and too deep")

        try:
            response = await _resolve_all(op_client, pending)
        except Exception as exc:
            raise RuntimeError(f"failed to resolve {len(pending)} secret reference(s)") from exc
        requests += 1

        secrets = _unwrap_resolved(response)
        missing = [reference for reference in pending if reference not in secrets]
        if missing:
            log.error("1Password returned no result for %d secret reference(s)", len(missing))
            raise RuntimeError(
                f"1Password returned no result for secret reference(s): {', '.join(missing)}"
            )
        resolved = {ref: secrets.get(value, value) for ref, value in resolved.items()}


def _unwrap_resolved(response: ResolveAllResponse) -> dict[str, str]:
    """Return the resolved secret for each reference, raising on the first failure."""
    secrets: dict[str, str] = {}
    for reference, individual in response.individual_responses.items():
        if individual.content is None:
            raise RuntimeError(
                f"failed to resolve secret reference '{reference}': {individual.error}"
            )
        secrets[reference] = individual.content.secret
    return secrets
