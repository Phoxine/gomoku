# Security Rules

- Never read, print, or commit `.env`, `*.pem`, `*.key`, or credential files.
- Never write API keys, tokens, or passwords into source code.
- Validate all external input.
- Never log passwords, tokens, national identification numbers, or credit card numbers.

## SQL queries

Use the Django ORM for database access. When an operation requires explicit SQL, use fixed query text and bind data values separately through the database API. Never construct SQL with string interpolation, formatting, or concatenation.
