# Git Branching Strategy for ISP Management Platform

This document outlines the Git branching strategy for the ISP Management Platform to ensure code stability, facilitate collaboration, and maintain a clean project history.

## Branch Structure

We follow a modified GitFlow workflow with the following branches:

### Core Branches

- **main**: The production-ready code. This branch is always stable and deployable.
- **develop**: The main development branch where features are integrated. This branch should always be in a working state.

### Supporting Branches

- **feature/***:  Feature branches for new functionality (e.g., `feature/mfa-implementation`)
- **bugfix/***:   Bugfix branches for fixing issues (e.g., `bugfix/auth-token-validation`)
- **hotfix/***:   Hotfix branches for critical production fixes (e.g., `hotfix/security-vulnerability`)
- **release/***:  Release branches for preparing releases (e.g., `release/v1.2.0`)

## Workflow

### Feature Development

1. Create a feature branch from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/feature-name
   ```

2. Develop the feature with regular commits:
   ```bash
   git add .
   git commit -m "Descriptive commit message"
   ```

3. Push the feature branch to remote:
   ```bash
   git push origin feature/feature-name
   ```

4. When the feature is complete, create a pull request to merge into `develop`.

5. After code review and testing, merge the feature branch into `develop`:
   ```bash
   git checkout develop
   git merge --no-ff feature/feature-name
   git push origin develop
   ```

### Bug Fixes

1. Create a bugfix branch from `develop`:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b bugfix/bug-description
   ```

2. Fix the bug with clear commit messages:
   ```bash
   git add .
   git commit -m "Fix: Description of the bug fix"
   ```

3. Push the bugfix branch to remote:
   ```bash
   git push origin bugfix/bug-description
   ```

4. Create a pull request to merge into `develop`.

5. After code review and testing, merge the bugfix branch into `develop`:
   ```bash
   git checkout develop
   git merge --no-ff bugfix/bug-description
   git push origin develop
   ```

### Hotfixes

For critical issues in production:

1. Create a hotfix branch from `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b hotfix/issue-description
   ```

2. Fix the issue with clear commit messages:
   ```bash
   git add .
   git commit -m "Hotfix: Description of the critical fix"
   ```

3. Push the hotfix branch to remote:
   ```bash
   git push origin hotfix/issue-description
   ```

4. Create pull requests to merge into both `main` and `develop`.

5. After code review and testing, merge the hotfix branch into both branches:
   ```bash
   git checkout main
   git merge --no-ff hotfix/issue-description
   git tag -a v1.2.1 -m "Version 1.2.1"
   git push origin main --tags
   
   git checkout develop
   git merge --no-ff hotfix/issue-description
   git push origin develop
   ```

### Releases

1. Create a release branch from `develop` when ready to prepare a release:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b release/v1.3.0
   ```

2. Make any final adjustments, version bumps, and documentation updates:
   ```bash
   git add .
   git commit -m "Prepare release v1.3.0"
   ```

3. Push the release branch to remote:
   ```bash
   git push origin release/v1.3.0
   ```

4. Create pull requests to merge into both `main` and `develop`.

5. After final testing, merge the release branch into both branches:
   ```bash
   git checkout main
   git merge --no-ff release/v1.3.0
   git tag -a v1.3.0 -m "Version 1.3.0"
   git push origin main --tags
   
   git checkout develop
   git merge --no-ff release/v1.3.0
   git push origin develop
   ```

## Commit Message Guidelines

Follow these guidelines for clear and informative commit messages:

- Use the imperative mood ("Add feature" not "Added feature")
- Start with a capital letter
- Keep the first line under 50 characters
- Add more detailed explanation in the commit body if needed
- Reference issue numbers when applicable

Examples:
```
Add multi-factor authentication feature
Fix token validation in auth service
Update documentation for API endpoints
```

For more significant commits, use a structured format:
```
Feature: Add session management

- Track user sessions with IP and device info
- Allow users to view and terminate active sessions
- Implement automatic session timeout after inactivity

Resolves #123
```

## Pull Request Process

1. Create a pull request with a clear title and description
2. Link to relevant issues
3. Ensure all tests pass
4. Request reviews from appropriate team members
5. Address review comments
6. Merge only after approval

## Tagging and Versioning

We follow Semantic Versioning (SemVer):

- **MAJOR** version for incompatible API changes
- **MINOR** version for backward-compatible functionality
- **PATCH** version for backward-compatible bug fixes

Example: `v1.2.3`

Create tags for each release:
```bash
git tag -a v1.2.3 -m "Version 1.2.3"
git push origin --tags
```

## Best Practices

1. **Pull before you push**: Always pull the latest changes before pushing
2. **Rebase feature branches**: Keep feature branches up-to-date with develop
3. **Squash commits**: Consider squashing multiple small commits before merging
4. **Delete merged branches**: Clean up branches after they've been merged
5. **Write good commit messages**: Be clear and descriptive
6. **Run tests before committing**: Ensure your changes don't break existing functionality
7. **Review your own code**: Self-review before requesting reviews from others

## Handling the Authentication Module

Since the authentication module is critical for the system's security and functionality:

1. **Comprehensive Testing**: Ensure all authentication-related changes have thorough test coverage
2. **Security Reviews**: Request security-focused code reviews for authentication changes
3. **Feature Flags**: Consider using feature flags for major authentication changes
4. **Backward Compatibility**: Maintain backward compatibility for authentication APIs
5. **Documentation**: Update authentication documentation with each significant change

## CI/CD Integration

Our branching strategy integrates with CI/CD as follows:

- **Commit to any branch**: Triggers linting and unit tests
- **Pull request to develop**: Triggers integration tests
- **Merge to develop**: Triggers deployment to staging environment
- **Merge to main**: Triggers deployment to production environment

## Getting Started

To start using this Git strategy:

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/isp-management.git
   cd isp-management
   ```

2. Create the main branches if they don't exist:
   ```bash
   git checkout -b main
   git push -u origin main
   
   git checkout -b develop
   git push -u origin develop
   ```

3. Start creating feature branches from develop:
   ```bash
   git checkout develop
   git checkout -b feature/your-feature
   ```
