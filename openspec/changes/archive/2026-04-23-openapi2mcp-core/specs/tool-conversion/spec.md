## ADDED Requirements

### Requirement: Convert operation to MCP tool
The system SHALL convert each `Operation` into an MCP `types.Tool` with `name`, `description`, and `inputSchema`.

#### Scenario: Operation with full metadata
- **WHEN** an operation has `operationId`, `summary`, and `description`
- **THEN** the tool name SHALL be the `operationId`, and the description SHALL be `summary` (preferred) or `description`

#### Scenario: Operation with no summary or description
- **WHEN** an operation has neither `summary` nor `description`
- **THEN** the tool description SHALL be the fallback string `"{METHOD} {path}"` (e.g., `"POST /classifier/occlusion"`)

### Requirement: Build input schema from parameters
The system SHALL build a single JSON Schema `inputSchema` by merging path, query, header parameters and request body properties into one object.

#### Scenario: Path parameters only
- **WHEN** an operation has path parameters (e.g., `/users/{id}`)
- **THEN** each path parameter SHALL become a top-level property in `inputSchema` with its `required` flag preserved

#### Scenario: Mixed parameter types
- **WHEN** an operation has path, query, and body parameters
- **THEN** all SHALL be merged into top-level `properties`, and `required` SHALL be the union of all required parameters

#### Scenario: Request body flattening
- **WHEN** an operation has a JSON request body with properties
- **THEN** the body's top-level properties SHALL be merged into the `inputSchema` properties

### Requirement: Detect and resolve parameter name collisions
The system SHALL detect when a body property name conflicts with a path, query, or header parameter name and rename the body property.

#### Scenario: Body property collides with path parameter
- **WHEN** a path parameter named `id` exists and the request body also has a property named `id`
- **THEN** the body's `id` SHALL be renamed to `id_body` in the `inputSchema`

#### Scenario: No collision
- **WHEN** all parameter names are unique across path, query, header, and body
- **THEN** no renaming SHALL occur

#### Scenario: Operation with no parameters
- **WHEN** an operation has no path, query, header, or body parameters
- **THEN** the `inputSchema` SHALL be `{"type": "object", "properties": {}}`
