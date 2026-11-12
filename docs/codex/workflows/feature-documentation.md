## Feature Documentation

- For every feature, create or update English documentation in `docs/domains/<domain>/` in the same change as the implementation. Keep it accurate as the feature evolves.
- Maintain `apis.md` for affected APIs: describe each endpoint and purpose, HTTP method and path, parameters and request body (types, required fields, and defaults), and example requests and responses with status codes.
- Maintain `db-schemas.md` for affected database structures: describe tables and their purpose, columns (types, nullability, defaults, constraints, and descriptions), indexes, foreign keys, relationships, and meaningful enum or status values.
- Maintain `context-designs.md` for affected domain designs: describe the responsibilities and interfaces of repositories and services, including method signatures, and document entity fields, types, and meanings.
- Document each applicable area; when a feature does not affect an area, do not invent APIs, database structures, or components. Update existing domain documents instead of duplicating them.

