# Data Pipeline (Seed Repo)

This repository is a deterministic seed project for Repo Mode testing.

Current behavior intentionally leaves gaps:
- no strict schema validation for required fields
- no duplicate record detection
- no dead-letter routing for invalid rows

Tests currently pass, but they do not yet cover these missing behaviors.
