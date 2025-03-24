# ISP Management Platform Git Strategy

This document provides a quick reference for the Git branching strategy used in this project.

## Branch Structure

- **main**: Production-ready code
- **develop**: Main development branch
- **feature/***:  Feature branches (e.g., `feature/mfa-implementation`)
- **bugfix/***:   Bugfix branches (e.g., `bugfix/auth-token-validation`)
- **hotfix/***:   Hotfix branches for critical production fixes
- **release/***:  Release branches for preparing releases

## Quick Reference Commands

### Starting a New Feature

```bash
git checkout develop
git pull origin develop
git checkout -b feature/feature-name
# Make changes
git add .
git commit -m "Descriptive commit message"
git push origin feature/feature-name
# Create PR to develop when ready
```

### Fixing a Bug

```bash
git checkout develop
git pull origin develop
git checkout -b bugfix/bug-description
# Fix bug
git add .
git commit -m "Fix: Description of the bug fix"
git push origin bugfix/bug-description
# Create PR to develop when ready
```

### Critical Production Hotfix

```bash
git checkout main
git pull origin main
git checkout -b hotfix/issue-description
# Fix issue
git add .
git commit -m "Hotfix: Description of the critical fix"
git push origin hotfix/issue-description
# Create PRs to both main and develop
```

### Preparing a Release

```bash
git checkout develop
git pull origin develop
git checkout -b release/v1.3.0
# Make final adjustments
git add .
git commit -m "Prepare release v1.3.0"
git push origin release/v1.3.0
# Create PRs to both main and develop
```

## Commit Message Guidelines

- Use the imperative mood ("Add feature" not "Added feature")
- Start with a capital letter
- Keep the first line under 50 characters
- Reference issue numbers when applicable

## For More Details

See the full Git strategy documentation in [docs/git_strategy.md](docs/git_strategy.md).
