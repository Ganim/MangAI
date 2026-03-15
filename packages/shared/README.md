# Shared Package

Shared runtime contracts for MangAI.

This package now contains:

- schema version constant
- enums
- locale and language helpers
- entity validators
- API request validators
- worker payload and result validators

The initial implementation avoids external dependencies so the contract layer stays lightweight and easy to adopt across the monorepo.
