# Contributing to VoxChart

Thanks for your interest in contributing! This guide covers everything you need to get started.

---

## Dev Setup

### Prerequisites
- Python 3.10+
- NVIDIA GPU with CUDA (recommended) or CPU-only
- Ubuntu / WSL2 / macOS (Windows native supported)

### Install

```bash
git clone https://github.com/nathan-wilkins95/VoxChart.git
cd VoxChart
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### First Run

```bash
python app.py
```

The onboarding wizard runs on first launch and writes `config.json`.

---

## Running Tests

All tests live in `tests/`. Run the full suite with:

```bash
python -m pytest tests/ -v
```

Or run a specific file:

```bash
python -m pytest tests/test_updater.py -v
python -m pytest tests/test_dictation_engine.py -v
```

Tests are plain `unittest` and also discoverable via `python -m unittest discover tests`.

---

## Branching Strategy

| Branch | Purpose |
|---|---|
| `main` | Stable releases only |
| `dev` | Active development |
| `feature/<name>` | Individual features |
| `fix/<name>` | Bug fixes |

Always branch from `main` for fixes, `dev` for features.

---

## Pull Request Process

1. Fork the repo and create your branch from `main` or `dev`.
2. Make your changes with clear, focused commits.
3. Add or update tests in `tests/` for any logic you change.
4. Run `pytest tests/ -v` and confirm all tests pass.
5. Open a PR against `main` (bugfix) or `dev` (feature).
6. Fill in the PR template — describe what changed and why.
7. A maintainer will review and merge.

---

## Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/).
- Keep functions small and single-purpose.
- Docstrings on all public functions and classes.
- Use `logging` (never `print`) for runtime output.
- No secrets, credentials, or patient data in commits.

---

## Reporting Bugs

Use the in-app **Report Bug** button (top bar) to capture logs automatically, or open a [GitHub Issue](https://github.com/nathan-wilkins95/VoxChart/issues) with:
- VoxChart version (`Help > About`)
- OS and Python version
- Steps to reproduce
- Relevant log lines from `logs/`

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
