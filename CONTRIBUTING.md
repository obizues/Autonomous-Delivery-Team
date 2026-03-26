# Contributing Standards and Practices

## Import Conventions
- Place all imports at the top of each file.
- Use absolute imports for package modules (e.g., `from ai_software_factory.module import ...`).
- Use local imports for scripts within the same directory (e.g., `from config import ...`).
- Avoid circular imports by structuring code so dependencies flow one way.

## Module Organization
- Group related functions/classes into clear modules (e.g., config, models, utils).
- Keep each module focused—avoid mixing unrelated logic.
- Separate services and utilities for clarity and maintainability.

## Linting and Type Checks
- Use flake8, pylint, and mypy to catch undefined names, import errors, and indentation issues.
- Add pre-commit hooks to enforce linting and type checks before code is committed.

## Testing
- Write unit tests for each module and integration tests for workflows.
- Run tests automatically in CI/CD to catch errors early.

## Documentation
- Document import conventions and module structure in README and CONTRIBUTING.md.
- Provide examples for launching scripts and running tests.

## Code Review
- Require code review for all changes, focusing on import style, module boundaries, and error handling.

## Automated Checks
- Use tools like pytest, flake8, and mypy in CI to block merges with errors.

---

## Example Pre-commit Hook Setup
1. Install pre-commit:
   ```bash
   pip install pre-commit
   ```
2. Create `.pre-commit-config.yaml`:
   ```yaml
   repos:
     - repo: https://github.com/pycqa/flake8
       hooks:
         - id: flake8
     - repo: https://github.com/pre-commit/mirrors-mypy
       hooks:
         - id: mypy
   ```
3. Install hooks:
   ```bash
   pre-commit install
   ```

---

## Example Lint Command
```bash
flake8 .
pylint src/
mypy src/
```

---

## Example Test Command
```bash
pytest
```

---

## Launching Scripts
- Always activate the virtual environment before running scripts.
- Launch UI scripts from the `ui` directory for correct import resolution.
- Set `PYTHONPATH` as needed for package imports.

---

## Error Prevention Checklist
- Imports at top, correct style
- No circular dependencies
- All names defined and imported
- Consistent indentation
- Lint and type checks pass
- Tests pass
- Code reviewed

---

For questions or improvements, open an issue or pull request.
