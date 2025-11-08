# Required GitHub Actions Workflow Updates

Due to permission restrictions, the following workflow files need to be manually updated. These changes fix critical issues with version bumping and test coverage.

## Files to Update

1. `.github/workflows/ci.yml`
2. `.github/workflows/publish.yml`
3. `.github/workflows/release.yml`

## Changes for `.github/workflows/ci.yml`

### Change 1: Fix test coverage path (Line 94)

**Before:**
```yaml
      - name: Run tests
        run: |
          uv run pytest tests/ -v --cov=quickhooks --cov-report=xml --cov-report=term-missing
```

**After:**
```yaml
      - name: Run tests
        run: |
          uv run pytest tests/ -v --cov=src/quickhooks --cov-report=xml --cov-report=term-missing
```

## Changes for `.github/workflows/publish.yml`

### Change 1: Fix test coverage path (Line 40)

**Before:**
```yaml
      - name: Run full test suite
        run: |
          uv run pytest tests/ -v --cov=quickhooks --cov-fail-under=80
```

**After:**
```yaml
      - name: Run full test suite
        run: |
          uv run pytest tests/ -v --cov=src/quickhooks --cov-fail-under=80
```

## Changes for `.github/workflows/release.yml`

### Change 1: Remove UV_VERSION from env (Line 33-35)

**Before:**
```yaml
env:
  PYTHON_VERSION: "3.12"
  UV_VERSION: "0.5.0"
```

**After:**
```yaml
env:
  PYTHON_VERSION: "3.12"
```

### Change 2: Update all UV setup actions (Multiple locations)

**Before (appears 5 times in the file):**
```yaml
      - name: Install UV
        uses: astral-sh/setup-uv@v3
        with:
          version: ${{ env.UV_VERSION }}
          enable-cache: true
```

**After:**
```yaml
      - name: Install UV
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
          enable-cache: true
```

### Change 3: Update version bump logic (Lines 66-77)

**Before:**
```yaml
      - name: Get or bump version
        id: version
        run: |
          if [[ "${{ github.event_name }}" == "workflow_dispatch" && "${{ github.event.inputs.version_bump }}" != "" ]]; then
            # Bump version for manual dispatch
            NEW_VERSION=$(uv version --bump ${{ github.event.inputs.version_bump }})
            echo "version=$NEW_VERSION" >> $GITHUB_OUTPUT
          else
            # Get current version
            CURRENT_VERSION=$(uv version)
            echo "version=$CURRENT_VERSION" >> $GITHUB_OUTPUT
          fi
```

**After:**
```yaml
      - name: Get or bump version
        id: version
        run: |
          if [[ "${{ github.event_name }}" == "workflow_dispatch" && "${{ github.event.inputs.version_bump }}" != "" ]]; then
            # Bump version for manual dispatch
            NEW_VERSION=$(uv run python scripts/bump_version.py bump ${{ github.event.inputs.version_bump }})
            echo "version=$NEW_VERSION" >> $GITHUB_OUTPUT
          else
            # Get current version
            CURRENT_VERSION=$(uv run python scripts/bump_version.py get)
            echo "version=$CURRENT_VERSION" >> $GITHUB_OUTPUT
          fi
```

## Why These Changes Are Needed

### Version Bumping Fix
- UV does not have a `version` command
- The workflows were trying to use `uv version --bump` which doesn't exist
- New `scripts/bump_version.py` provides this functionality

### Test Coverage Fix
- Source code is in `src/quickhooks/` directory
- Previous path `--cov=quickhooks` was incorrect
- New path `--cov=src/quickhooks` matches the actual directory structure

### UV Setup Standardization
- Using latest stable version instead of hardcoded version
- Upgrading to setup-uv v4 for better caching and performance
- Removing unused UV_VERSION environment variable

## How to Apply These Changes

1. **Option 1: Manual Edit**
   - Open each workflow file in GitHub's web editor
   - Make the changes listed above
   - Commit directly to the branch

2. **Option 2: Local Edit**
   - Edit the files locally (outside of Claude)
   - Commit and push the changes

3. **Option 3: Use the Provided Workflow Files**
   - The complete updated workflow files are available in your local directory
   - Copy them to `.github/workflows/` and commit

## Verification

After applying the changes, verify they work by:

1. Triggering the CI workflow on a test branch
2. Checking that tests run with correct coverage
3. Testing the release workflow with manual dispatch

## Testing the Version Bump Script

Before using in workflows, test locally:

```bash
# Get current version
uv run python scripts/bump_version.py get

# Test bump (won't actually change if you don't commit)
uv run python scripts/bump_version.py bump patch
```

## Complete Updated Workflow Files

The complete updated workflow files with all changes applied are included in this commit. You can reference them when making manual updates.

## Questions?

See `docs/PUBLISHING.md` for complete documentation on the publishing process and version management.
