# Architecture Decision Records

<!-- omit in toc -->
## Table of Contents

- [ADR-001: Use Structlog for logging](#adr-001-use-structlog-for-logging)
- [ADR-002: Use Pydantic for configuration schema validation](#adr-002-use-pydantic-for-configuration-schema-validation)
- [ADR-003: Integrate directly with 1Password SDK](#adr-003-integrate-directly-with-1password-sdk)
- [ADR-004: Map nested models to 1Password sections](#adr-004-map-nested-models-to-1password-sections)
- [ADR-005: Normalize field names to snake\_case](#adr-005-normalize-field-names-to-snake_case)
- [ADR-006: Support recursive op:// secret references](#adr-006-support-recursive-op-secret-references)
- [ADR-007: Use async-first API design](#adr-007-use-async-first-api-design)
- [ADR-008: Implement special boolean parsing from strings](#adr-008-implement-special-boolean-parsing-from-strings)
- [ADR-009: Provide minimal public API surface](#adr-009-provide-minimal-public-api-surface)
- [ADR-010: Provide common configuration models as mixins](#adr-010-provide-common-configuration-models-as-mixins)
- [ADR-011: Support developer mode with .env file priority](#adr-011-support-developer-mode-with-env-file-priority)
- [ADR-012: Batch op:// reference resolution](#adr-012-batch-op-reference-resolution)
- [ADR-013: Retry 1Password calls, but never a rate limit](#adr-013-retry-1password-calls-but-never-a-rate-limit)
- [ADR-014: Split failures into unavailable and invalid](#adr-014-split-failures-into-unavailable-and-invalid)

## ADR-001: Use Structlog for logging

**Date:** 2025-11-12

**Context:**

We want the module to output structured logs.

**Decision:**

Use [structlog](https://www.structlog.org/) for log messages.

**Consequences:**

- Benefits
  - Emits structured, machine-readable logs (JSON, key/value) that are easy to index and query in log stores (ELK, Loki, Datadog).
  - Encourages consistent log schema and contextual logging (event-wise context, bound processors).
  - Easier to attach contextual data (request id, user id) without string formatting.
  - Simpler testing and assertions against emitted events.
  - Flexible output pipelines — processors can format, filter, redact, or enrich events centrally.

- Costs / Trade-offs
  - Adds a runtime dependency (structlog) and requires team familiarity with its API and concepts (processors, bind, event_dict).
  - Slight configuration complexity to wire structlog with Python's stdlib logging and third‑party libraries.
  - Possible performance overhead if many expensive processors are used; careful processor design is required.

- Operational considerations
  - Decide a canonical output format (JSON for ingestion systems or human console format for local dev).
  - Standardize event and field names to avoid fragmentation across services.
  - Implement redaction/PII handling as processors.
  - Ensure log rotation/retention and existing monitoring tooling accept the chosen format.

- Developer impact
  - Improves debuggability and observability long term.
  - Requires documentation and examples for developers to adopt consistent usage.
  - Tests should assert on structured events instead of formatted strings.

## ADR-002: Use Pydantic for configuration schema validation

**Date:** 2025-11-14

**Context:**

We need a type-safe way to define and validate application configuration loaded from 1Password. The configuration schema should be self-documenting, provide IDE autocomplete, and catch type errors at runtime.

**Decision:**

Use Pydantic's `BaseModel` as the base class for all configuration schemas. Users define their configuration structure as Python classes inheriting from `BaseModel`, with field names and types defined as class attributes.

**Consequences:**

- Benefits
  - Type safety: Field types are enforced at runtime with automatic type coercion where appropriate.
  - IDE support: Full autocomplete and type checking in modern Python IDEs.
  - Self-documenting: Schema definition serves as documentation for configuration structure.
  - Validation: Built-in validation rules (e.g., `Field(ge=0.0, le=1.0)` for ranges).
  - Serialization: Easy conversion to/from dictionaries and JSON.
  - Default values: Native support for default values via Pydantic's field defaults.
  - Nested structures: Natural support for nested configuration via nested models.

- Costs / Trade-offs
  - Runtime dependency on Pydantic v2.
  - Learning curve for teams unfamiliar with Pydantic.
  - Potential performance overhead for validation (negligible for configuration loading use case).
  - Limited to Pydantic's type system (though this covers most use cases).

- Operational considerations
  - Configuration schema changes are code changes requiring deployment.
  - Schema validation errors surface at application startup rather than during 1Password item creation.
  - Teams must maintain compatibility between 1Password items and code schemas.

- Developer impact
  - Clear, IDE-friendly configuration definitions.
  - Compile-time and runtime type checking reduces configuration errors.
  - Easy to extend with custom validators if needed.

## ADR-003: Integrate directly with 1Password SDK

**Date:** 2025-11-14

**Context:**

We need to retrieve configuration values from 1Password vaults. Multiple approaches exist: using the 1Password CLI (`op`), using the 1Password Connect API, or using the official 1Password Python SDK.

**Decision:**

Use the official 1Password Python SDK (`onepassword-sdk`) for direct integration with 1Password services. Authenticate using service account tokens passed as parameters.

**Consequences:**

- Benefits
  - Official SDK: Maintained by 1Password with guaranteed API compatibility.
  - Native async support: SDK provides async methods matching our async-first design.
  - Type safety: SDK includes type stubs for better IDE support.
  - Simplified authentication: Service account tokens provide secure, programmatic access.
  - No external process dependencies: No need to install or manage the `op` CLI.
  - Secret reference resolution: Built-in support for resolving `op://` references.

- Costs / Trade-offs
  - Dependency on SDK maintained by external party.
  - SDK version upgrades may introduce breaking changes.
  - Service account tokens required (not suitable for individual user authentication scenarios).
  - SDK adds to application binary size.

- Operational considerations
  - Service account tokens must be securely managed (environment variables, key vaults).
  - Token rotation procedures must be established.
  - SDK version must be kept current for security patches.

- Developer impact
  - Straightforward API for vault and item access.
  - Integration name and version automatically reported to 1Password for usage tracking.
  - Good error messages from SDK help with debugging.

## ADR-004: Map nested models to 1Password sections

**Date:** 2025-11-14

**Context:**

Configuration often has logical groupings (database settings, API keys, feature flags). 1Password items support sections for organizing fields. We need a convention for mapping Python configuration structure to 1Password items.

**Decision:**

Map nested Pydantic models to 1Password item sections. When a configuration field's type is a `BaseModel` subclass, look for a section with the same name (normalized to lowercase) and hydrate the nested model from fields in that section. Fields in the root model match against fields in any section (or no section).

**Consequences:**

- Benefits
  - Logical organization: Configuration naturally groups related settings.
  - Namespace isolation: Nested models can have fields with the same name as other sections.
  - Clarity in 1Password: Sections in 1Password mirror code structure.
  - Extensibility: Easy to add new configuration groups by adding nested models.

- Costs / Trade-offs
  - Convention requires understanding of mapping rules.
  - Section names must match nested model field names (case-insensitive).
  - Root-level fields can come from any section, requiring unique naming.
  - Doesn't support arbitrarily deep nesting (practical limitation, not technical).

- Operational considerations
  - 1Password item sections must be created manually to match schema.
  - Refactoring nested model names requires updating 1Password sections.
  - Section title changes in 1Password break configuration loading.

- Developer impact
  - Natural code organization matching configuration domain.
  - Intuitive for developers familiar with nested data structures.
  - Clear error messages when sections are missing.

## ADR-005: Normalize field names to snake_case

**Date:** 2025-11-14

**Context:**

Python uses `snake_case` for variable names by convention. 1Password allows various naming conventions including "Title Case", "kebab-case", and "SCREAMING_SNAKE_CASE". We need a consistent mapping between 1Password field names and Python model field names.

**Decision:**

Normalize 1Password field titles to lowercase snake_case when matching against Python model fields. Convert hyphens to underscores and lowercase all characters. For example, "Database-Host", "database-host", and "DATABASE_HOST" all match a Python field named `database_host`.

**Consequences:**

- Benefits
  - Flexibility: Multiple 1Password naming conventions map to Python convention.
  - Python idiomatic: Matches PEP 8 naming guidelines.
  - Case insensitive: Reduces errors from capitalization differences.
  - Hyphen conversion: Accommodates common 1Password naming with hyphens.

- Costs / Trade-offs
  - May cause collisions if 1Password has fields differing only in case/hyphens (e.g., "api-key" and "API_KEY").
  - Hidden complexity: Normalization logic not obvious to users.
  - No support for other naming conventions (camelCase not converted).

- Operational considerations
  - Field names must be unique within their scope (section or root) after normalization.
  - Teams should establish 1Password field naming conventions to avoid collisions.
  - Case sensitivity errors in 1Password won't be caught until runtime.

- Developer impact
  - Reduces friction when 1Password naming doesn't match Python conventions.
  - Developers must be aware of normalization when debugging field matching issues.

## ADR-006: Support recursive op:// secret references

**Date:** 2025-11-14

**Context:**

1Password supports secret references using `op://vault/item/field` syntax. A field's value can be a reference to another field, enabling DRY configuration. References may chain (a reference pointing to another reference).

**Decision:**

Recursively resolve `op://` references using the SDK's `secrets.resolve()` method. Limit recursion depth to 10 levels to prevent infinite loops from circular references. All field values are checked for `op://` prefix and resolved before type coercion.

**Consequences:**

- Benefits
  - DRY configuration: Share common values (API endpoints, service names) across multiple items.
  - Security: Centralize sensitive values in dedicated items.
  - Flexibility: Update shared values without touching dependent items.
  - Transitive resolution: References to references work transparently.

- Costs / Trade-offs
  - Performance: References cost 1Password requests; see [ADR-012](#adr-012-batch-op-reference-resolution) for how they are batched.
  - Complexity: Nested references harder to debug.
  - Recursion limit: Circular references fail at runtime after 10 iterations.
  - Error messages: Deep reference chains make error messages less clear about source location.

- Operational considerations
  - Reference chains should be kept shallow (ideally 1-2 levels) for performance and maintainability.
  - Circular references must be detected and prevented in 1Password organization practices.
  - Reference resolution errors only caught at application startup.

- Developer impact
  - Transparent to schema definitions - works with any field type.
  - Debugging requires tracing through 1Password UI to understand reference chains.
  - Error message "the dwarves delved too greedily and too deep" signals circular reference or excessive depth.

## ADR-007: Use async-first API design

**Date:** 2025-11-14

**Context:**

The 1Password SDK provides async methods for all I/O operations. Modern Python applications increasingly use async/await for concurrent I/O. We must decide whether to provide sync, async, or both APIs.

**Decision:**

Provide only async APIs. All public functions are async and require `await`. Users must run from an async context (e.g., `asyncio.run()`, existing async frameworks).

**Consequences:**

- Benefits
  - SDK alignment: Natural fit with 1Password SDK's async methods.
  - Performance: Enables concurrent configuration loading if needed in future.
  - Modern Python: Aligns with async ecosystem (FastAPI, aiohttp, asyncpg).
  - Simpler codebase: No sync wrappers or duplicate code paths.
  - Better for I/O: Inherently I/O-bound operations benefit from async.

- Costs / Trade-offs
  - Requires async runtime: Users must use `asyncio.run()` or equivalent.
  - Not usable from sync code without wrapper: Integration with sync frameworks requires adaptation.
  - Slight complexity for simple use cases: Boilerplate of `asyncio.run()` for simple scripts.

- Operational considerations
  - Compatible with async application frameworks (FastAPI, Quart, Sanic).
  - May require refactoring for existing sync applications.
  - Testing requires pytest-asyncio or similar async test support.

- Developer impact
  - Must understand async/await basics.
  - Natural fit for developers already using async frameworks.
  - Clear code with explicit async boundaries.

## ADR-008: Implement special boolean parsing from strings

**Date:** 2025-11-14

**Context:**

1Password stores all field values as strings. Python booleans require special handling because any non-empty string is truthy in Python (e.g., `bool("false")` is `True`). We need explicit parsing rules for boolean configuration values.

**Decision:**

Implement custom boolean parsing that recognizes 8 case-insensitive string values:

- Truthy: "true", "1", "yes", "on"
- Falsy: "false", "0", "no", "off"

Any other string value raises `ValueError`.

**Consequences:**

- Benefits
  - Predictable: Clear, documented set of valid boolean strings.
  - Prevents bugs: Catches invalid boolean values early rather than accepting all strings as truthy.
  - User friendly: Supports common boolean representations from various systems.
  - Case insensitive: Reduces user error from capitalization.

- Costs / Trade-offs
  - Special case logic: Booleans handled differently from other types.
  - Restrictive: Doesn't accept other common values like "True"/"False" (Python string representations).
  - Runtime errors: Invalid boolean strings fail at application startup.

- Operational considerations
  - 1Password boolean fields must use one of the 8 valid values.
  - Teams should document valid boolean strings in configuration guides.
  - Error messages clearly indicate valid values when parsing fails.

- Developer impact
  - Must use supported boolean strings in 1Password items.
  - Clear error messages when invalid values used.
  - Explicit validation better than silent conversion bugs.

## ADR-009: Provide minimal public API surface

**Date:** 2025-11-14

**Context:**

Library design involves balancing flexibility with simplicity. A large API surface provides flexibility but increases maintenance burden and user cognitive load. Configuration loading has a clear primary use case.

**Decision:**

Expose only `load_config()` as the public API. Accept parameters as keyword arguments: `token`, `vault`, `item`, and `schema`. All implementation details (client initialization, field matching, hydration) are private functions.

**Consequences:**

- Benefits
  - Simple API: One function to learn and use.
  - Encapsulation: Implementation can change without breaking users.
  - Clear intent: Function name and signature communicate purpose.
  - Easy testing: Single entry point simplifies test coverage.
  - Reduced maintenance: Fewer public functions to maintain compatibility for.

- Costs / Trade-offs
  - Less flexibility: Users can't reuse internal components for custom workflows.
  - All-or-nothing: Can't easily load parts of configuration separately.
  - Parameter passing: Must pass token for every call (no client reuse).

- Operational considerations
  - Function signature changes are breaking changes requiring major version bump.
  - Advanced use cases may require forking or requesting new features.

- Developer impact
  - Extremely simple to use: Single function call with clear parameters.
  - Reduced cognitive load: No complex API to learn.
  - Limited customization: Must use the provided workflow or go around the library.

## ADR-010: Provide common configuration models as mixins

**Date:** 2025-11-14

**Context:**

Many applications need similar configuration structures (database connections, Sentry integration, environment designation). Duplicating these across projects is error-prone. We can provide reusable, well-tested configuration models.

**Decision:**

Provide common configuration models in `configator.models` module:

- `Environment`: Enum for dev/staging/prod environments
- `PostgresConfig`: Standard PostgreSQL connection parameters with DSN builder
- `PostgresSSLMode`: Enum for PostgreSQL SSL modes
- `SentryConfig`: Sentry DSN and common settings

These can be used directly or composed into larger configurations via nesting.

**Consequences:**

- Benefits
  - Reusability: Standard patterns shared across projects.
  - Best practices: Models encode good defaults and validation rules.
  - Consistency: Same configuration structure across organization.
  - Type safety: Enums for environments and modes prevent typos.
  - Utility methods: E.g., `PostgresConfig.dsn()` builds connection strings.
  - Environment integration: Some fields read from standard environment variables (PGHOST, PGPORT, etc.) as defaults.

- Costs / Trade-offs
  - Opinionated: Models encode specific opinions about structure and naming.
  - Dependencies: Models may pull in extra dependencies (e.g., pydantic's PostgresDsn type).
  - Version lock: Changes to provided models are breaking changes.
  - Not suitable for all: Some projects need different structures.

- Operational considerations
  - Standard models reduce variation across projects (easier to support).
  - Changes to common models require coordination across dependent projects.
  - Projects can extend or override defaults as needed.

- Developer impact
  - Faster project setup: Copy/paste standard configuration classes.
  - Reduced boilerplate: Don't rewrite database config for every project.
  - Learning curve: Developers must understand provided models.
  - Easy to extend: Inherit and add fields as needed for project-specific requirements.

## ADR-011: Support developer mode with .env file priority

**Date:** 2025-11-15

**Context:**

During local development, developers need to test configuration changes without modifying 1Password items. Pydantic Settings supports loading values from multiple sources (.env files, environment variables, initialization parameters) but with a fixed priority order. We need a way to prioritize local .env files during development while maintaining production behavior by default.

**Decision:**

Introduce a `ConfigatorSettings` base class that extends `pydantic_settings.BaseSettings` and customizes the settings source priority based on the `CONFIGATOR_DEV_MODE` environment variable. When this variable is set to any non-empty value, the priority changes to:

1. .env files (highest priority)
2. Environment variables
3. Initialization parameters
4. File secrets (lowest priority)

Without developer mode (default), the standard priority is maintained:

1. Initialization parameters (highest priority)
2. Environment variables
3. .env files
4. File secrets (lowest priority)

All common configuration models (`PostgresConfig`, `SentryConfig`) extend `ConfigatorSettings` to inherit this behavior.

**Consequences:**

- Benefits
  - Local development: Developers can override configuration values using a .env file without touching 1Password.
  - Safe defaults: Production behavior unchanged unless developer mode explicitly enabled.
  - Explicit control: Clear environment variable signals developer mode activation.
  - Standard workflow: Follows common practice of using .env files for local development.
  - Visibility: Logs a warning message when developer mode is enabled/disabled for awareness.
  - Flexible testing: Easy to test different configuration values without modifying actual secrets.

- Costs / Trade-offs
  - Additional complexity: Two different priority modes to understand and document.
  - Potential confusion: Developers must remember to enable developer mode and understand priority changes.
  - pydantic-settings dependency: Adds pydantic-settings as a required dependency.
  - Mode indicator noise: Warning log on every instantiation (though useful for awareness).
  - Not applicable to core loading: Only works with provided common models, not custom BaseModel schemas.

- Operational considerations
  - .env files should never be committed to version control (add to .gitignore).
  - Developer mode should never be enabled in production environments. This is enforced: when `CONFIGATOR_DEV_MODE` is set while `ENVIRONMENT` (fallback `APP_ENV`) resolves to production — matched case-insensitively against the `Environment.PRODUCTION` prefix (`product`) — instantiating a config model raises a `RuntimeError` instead of silently letting a `.env` file override vetted secrets.
  - Teams should document when and how to use developer mode in development guides.
  - .env file format must match pydantic-settings expectations (KEY=value).

- Developer impact
  - Convenient local development: Test configuration changes without 1Password access.
  - Clear mode switching: Single environment variable controls behavior.
  - Must understand priority: Know which source wins in each mode.
  - Explicit opt-in: Developer mode must be deliberately enabled.
  - Standard patterns: Follows familiar .env file conventions from other frameworks.

## ADR-012: Batch op:// reference resolution

**Date:** 2026-08-18

**Context:**

Resolving each `op://` reference with its own `secrets.resolve()` call made the cost of a
`load_config` proportional to the number of schema fields. A real schema with 87 annotated
fields cost roughly 90 1Password requests per load. Because nothing is cached between
process starts, a container crash-looping under `--restart unless-stopped` multiplied that
figure by the restart count and exhausted a service account's hourly read budget
(10,000 requests), after which neither the application nor the deploy tooling could reach
1Password until the window reset.

**Decision:**

Resolve references in batches instead of one at a time. After the config item is fetched,
collect every field value beginning with `op://`, deduplicate them, and resolve the whole
set with a single `secrets.resolve_all()` call. Chained references are followed by repeating
the batch, one request per level of nesting, keeping the ADR-006 depth limit of 10. The
limit is enforced as ten resolution rounds, so a chain of exactly ten links now resolves;
the previous per-field implementation raised on the tenth hop and therefore only reached
nine. Hydration then reads from the resolved mapping and performs no I/O, so `_hydrate_model`
and `_hydrate_field` are synchronous. The total request count for a load is logged at info level.

**Consequences:**

- Benefits
  - Bounded cost: a load costs `3 + depth` requests regardless of how many fields the schema declares. Measured against the `REPO configator` vault, resolving 14 distinct references (one of them chained one level) cost 30 reads before and 2 after.
  - Crash-loop safety: a restarting container can no longer exhaust an hourly token budget on its own.
  - Deduplication: a reference repeated across fields is resolved once.
  - Lower latency: one round trip per nesting level instead of one per field.
  - Observability: the per-load request count appears in startup logs.
  - Simpler retry seam: retry logic (see UT-9205) wraps one batch call rather than N per-field calls.

- Costs / Trade-offs
  - Every `op://` field in the config item is resolved, including fields the schema does not
    declare. Batched into the same request this is effectively free, but the values are fetched.
  - `resolve_all` reports per-reference failures in its response rather than raising, so failures
    are surfaced by inspecting the response instead of by exception. A reference the response
    omits entirely is reported by name rather than retried, since retrying it could not make
    progress and would otherwise be misreported as an over-deep reference chain.
  - A missing required field now raises `RuntimeError` directly; previously the `StopIteration`
    from the field lookup was converted to `RuntimeError` by PEP 479 because the hydrator was async.

- Operational considerations
  - Requires `onepassword-sdk` with `secrets.resolve_all` (0.3 and later).
  - Startup logs record the request count, so regressions in load cost are visible without instrumentation.

- Developer impact
  - No change to schema definitions or to the `load_config` signature.
  - Deep reference chains still cost one request per level, so keeping chains shallow remains worthwhile.

## ADR-013: Retry 1Password calls, but never a rate limit

**Date:** 2026-08-18

**Context:**

A `load_config` is a chain of network calls, and any of them can fail on a transient
network blip. Without retries a single blip fails application start-up, which under a
container restart policy turns into a restart and a fresh set of 1Password requests.

Retrying is not universally safe, though. When a service account exceeds its hourly read
budget the SDK raises `RateLimitExceededException`, whose message carries no usable
retry-after (`Try again in  seconds`). Retrying that spends further requests against an
empty budget that may be up to an hour from resetting, and no retry policy has a sensible
upper bound on that timescale. A crash loop retrying rate-limit errors is exactly how the
develop environment locked itself out of 1Password.

**Decision:**

Use [stamina](https://stamina.hynek.me/) to retry each 1Password call individually —
`Client.authenticate`, `vaults.list`, `items.list`, `items.get` and `secrets.resolve_all`
— rather than wrapping the whole load. A retry therefore costs one request, not a reload
of every reference.

Retries are governed by a predicate, `_is_transient`, which treats
`RateLimitExceededException` as terminal (logging an error before it propagates) and every
other exception as worth retrying. The SDK collapses network failures into a bare
`Exception` with a message rather than a typed error, so an allow-list of exception types
would never fire; a deny-list anchored on the one typed error that matters is both simpler
and effective. The cost is that a permanent failure such as a bad token is attempted three
times instead of once.

The budget is 3 attempts with waits from 0.2 s to 2 s, and no further attempt is scheduled
more than 10 seconds after the first. That fits inside a gunicorn worker timeout of 30 s and
leaves room in the deploy tooling's 120 s readiness wait, so a partial 1Password outage reads
as a slow start rather than a failed deploy.

**Consequences:**

- Benefits
  - A transient failure no longer fails application start-up.
  - A retry re-spends one request, not the whole load.
  - Rate limiting fails fast and is logged as such, so a restarting container cannot deepen
    the hole it is in.
  - Retry attempts are reported through stamina's instrumentation, which uses structlog when
    it is installed (see [ADR-001](#adr-001-use-structlog-for-logging)).

- Costs / Trade-offs
  - Adds a runtime dependency on stamina (and its tenacity dependency).
  - Terminal non-rate-limit failures (bad token, revoked access) cost three attempts.
  - Worst case a load takes about 10 seconds longer per failing call than it used to.
  - The timeout bounds the scheduling of retries, not the duration of any single call. The
    SDK exposes no request timeout, so a request that hangs rather than fails still hangs;
    bounding that would require wrapping the whole load in an `asyncio.timeout`, which is a
    separate decision about whether a load may abort an in-flight request.
  - The request count logged on a successful load counts logical requests, not retried
    attempts, so it under-reports when a retry occurred.

- Operational considerations
  - Retries multiply with the container restart policy; a bounded restart count remains
    necessary to keep a persistent failure from burning quota.
  - The retry budget is deliberately tied to deployment timeouts; revisit it if those change.

- Developer impact
  - No change to the `load_config` signature or to schema definitions.
  - Tests that exercise failure paths should use `stamina.set_testing()` so retries do not
    add backoff waits to the suite.

## ADR-014: Split failures into unavailable and invalid

**Date:** 2026-08-28

**Context:**

`load_config` raised a bare `RuntimeError` for every failure, so a caller could not tell an
outage apart from a misconfiguration without matching on the exception message. That
distinction is not academic: a service that keeps a last-good config snapshot wants to boot
from it when 1Password is unreachable, but must fail loudly when someone has edited the vault
item wrong — serving stale config over an unfixed error is worse than not starting.

The assetlife-api fallback (UT-9201) shipped an interim classifier that matched on Configator's
message strings (`vault '...' not found`, `the dwarves delved too greedily and too deep`, and
three others). That is fragile — rewording a log message silently flips a production start from
"fall back" to "crash", or the other way — and every other consumer wanting the same behaviour
has to copy the same string table.

**Decision:**

Introduce a three-type hierarchy in `configator.errors`, exported from the package root:

- `ConfigatorError(Exception)` — base, so one `except` catches every typed configuration-loading
  failure. The developer-mode production guard is deliberately not one of them; see below.
- `ConfigUnavailableError` — 1Password could not be reached or would not answer: auth failure,
  network or TLS error, `RateLimitExceededException`, an empty vault or item listing, and
  reference resolution that fails for transport reasons.
- `ConfigInvalidError` — the item was read but does not fit the schema: a field with no value
  and no default, a value that will not construct its annotated type, a `JSONDecodeError`,
  Pydantic's `ValidationError`, and the `_MAX_REFERENCE_DEPTH` guard.

Where a failure originates in an underlying exception it is chained with `raise ... from`, so the
message and traceback survive. Failures Configator detects itself — a vault or item absent from a
listing, a required field with no value, a reference the response omits, the depth guard — have no
`__cause__`, so a consumer reading it must treat it as optional. A single helper,
`_call_1password`, wraps each SDK await in `load_config` and
`_resolve_references`; since the SDK collapses auth, network and TLS failures into a bare
`Exception` (see [ADR-013](#adr-013-retry-1password-calls-but-never-a-rate-limit)), anything
escaping a retried call is by construction a failure to reach 1Password rather than a statement
about the config it holds.

An empty vault or item listing is classified as unavailable rather than invalid because a
de-permissioned or rotated service-account token is indistinguishable from a vault that is not
there, and the safe reading of that ambiguity is the one that does not crash a healthy service.

The developer-mode production guard in `models.py` keeps raising a plain `RuntimeError`: it is a
refusal to start, not a report about the config item, and folding it into `ConfigInvalidError`
would invite a caller to catch and handle it.

**Consequences:**

- Benefits
  - Consumers branch on a type instead of a message; rewording a log line can no longer change
    production start-up behaviour.
  - The assetlife-api string table can be deleted in favour of `except ConfigUnavailableError`.
  - Pydantic's `ValidationError` is wrapped, so a caller needs one `except` clause, not two.
  - Chaining preserves the underlying diagnostic for logs and error reporting.

- Costs / Trade-offs
  - `ConfigatorError` derives from `Exception`, not `RuntimeError`, so a caller catching
    `RuntimeError` specifically stops catching Configator failures. This is a breaking change
    for such callers and warrants a minor version bump; code catching broad `Exception` is
    unaffected.
  - The unavailable/invalid split is a judgement call at the boundary. A reference pointing at a
    vault that does not exist is a config error in spirit but reported as unavailable, because
    the SDK cannot distinguish it from a permissions problem.
  - Two extra public names on an API surface [ADR-009](#adr-009-provide-minimal-public-api-surface)
    deliberately keeps small.

- Operational considerations
  - A consumer booting from a snapshot on `ConfigUnavailableError` should log loudly and alert;
    a silent fallback that persists is how stale config reaches production unnoticed.

- Developer impact
  - No change to the `load_config` signature or to schema definitions.
  - Tests asserting on failure paths assert on the exception type rather than the message.
