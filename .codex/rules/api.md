# API Rules

**Scope:** `src/app/api/**`

All APIs must comply with the following requirements:

- Use DTOs as request and response models.
- Never return entities directly.
- Use a consistent response envelope:

  ```json
  {
    "success": true,
    "data": {},
    "error": null
  }
  ```
