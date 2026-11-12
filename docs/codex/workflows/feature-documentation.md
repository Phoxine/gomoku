## Feature Documentation

- For every feature, create or update English documentation in `docs/domains/<domain>/` in the same change as the implementation. Keep it accurate as the feature evolves.
- Maintain `apis.md` for affected APIs: describe each endpoint and purpose, HTTP method and path, parameters and request body (types, required fields, and defaults), and example requests and responses with status codes.
- Maintain `db-schemas.md` for affected database structures: describe tables and their purpose, columns (types, nullability, defaults, constraints, and descriptions), indexes, foreign keys, relationships, and meaningful enum or status values.
- Maintain `context-designs.md` for affected domain designs: describe the responsibilities and interfaces of repositories and services, including method signatures, and document entity fields, types, and meanings.
- Document each applicable area; when a feature does not affect an area, do not invent APIs, database structures, or components. Update existing domain documents instead of duplicating them.


## Examples

The examples below illustrate documentation format for a fictional user domain. Adapt them to the actual feature; they do not describe implemented endpoints or tables. Use consistent identifiers and types across API, schema, and domain documentation.

### API example (`apis.md`)

#### Get user detail

Return a user by ID. Authentication is required.

`GET /api/v1/users/{id}/`

| Path parameter | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | UUID | Yes | User identifier. |

Example request: `GET /api/v1/users/123e4567-e89b-12d3-a456-426614174000/`

Response `200 OK`:

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "username": "alice"
}
```

Response `404 Not Found`:

```json
{"detail": "Not found."}
```

For endpoints with a request body or query parameters, include their types, required fields, defaults, and an example request as well.

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
