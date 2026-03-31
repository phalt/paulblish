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
2. Make your changes.
3. Run `make format` to format code.
4. Run `make lint` to check for issues.
5. Run `make test` to run the test suite.
6. Open a pull request against `main`.

## Code Style

This project uses `ruff` for linting and formatting, configured in `pyproject.toml`. Run `make format` before committing.
