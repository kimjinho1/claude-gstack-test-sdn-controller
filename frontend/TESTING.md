# Testing

100% test coverage is the key to great vibe coding. Tests let you move fast, trust your instincts, and ship with confidence — without them, vibe coding is just yolo coding. With tests, it's a superpower.

## Framework

**Vitest v3** + **@testing-library/vue** + **jsdom**

## Run tests

```bash
cd frontend
npm test          # run once
npm run test:watch  # watch mode
```

Test files live in `src/__tests__/` and match `*.test.ts`.

## Test layers

- **Unit tests** — pure functions, utilities, computed logic (`src/__tests__/`)
- **Component tests** — Vue components with @testing-library/vue (render, interact, assert)
- **Integration tests** — Pinia stores with mocked API responses

## Conventions

- Files: `src/__tests__/<subject>.test.ts`
- Assertions: use `expect` with meaningful matchers — never `toBeDefined()` alone
- Mock external deps (API calls, stores) in component tests
- One describe block per file; group related cases with `it(...)`
