# QLive Tests

Test suites for the QLive decentralized live-streaming protocol.

## Structure

```
tests/
├── python/          # Python test suites (pytest)
├── js/              # JavaScript/TypeScript test suites (Jest/Vitest)
├── java/            # Java test suites (JUnit)
└── integration/     # Cross-language integration tests
```

## Running Tests

### Python
```bash
cd src/python
pytest
```

### JavaScript/TypeScript
```bash
cd src/js
npm test
```

### Java
```bash
cd src/java
mvn test
```

### Integration
```bash
# Cross-language integration tests (TBD)
```

## Coverage

Coverage reports are generated per-language and should not be committed (see `.gitignore`).