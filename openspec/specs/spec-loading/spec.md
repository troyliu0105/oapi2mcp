## Purpose

Handles loading OpenAPI specs from remote URLs or local files, resolving `$ref` references, extracting operations, and inferring base URLs.

## Requirements

### Requirement: Load spec from remote URL
The system SHALL load an OpenAPI spec from a remote HTTP/HTTPS URL using `httpx`.

#### Scenario: Successful remote load
- **WHEN** a valid HTTP(S) URL is provided as the spec source
- **THEN** the system SHALL download the JSON content and return it as a parsed dictionary

#### Scenario: Remote URL returns non-200
- **WHEN** the remote URL returns a non-200 status code
- **THEN** the system SHALL raise an error with the status code and URL

#### Scenario: Remote URL is unreachable
- **WHEN** the remote URL cannot be reached (connection error, timeout)
- **THEN** the system SHALL raise an error describing the connection failure

### Requirement: Load spec from local file
The system SHALL load an OpenAPI spec from a local file path.

#### Scenario: Successful local load
- **WHEN** a valid local file path is provided as the spec source
- **THEN** the system SHALL read the file and return it as a parsed dictionary

#### Scenario: Local file not found
- **WHEN** the specified local file does not exist
- **THEN** the system SHALL raise a `FileNotFoundError`

### Requirement: Resolve $ref references
The system SHALL recursively resolve all `$ref` references in the spec against `#/components/schemas/`.

#### Scenario: Simple $ref resolution
- **WHEN** a schema contains `{"$ref": "#/components/schemas/Pet"}`
- **THEN** the system SHALL replace it with the actual `Pet` schema object from `components.schemas`

#### Scenario: Nested $ref resolution
- **WHEN** a resolved schema itself contains `$ref` references
- **THEN** the system SHALL resolve those recursively until no `$ref` remains

#### Scenario: Unresolvable $ref
- **WHEN** a `$ref` points to a path that does not exist in the spec
- **THEN** the system SHALL leave the `$ref` as-is

### Requirement: Extract operations
The system SHALL extract all operations from the spec's `paths` object as a list of `Operation` dataclass instances.

#### Scenario: Standard extraction
- **WHEN** the spec contains paths with `get`, `post`, `put`, `patch`, `delete` methods
- **THEN** each method entry SHALL produce one `Operation` with `method`, `path`, `operationId`, `summary`, `description`, `parameters`, `request_body_schema`, and `responses`

#### Scenario: Missing operationId
- **WHEN** an operation does not have an `operationId`
- **THEN** the system SHALL generate one from the method and path (e.g., `get_users_id`)

### Requirement: Infer base URL from spec source
The system SHALL infer the base URL when the spec is loaded from a remote URL by stripping the last path segment.

#### Scenario: URL with path segment
- **WHEN** the spec source is `http://127.0.0.1:3000/openapi.json`
- **THEN** the inferred base URL SHALL be `http://127.0.0.1:3000`

#### Scenario: URL with nested path
- **WHEN** the spec source is `https://api.example.com/v2/spec.json`
- **THEN** the inferred base URL SHALL be `https://api.example.com/v2`

#### Scenario: Local file source
- **WHEN** the spec source is a local file path
- **THEN** no base URL SHALL be inferred (returns `None`)
