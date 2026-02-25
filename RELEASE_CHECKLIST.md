# Release Checklist

Use this for every Python SDK release.

## Pre-release

- Install dev dependencies: `python3 -m pip install -e ".[dev]"`
- Run tests: `pytest -q`
- Build artifacts: `python3 -m build`
- Validate package metadata/artifacts: `python3 -m twine check dist/*`
- Confirm README examples still match API behavior.

## Release

- Commit changes on `main`.
- Bump version in `pyproject.toml`.
- Create tag: `git tag vX.Y.Z`
- Push main branch.
- Push tag: `git push origin vX.Y.Z`
- Publish to PyPI: `python3 -m twine upload dist/*`

## Post-release

- Verify install from clean folder:
  - `python3 -m pip install cronbeats-python==X.Y.Z`
- Run a quick import + ping call smoke test.
