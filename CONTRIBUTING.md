# Contributing to Paulblish

Thanks for your interest in contributing!

## Setup

```bash
git clone https://github.com/phalt/paulblish.git
cd paulblish
make install
```

## Development Workflow

1. Create a branch for your change.
2. Make your changes — **every implementation change must include tests**.
3. Run `make format` to format code.
4. Run `make lint` to check for issues.
5. Run `make test` to run the test suite — all tests must pass.
6. Open a pull request against `main`.

## Code Style

- `ruff` for linting and formatting, configured in `pyproject.toml`. Run `make format` before committing.
- Line length: 120. Target: Python 3.13+.
- Package layout: flat `paulblish/` at repo root (not `src/`).
- Dependencies managed with `uv`. Commit `uv.lock`.

## Testing

Tests live in `tests/` and use `pytest`. Fixtures are in `tests/fixtures/`.

```bash
make test             # run the full suite
uv run pytest tests/test_foo.py  # run a single file
```

Do not open a PR with untested code. If a change is hard to unit test, explain why in the PR description.

## Project Conventions

See [CLAUDE.md](CLAUDE.md) for the full set of conventions used in this project.
