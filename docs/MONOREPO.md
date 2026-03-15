# Monorepo Structure

## Layout

```text
.
|-- apps/
|   `-- web/
|-- docs/
|   |-- ARCHITECTURE.md
|   |-- MONOREPO.md
|   `-- PRD.md
|-- packages/
|   `-- shared/
|-- services/
|   |-- api/
|   `-- workers/
|-- package.json
|-- pnpm-workspace.yaml
|-- README.md
|-- ROADMAP.md
`-- TODO.md
```

## Intent

- `apps/web`: user-facing editor and dashboard
- `services/api`: main backend API
- `services/workers`: background processing
- `packages/shared`: shared schemas and contracts

## Next Technical Step

Bootstrap:

- Next.js in `apps/web`
- FastAPI in `services/api`
- Celery worker package in `services/workers`
- shared TypeScript and JSON schema definitions in `packages/shared`
