# Coding Style & File Header Templates

## File Header Templates

### Python (`.py`)

Every Python source file must start with a module docstring:

```python
"""QLive — <Module description>.

<Optional: one or two sentences about what this module provides.>
"""

from __future__ import annotations

...
```

**`__init__.py`** (package root — keep minimal):

```python
"""QLive — <Package description>."""

__version__ = "0.1.0"
```

**Test files** (`tests/python/test_<module>.py`):

```python
"""Tests for QLive <module>."""

import pytest

from qlive.<module> import ...
```

---

### TypeScript / React (`.ts`, `.tsx`)

Every file starts with JSDoc comment describing the module/component:

```typescript
/**
 * QLive — <Component or module description>.
 *
 * <Optional: behaviour, rendering conditions, state notes.>
 */

import ... from "...";
...
```

**Test files** (`*.test.ts`, `*.test.tsx`):

```typescript
/**
 * Tests for <Component / module>.
 */

import { describe, it, expect } from "vitest";
...
```

---

### Java (`.java`)

```java
/**
 * QLive — <Class description>.
 */
package com.qortal.qlive.<package>;

...
```

---

## Style Rules

### Python
- **Format:** `black` with line-length 100 (`pyproject.toml`).
- **Lint:** `ruff` with select groups `E, F, W, I, N, UP, B, SIM, C4`.
- **Types:** Use `from __future__ import annotations` and full type hints everywhere.
- **Docstrings:** Google/NumPy style is acceptable; minimum = one-line module + one-line class/method.
- **Imports:** Group: stdlib → third-party → project-local. Sort with `ruff` (isort rules).
- **Constants:** `UPPER_SNAKE_CASE` for protocol constants.
- **Classes:** `PascalCase`.
- **Functions/Methods:** `snake_case`.
- **Exceptions:** `<Meaning>Error` suffix, inherit from a base `QLiveError` or appropriate module-level base.
- **Dataclasses:** Prefer `@dataclass` over hand-written `__init__`.

### TypeScript / React
- **Format:** Prettier with project config.
- **Lint:** ESLint with TypeScript plugin.
- **Types:** Prefer `interface` over `type` for object shapes; use `type` for unions/intersections.
- **Components:** PascalCase, functional components only (no class components).
- **Exports:** Default export for page components; named exports for utilities.
- **Imports:** Group: third-party → project-relative. Sort with `import/order` ESLint rule.
- **Props:** Define as `interface <ComponentName>Props`.

### Java
- **Style:** Google Java Style Guide.
- **Build:** Maven (`pom.xml` at `src/java/pom.xml`).

### General
- Keep functions under ~50 lines where possible.
- One logical change per commit; use Conventional Commits (`feat:`, `fix:`, `docs:`, etc.).
- **Never commit** secrets, credentials, or private keys.
- API keys and node addresses go into `.env` files (see `.gitignore`).
