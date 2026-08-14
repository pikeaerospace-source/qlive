# Contributing to QLive

Thank you for your interest in contributing to QLive! This project is in its early design phase, and contributions are welcome across protocol design, implementation, documentation, and testing.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)
- [Design Discussions](#design-discussions)

---

## Code of Conduct

Be respectful, constructive, and inclusive. This project welcomes contributors of all backgrounds and experience levels. Harassment, discrimination, or toxic behavior will not be tolerated.

---

## How to Contribute

### 1. Design & Specification
QLive is in active design. The [TODO.md](TODO.md) contains open design questions and research tasks. You can contribute by:

- Answering open design questions in issues/discussions
- Writing protocol specification documents in `docs/`
- Researching technical topics (Reticulum, WebRTC, CMAF, QDN APIs, etc.)
- Reviewing and critiquing the architecture

### 2. Code
Once implementation begins, contributions are welcome across:

- **Python** — backend services, protocol implementation
- **JavaScript/TypeScript** — web player, CLI tools, broadcaster app
- **Java** — Qortal Core integration

### 3. Documentation
- Improving README, TODO, or docs
- Writing tutorials and guides
- Translating documentation

### 4. Testing
- Writing unit/integration tests
- Manual testing of the reference implementation
- Performance benchmarking

---

## Development Setup

> **Note:** The project is in design phase. This section will be expanded as code lands.

### Prerequisites
- Git
- Node.js 18+ (for JS tooling)
- Python 3.10+ (for Python tooling)
- Java 17+ (for Qortal Core integration)
- FFmpeg (for media processing)

### Clone & Setup

```bash
git clone git@github.com:pikeaerospace-source/qlive.git
cd qlive
```

---

## Project Structure

```
qlive/
├── docs/               # Protocol specs, design docs, research notes
├── src/                # Source code (organized by language/component)
│   ├── python/         # Python components
│   ├── js/             # JavaScript/TypeScript components
│   └── java/           # Java components (Qortal Core integration)
├── tests/              # Test suites
├── README.md           # Project overview
├── TODO.md             # Task tracking & planning
├── CONTRIBUTING.md     # This file
├── SECURITY.md         # Security policy
├── CHANGELOG.md        # Version history
├── AUTHORS.md          # Contributors
└── LICENSE.md          # MIT License
```

---

## Coding Standards

### General
- Write clear, self-documenting code
- Include docstrings/comments for non-obvious logic
- Keep functions small and focused
- Follow the language's idiomatic style

### Python
- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use type hints
- Format with `black` and lint with `ruff`

### JavaScript/TypeScript
- Use ESLint with the project config
- Prefer TypeScript for new code
- Use Prettier for formatting

### Java
- Follow [Google Java Style Guide](https://google.github.io/styleguide/javaguide.html)
- Use Maven or Gradle conventions

---

## Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

### Types
- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation only
- `style` — formatting, no code change
- `refactor` — code change that neither fixes a bug nor adds a feature
- `perf` — performance improvement
- `test` — adding/updating tests
- `build` — build system or dependencies
- `ci` — CI configuration
- `chore` — other changes

### Examples
```
feat(transport): add CMAF chunk signing
fix(swarm): handle parent node drop in mesh fallback
docs(readme): update architecture diagram
test(buffer): add sliding-window eviction tests
```

---

## Pull Request Process

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make your changes** following the coding standards.

3. **Write tests** for new functionality.

4. **Run tests** and ensure they pass.

5. **Commit** with a clear conventional commit message.

6. **Push** and open a pull request:
   ```bash
   git push origin feat/my-feature
   ```

7. **Describe your changes** in the PR description:
   - What changed and why
   - Any design decisions or tradeoffs
   - Related issues/PRs

8. **Address review feedback** — maintainers may request changes.

---

## Reporting Issues

When reporting a bug or issue, please include:

- **Description** — what happened vs. what you expected
- **Steps to reproduce**
- **Environment** — OS, versions, node type
- **Logs/screenshots** if applicable
- **Proposed fix** if you have one

Use the issue templates if available.

---

## Design Discussions

For design questions and architectural decisions:

- Check [TODO.md](TODO.md) → **Open Design Questions** section
- Open a discussion or issue tagged `design`
- Reference the relevant TODO item

Major design decisions should be documented in `docs/` and reflected in the TODO.md **Notes & Decisions Log**.

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE.md).

---

*Thank you for helping build QLive — live streaming that belongs to the network, not the platform.*