---
name: document-feature
description: Create or update English domain documentation for a feature, including applicable API, schema, and design details.
---

## Feature Documentation

- For every feature, create or update English documentation in `docs/domains/<domain>/` in the same change as the implementation. Keep it accurate as the feature evolves.
- Maintain `apis.md` for affected APIs using the endpoint format below.
- Maintain `db-schemas.md` for affected database structures: describe tables and their purpose, columns (types, nullability, defaults, constraints, and descriptions), indexes, foreign keys, relationships, and meaningful enum or status values.
- Maintain `context-designs.md` for affected domain designs: describe the responsibilities and interfaces of repositories and services, including method signatures, and document entity fields, types, and meanings.
-  ⚠️**IMPORTANT**: Before editing an existing document, read it in full and locate where it already covers the affected behavior. Limit edits to content affected by the feature and integrate changes into the existing sections, endpoint entries, and tables where they belong. After editing, review the full document for duplicated sections, endpoint entries, or descriptions of the same behavior.
- If the feature has an execution plan, record review status, approvals, and implementation progress there.


## Examples

New and updated domain documents must follow the structure and formatting of the applicable examples below, including headings, tables, and code blocks. Include sections only when applicable to the feature; add details when needed to meet the requirements above. These examples describe a fictional user domain, not implemented endpoints or tables. Use consistent identifiers and types across API, schema, and domain documentation.

### API example (`apis.md`)

Document each endpoint in this order. Start with the title, purpose, and method and URI. Then document any path parameters, query parameters, and request body. For query parameters, give the type, whether the parameter is required, its default, and an example URI with the query string. For a request body, include the content type, field types, required fields, defaults, and an example. Next describe the success status and what the response contains, then show a response example. Link to an existing response example when the body is identical. End with a representative error response and a table mapping endpoint errors to HTTP statuses, error codes, and meanings. Document shared middleware errors once when they apply across endpoints.

#### List users

List users ordered by username, optionally filtered by account status. Authentication is required.

`GET /api/v1/users/`

| Query parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `is_active` | boolean | No | None | Use `true` for active users or `false` for inactive users. Omit to include both. |
| `limit` | integer | No | `20` | Maximum number of users to return, from `1` through `100`. |

Example request with query parameters.

`GET /api/v1/users/?is_active=true&limit=10`

Response `200 OK` returns an array of matching users. If no users match, the array is empty.

```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "username": "alice",
    "is_active": true
  }
]
```

Example error response for a query with `limit=0`.

```json
{"error": "invalid_query"}
```

| Status | Error code | Meaning |
| --- | --- | --- |
| `400 Bad Request` | `invalid_query` | A query parameter has an invalid value. |

#### Update a user

Update the username of a user identified by UUID. Authentication is required.

`PATCH /api/v1/users/{id}/`

| Path parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | UUID | Yes | User identifier. |

Send an `application/json` object with the following field.

| Field | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `username` | string | Yes | None | New username. |

```json
{"username": "alice"}
```

Response `200 OK` returns the updated user.

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "username": "alice"
}
```

Example error response when the UUID does not identify a user.

```json
{"error": "user_not_found"}
```

| Status | Error code | Meaning |
| --- | --- | --- |
| `400 Bad Request` | `invalid_request` | The request body is malformed or the username is missing or invalid. |
| `404 Not Found` | `user_not_found` | No user exists with the supplied UUID. |
| `415 Unsupported Media Type` | `unsupported_media_type` | The content type is other than `application/json`. |

### Database example (`db-schemas.md`)

The `users` table stores basic user information.

| Column | Type | Nullable | Default | Constraints | Description |
| --- | --- | --- | --- | --- | --- |
| `id` | UUID | No | Generated UUID | Primary key | User identifier. |
| `username` | VARCHAR(150) | No | None | Unique | User name. |
| `is_active` | BOOLEAN | No | `true` | None | Account status. |

| Index | Columns | Type | Purpose |
| --- | --- | --- | --- |
| `users_pkey` | `id` | Primary key | Identifies a user. |
| `users_username_key` | `username` | Unique | Prevents duplicate names. |

Document foreign keys, relationships, and enum values when applicable.

### Domain design example (`context-designs.md`)

`UserRepository` persists and retrieves users; `UserService` coordinates user operations.

```python
class UserRepository:
    def get_user_by_id(self, user_id: UUID) -> User | None: ...

class UserService:
    def get_user_by_id(self, user_id: UUID) -> UserDTO | None: ...
```

The `User` entity represents an account:

| Field | Type | Description |
| --- | --- | --- |
| `id` | `UUID` | User identifier. |
| `username` | `str` | User name. |
| `is_active` | `bool` | Whether the account is active. |
