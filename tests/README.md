# QLive Tests

Test suites for the QLive decentralized live-streaming protocol.

## Structure

```
tests/
└── python/          # Python test suites (pytest)
```

JavaScript/TypeScript tests live alongside the source:

```
src/js/src/**/*.test.{ts,tsx}   # Vitest unit tests
src/js/e2e/                     # Playwright end-to-end tests
```

Java tests are not yet present (the Java project is a skeleton).

## Running Tests

### Python
```bash
cd src/python
pytest
```

### JavaScript/TypeScript (unit)
```bash
cd src/js
npm test
```

### JavaScript/TypeScript (end-to-end)
```bash
cd src/js
npx playwright install
npm run test:e2e
```

## Coverage

Coverage reports are generated per-language and should not be committed (see `.gitignore`).