# Release Process for ghost-ng

This document outlines the release process for ghost-ng, including version management and automated builds.

## Version Management

ghost-ng uses semantic versioning (SemVer) with the format `MAJOR.MINOR.PATCH`:

- **MAJOR**: Breaking changes, major feature additions
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

## Release Workflow

### 1. Manual Release Process

Use the release script for a streamlined experience:

```bash
# For a patch release (bug fixes)
python scripts/release.py patch

# For a minor release (new features)
python scripts/release.py minor

# For a major release (breaking changes)
python scripts/release.py major
```

This script will:
1. Bump the version in `ghostman/__version__.py`
2. Commit the version change
3. Create and push a git tag
4. Trigger automated builds via GitHub Actions

### 2. Manual Version Bumping

If you prefer manual control:

```bash
# Bump version and create tag
python scripts/version_bump.py patch --tag

# Push the tag to trigger builds
git push origin v1.0.1
```

### 3. Direct Git Tagging

For emergency releases or specific control:

```bash
# Create and push tag directly
git tag -a v1.0.1 -m "Release v1.0.1"
git push origin v1.0.1
```

## Automated Build Process

When a version tag (e.g., `v1.0.0`) is pushed to GitHub, the release workflow automatically:

### Creates Release Assets:
- **Windows**: `ghost-ng-windows-x64.zip` (PyInstaller executable)
- **Linux**: `ghost-ng-linux-x64.tar.gz` (PyInstaller executable)  
- **macOS**: `ghost-ng-macos-x64.tar.gz` (PyInstaller executable)
- **Python Package**: `ghost-ng.whl` (wheel distribution)
- **Source**: `ghost-ng-source.tar.gz` (source distribution)

### Build Matrix:
- Windows (latest)
- Ubuntu (latest)
- macOS (latest)
- Python 3.12

## File Structure

```
├── ghostman/__version__.py          # Version information
├── ghost-ng.spec                    # PyInstaller specification
├── scripts/
│   ├── version_bump.py              # Version management
│   └── release.py                   # Release automation
├── .github/workflows/
│   ├── release.yml                  # Release builds
│   └── ci.yml                       # Continuous integration
└── build.py                         # Local build script
```

## Version File Format

The `ghostman/__version__.py` file contains:

```python
__version__ = "1.0.0"
__title__ = "ghost-ng"
__description__ = "A sleek AI-powered desktop assistant..."
__author__ = "ghost-ng team"
__author_email__ = "team@ghost-ng.org"
__license__ = "MIT"
__url__ = "https://github.com/ghost-ng/ghost-ng"

VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0
VERSION_INFO = (1, 0, 0)
```

## Release Checklist

Before creating a release:

- [ ] All tests pass (`python -m pytest`)
- [ ] Code is linted (`flake8 ghostman`)
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (if exists)
- [ ] Version bump type is correct (patch/minor/major)
- [ ] Git working directory is clean

## Post-Release

After a successful release:

1. **Verify Release**: Check [GitHub Releases](https://github.com/ghost-ng/ghost-ng/releases)
2. **Test Artifacts**: Download and test the built executables
3. **Update Documentation**: Ensure docs reflect the new version
4. **Announce**: Share the release with users

## Troubleshooting

### Build Failures

If GitHub Actions builds fail:

1. Check the [Actions tab](https://github.com/ghost-ng/ghost-ng/actions)
2. Review build logs for specific errors
3. Common issues:
   - Missing dependencies in `requirements.txt`
   - PyInstaller spec file errors
   - Platform-specific build problems

### Version Conflicts

If version bumping fails:
- Ensure git working directory is clean
- Check that the version format is valid
- Verify no existing tag with the same version

### Manual Recovery

To fix a failed release:

```bash
# Delete problematic tag
git tag -d v1.0.1
git push origin --delete v1.0.1

# Fix issues and retry
python scripts/version_bump.py patch --tag --push
```

## Development Builds

For development testing:

```bash
# Build locally
python build.py

# Test PyInstaller spec
pyinstaller ghost-ng.spec
```