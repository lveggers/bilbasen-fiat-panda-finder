# Claude Code Development Workflow

## Git Workflow for Feature Development

This document outlines the development workflow to be followed for all code changes in this project.

### 1. Feature Branch Workflow

For every feature, bug fix, or code change:

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/descriptive-name
   ```
   - Use descriptive branch names: `feature/api-endpoints`, `feature/dark-ui`, `bugfix/scraper-timeout`
   - Always branch from `master`

2. **Implement the Feature**
   - Write code following project conventions
   - Include type hints, docstrings, and error handling
   - Follow the established project structure

3. **Commit Changes**
   ```bash
   git add .
   git commit -m "Descriptive commit message

   - Bullet points of changes
   - Reference GitHub issues: Closes #X, Addresses #Y
   
   🤖 Generated with [Claude Code](https://claude.ai/code)
   
   Co-Authored-By: Claude <noreply@anthropic.com>"
   ```

4. **Push and Create Pull Request**
   ```bash
   git push -u origin feature/branch-name
   gh pr create --title "Feature: Descriptive Title" --body "PR_BODY_TEMPLATE"
   ```

### 2. Pull Request Template

Use this template for all PR descriptions:

```markdown
## Summary
Brief description of what this PR implements.

## Key Features
- Feature 1
- Feature 2
- Feature 3

## Addresses Issues
- Closes #X (Description)
- Addresses #Y (Description)

## Test Plan
- [ ] Test item 1
- [ ] Test item 2
- [ ] Test item 3

🤖 Generated with [Claude Code](https://claude.ai/code)
```

### 3. GitHub Issue Management

1. **Update Issues**: Comment on relevant issues with PR references
   ```bash
   gh issue comment X --body "Implementation ready: PR #Y includes [description]"
   ```

2. **Close Issues**: Use commit messages or PR description to close issues
   - "Closes #X" or "Fixes #X" in commit message
   - GitHub will auto-close when PR is merged

### 4. Review Process

1. **Wait for Review**: After creating PR, stop work and wait for approval
2. **Address Feedback**: Make requested changes in the same feature branch
3. **Merge After Approval**: Only continue after PR is approved and merged

### 5. Post-Merge Cleanup

After PR is approved and merged:
1. Switch back to master: `git checkout master`
2. Pull latest changes: `git pull origin master`
3. Delete feature branch: `git branch -d feature/branch-name`
4. Continue with next feature

## Current Project Status

### Completed Features (Merged)
- ✅ Configuration and logging
- ✅ Database models and CRUD
- ✅ Danish condition parsing
- ✅ Playwright scraper with rate limiting
- ✅ Scoring algorithm with winsorization

### Remaining Features
- 🔄 FastAPI server and endpoints
- 🔄 Dark-themed UI with Tailwind and Plotly
- 🔄 Comprehensive testing suite
- 🔄 CI/CD pipeline
- 🔄 Documentation and README

## Development Guidelines

### Code Standards
- Use type hints throughout
- Include comprehensive docstrings
- Follow existing code patterns and conventions
- Handle errors gracefully with logging
- Respect rate limits and implement polite scraping

### Branch Naming Conventions
- `feature/` - New features
- `bugfix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation updates
- `test/` - Test improvements

### Commit Message Format
```
Short descriptive title (50 chars max)

Longer description if needed:
- Bullet points for changes
- Reference issues with #number
- Explain the why, not just the what

Closes #issue-number
```

## Next Steps Protocol

1. **Before Starting**: Check that current PR is approved and merged
2. **Create Branch**: Always create new feature branch for each task
3. **Implement**: Focus on one feature at a time
4. **Test**: Ensure code works as expected
5. **PR Review**: Wait for approval before continuing
6. **Repeat**: Continue with next feature

This workflow ensures code quality, traceability, and proper collaboration through the review process.