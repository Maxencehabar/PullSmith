# Repository Guidelines

## Project Structure & Module Organization
- Keep runtime code in `src/` and mirror folders by feature or domain.
- Place automated tests in `tests/` matching the `src/` structure; share fixtures under `tests/fixtures/`.
- Use `scripts/` for developer utilities (setup, lint, format, release), and `docs/` for reference material.
- Store static assets in `assets/` or `public/`, and keep modules small with clear dependencies to ease testing.

## Build, Test, and Development Commands
- Add or update a top-level `Makefile` or `package.json` scripts so new contributors can run:
  - `make setup` or `npm install` to install dependencies.
  - `make test` or `npm test` for the full suite.
  - `make lint` / `npm run lint` and `make format` / `npm run format` to enforce style.
  - `make dev` or `npm run dev` to start the local server/CLI loop.
- Document any service emulators or required background processes in `docs/` and reference them from the README.

## Coding Style & Naming Conventions
- Default to 2-space indentation and keep lines ≤100 characters unless language tooling disagrees.
- Prefer `kebab-case` for directories/files, `camelCase` for variables/functions, and `PascalCase` for types/classes.
- Use an auto-formatter (e.g., Prettier, Black, gofmt) appropriate to the language; surface it via `make format`.
- Run linting before pushing; treat warnings as errors in CI once configured.

## Testing Guidelines
- Mirror `src/` paths inside `tests/` and name files `*.spec.*` or `*_test.*` per ecosystem norms.
- Favor table-driven cases to cover edge conditions; keep fixtures deterministic and versioned.
- Target ≥80% coverage once a coverage tool is configured; avoid flakiness and long-running tests.
- For integration flows, document setup/teardown steps alongside the test or in `docs/`.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat: ...`, `fix: ...`, `chore: ...`); keep subjects ≤72 characters.
- Each PR should include a short summary, rationale, and test notes (e.g., `make test`, `make lint` outputs).
- Link related issues (`#123`) and add screenshots for UI-facing changes.
- Keep changes small and focused; prefer multiple PRs over one large one.

## Security & Configuration Tips
- Never commit secrets; track required variables in `.env.example` and load via a local `.env`.
- Add `.gitignore` entries for local tooling output and secret files.
- Prefer least-privilege credentials; rotate tokens used for local development regularly.
