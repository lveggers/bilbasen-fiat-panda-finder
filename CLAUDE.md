# Claude Code Development Workflow

**IMPORTANT: Never use emojis in any code, comments, documentation, or output. Always use plain text.**

**CRITICAL WORKFLOW INSTRUCTION: When encountering code issues that require skipping or deferring:**

1. **ALWAYS ASK PERMISSION FIRST** - Never skip failing tests, broken functionality, or defer fixes without explicit user approval
2. **IF USER APPROVES SKIPPING** - Must immediately create a comprehensive GitHub issue that includes:
   - Complete error logs and stack traces
   - Detailed analysis of root causes
   - Potential solution approaches
   - Impact assessment on the codebase
   - Clear steps to reproduce the issue
3. **DOCUMENT EVERYTHING** - The issue must be thorough enough for future developers to understand and fix
4. **REFERENCE THE SKIP** - Any temporary workarounds must reference the GitHub issue number

This ensures no issues are lost and maintains full project transparency.

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

1. **Create Pull Request**: After pushing changes, create PR with detailed description
2. **Demo Application**: **CRITICAL** - Before approval, always spin up the application for live review
   ```bash
   # Start the application server
   poetry run uvicorn src.app.server:app --host 127.0.0.1 --port 8001
   
   # Verify application is working with real data
   curl "http://127.0.0.1:8001/api/v1/scores"
   
   # Provide access URL for review
   echo "Application ready at: http://127.0.0.1:8001"
   ```
3. **Wait for Review**: Stop work and wait for approval after demonstrating functionality
4. **Address Feedback**: Make requested changes in the same feature branch if needed
5. **Merge After Approval**: Only continue after PR is approved and merged

### 5. Post-Merge Cleanup

After PR is approved and merged:
1. Switch back to master: `git checkout master`
2. Pull latest changes: `git pull origin master`
3. Delete feature branch: `git branch -d feature/branch-name`
4. **Update Project Context**: Update the changelog in `project_context.md` with the completed feature
   ```bash
   # Add entry to changelog reflecting the merged PR:
   # 1. Move PR from "Pending Review" to "Merged" in Key Milestones section
   # 2. Add new version entry in Change Log with:
   #    - Version number (semantic versioning)
   #    - Release date
   #    - Added/Fixed/Changed sections with bullet points
   #    - Reference to closed GitHub issues
   # 3. Update Current Status section if needed
   ```
5. Continue with next feature

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

## Debug Workflow

### Debug Folder Structure

All debugging and testing scripts are located in the `debug/` folder:

- `debug/test_scraper.py` - Test original CSS-based scraper
- `debug/test_json_scraper.py` - Test new JSON-based scraper  
- `debug/test_end_to_end.py` - Complete end-to-end system test

### Running Debug Tests

To test the complete system functionality:

```bash
# Test JSON-based scraper (recommended)
python debug/test_json_scraper.py

# Test complete workflow: scraping -> scoring -> storage
python debug/test_end_to_end.py
```

### Key Improvements Made

1. **Fixed Scraper Issues**:
   - Updated search URL to use correct Fiat Panda endpoint
   - Created JSON-based extractor for modern Bilbasen structure
   - Added fallback CSS selectors for compatibility

2. **Enhanced Data Extraction**:
   - Extracts data from Next.js `__NEXT_DATA__` JSON structure
   - Properly parses price, year, kilometers, location, etc.
   - Added condition scoring based on description analysis

3. **Improved Workflow**:
   - JSON extraction is faster and more reliable than DOM parsing
   - Added comprehensive error handling and logging
   - Created modular components for easier testing

### Troubleshooting

If scraping fails:
1. Check if Bilbasen has updated their structure
2. Review saved fixtures in `src/app/scraper/fixtures/`
3. Use debug scripts to isolate issues
4. Update CSS selectors in `selectors.py` if needed

The debug folder is automatically ignored by git to prevent clutter.