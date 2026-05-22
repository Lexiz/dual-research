.PHONY: stable-worktree test-js

stable-worktree:
	@./scripts/setup-stable-worktree.sh

# Spec 0161 — run the JS test suite (Pages Function + dashboard-bootstrap.js).
# Python tests stay on `uv run pytest tests/ -q`; this target is opt-in and
# installs devDependencies on first run. Re-runs are fast (npm install no-ops
# when node_modules is up to date).
test-js:
	@npm install --no-audit --no-fund && npm test
