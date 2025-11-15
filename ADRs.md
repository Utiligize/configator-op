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
  - Performance: Each reference resolution is an SDK call (network latency).
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
  - Developer mode should never be enabled in production environments.
  - Teams should document when and how to use developer mode in development guides.
  - .env file format must match pydantic-settings expectations (KEY=value).

- Developer impact
  - Convenient local development: Test configuration changes without 1Password access.
  - Clear mode switching: Single environment variable controls behavior.
  - Must understand priority: Know which source wins in each mode.
  - Explicit opt-in: Developer mode must be deliberately enabled.
  - Standard patterns: Follows familiar .env file conventions from other frameworks.
