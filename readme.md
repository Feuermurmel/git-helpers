# git-helpers

## Development

### Setup

The project uses [pre-commit](https://pre-commit.com) to run source code formatters and
type checking before commit. A Makefile target is provided to create a virtualenv ready
for development:

```shell
pre-commit install
make venv
. venv/bin/activate
```

### Tests

Unit test can be run using [pytest](https://docs.pytest.org/en/stable/):

```bash
pytest
```

### Type Checking

Type checking can be run using [mypy](https://github.com/python/mypy):

```bash
mypy
```
