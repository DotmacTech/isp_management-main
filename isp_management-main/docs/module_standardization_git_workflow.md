# Module Standardization Git Workflow

## Overview

This document outlines the Git workflow strategy for implementing the module standardization across the ISP Management Platform codebase. Following this workflow will ensure that changes are made systematically, tracked properly, and can be reviewed and tested thoroughly before being merged into the main branch.

## Branch Strategy

### Main Branches

- `main` - The production-ready branch
- `develop` - The development branch where features are integrated

### Feature Branches

For each module standardization, create a feature branch with the following naming convention:

```
standardize/module-name
```

Examples:
- `standardize/monitoring`
- `standardize/billing`
- `standardize/auth`

## Workflow Steps

### 1. Create a Standardization Branch

```bash
# Ensure you're on the latest develop branch
git checkout develop
git pull origin develop

# Create a new standardization branch
git checkout -b standardize/module-name
```

### 2. Implement Standardization Changes

Follow the standardization guide to implement changes for the module:

1. Create the standard directory structure
2. Move files to appropriate directories
3. Update imports
4. Create proper `__init__.py` files
5. Update the module's main `__init__.py`

Use the standardization script to automate parts of this process:

```bash
python scripts/standardize_module.py module_name
```

### 3. Commit Changes

Make atomic commits with descriptive messages:

```bash
# Example commit messages
git commit -m "Create standard directory structure for module_name"
git commit -m "Move endpoints to api directory in module_name"
git commit -m "Update imports in module_name"
git commit -m "Create proper __init__.py files in module_name"
```

### 4. Test Changes

Run tests to ensure functionality is preserved:

```bash
# Run unit tests for the module
pytest tests/modules/module_name

# Run integration tests
pytest tests/integration/test_module_name.py
```

### 5. Push Changes

Push your changes to the remote repository:

```bash
git push origin standardize/module-name
```

### 6. Create a Pull Request

Create a pull request from your standardization branch to the `develop` branch:

- Title: `Standardize module_name module structure`
- Description: Include details about the changes made and any special considerations

### 7. Code Review

Request code review from team members:

- Ensure all standardization requirements are met
- Check for any potential issues with imports or dependencies
- Verify that tests are passing

### 8. Address Feedback

Make any necessary changes based on code review feedback:

```bash
# Make changes
git commit -m "Address code review feedback"
git push origin standardize/module-name
```

### 9. Merge to Develop

Once the pull request is approved and all tests pass, merge the changes to the `develop` branch:

```bash
# Option 1: Merge via GitHub UI

# Option 2: Merge via command line
git checkout develop
git merge --no-ff standardize/module-name
git push origin develop
```

### 10. Delete the Branch

After successful merge, delete the standardization branch:

```bash
# Delete local branch
git branch -d standardize/module-name

# Delete remote branch
git push origin --delete standardize/module-name
```

## Handling Conflicts

If you encounter merge conflicts:

1. Pull the latest changes from the `develop` branch
   ```bash
   git checkout develop
   git pull origin develop
   git checkout standardize/module-name
   git merge develop
   ```

2. Resolve conflicts
   - Carefully review each conflict
   - Ensure that standardization changes are preserved
   - Consult with team members if needed

3. Complete the merge
   ```bash
   git add .
   git commit -m "Resolve merge conflicts with develop"
   git push origin standardize/module-name
   ```

## Tracking Progress

Use GitHub project boards or issues to track the standardization progress:

1. Create an issue for each module standardization
2. Link pull requests to the corresponding issues
3. Update the status as you progress through the implementation

## Rollback Plan

If issues are discovered after merging:

1. Create a revert branch
   ```bash
   git checkout develop
   git checkout -b revert/standardize-module-name
   ```

2. Revert the merge commit
   ```bash
   git revert -m 1 <merge-commit-hash>
   git push origin revert/standardize-module-name
   ```

3. Create a pull request to revert the changes

## Conclusion

Following this Git workflow will ensure a systematic approach to module standardization, making it easier to track changes, review code, and maintain a stable codebase throughout the standardization process.
