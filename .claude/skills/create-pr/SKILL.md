---
name: create-pr
description: Create a pull request with standardized format for FinAgent
disable-model-invocation: true
allowed-tools: Bash(git *), Bash(gh *)
argument-hint: [title]
---

# Create Pull Request for FinAgent

Create a pull request following FinAgent's standardized format and conventions.

## Pre-flight Checks

1. Ensure we're on a feature branch (must start with `feature/`)
2. Ensure all changes are committed
3. Run tests before creating PR
4. **TEST COVERAGE**: Ensure test coverage is at least 50%
5. **SECURITY CHECK**: Scan for sensitive information before creating PR
6. **README CHECK**: Ensure README.md is updated for architectural changes

## Process

### Step 1: Verify Branch
```bash
git rev-parse --abbrev-ref HEAD
```
- If on `main`, STOP and ask user to create a feature branch first
- Branch MUST start with `feature/` per CLAUDE.md guidelines

### Step 2: Check for Uncommitted Changes
```bash
git status --porcelain
```
- If there are uncommitted changes, ask user if they want to commit first

### Step 3: Test Coverage Check (REQUIRED)

**Minimum coverage requirement: 50%**

Run tests with coverage:
```bash
cd backend && source venv/bin/activate && python -m pytest tests/ --cov=. --cov-report=term-missing --cov-fail-under=50
```

**If coverage is below 50%:**
1. STOP the PR creation
2. Show the current coverage percentage
3. Show which files/functions have low coverage
4. Ask user to add tests before proceeding

**Coverage report interpretation:**
- Look at the `TOTAL` line for overall coverage percentage
- Files with `0%` or very low coverage need attention
- Focus on testing new code that was added in this PR

**Only proceed to Step 4 if coverage >= 50%**

### Step 4: Security Scan (CRITICAL)

**STOP the PR if any of these are found in the diff:**

```bash
git diff main --cached
git diff main
```

Scan for these patterns in the diff output:

| Category | Patterns to Flag |
|----------|------------------|
| **API Keys** | `api_key`, `apikey`, `api-key`, `sk-`, `pk_live_`, `sk_live_`, `AKIA`, `ghp_`, `gho_`, `github_pat_` |
| **Secrets** | `secret`, `password`, `passwd`, `credential`, `token` (when followed by `=` or `:` and a value) |
| **Private Keys** | `-----BEGIN`, `PRIVATE KEY`, `RSA PRIVATE` |
| **Environment Files** | `.env` files being added (check `git diff --name-only`) |
| **Personal Info** | Email addresses (other than generic ones), phone numbers, physical addresses |
| **Hardcoded URLs** | Internal/staging URLs, localhost with credentials |

**Check commands:**
```bash
# Check for .env files
git diff main --name-only | grep -E '\.env'

# Check for potential secrets in diff
git diff main | grep -iE '(api[_-]?key|secret|password|token|credential)\s*[:=]'

# Check for private keys
git diff main | grep -E '(BEGIN|PRIVATE).*(KEY|RSA)'

# Check for API key patterns
git diff main | grep -E '(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|AKIA[A-Z0-9]{16})'
```

**If ANY sensitive data is found:**
1. STOP immediately
2. Show the user exactly what was found and in which file
3. Ask user to remove the sensitive data before proceeding
4. Suggest using environment variables instead

**Only proceed to Step 5 if security scan passes.**

### Step 5: Get Change Context (only after security scan passes)
Run these in parallel:
```bash
git log main..HEAD --oneline
git diff main --stat
```

### Step 6: README Update Check (REQUIRED)

**Check if changes require README.md updates:**

Analyze the diff to detect architectural or high-level changes:

```bash
git diff main --name-only
```

**Changes that REQUIRE README.md updates:**

| Change Type | Examples |
|-------------|----------|
| **New features** | New API endpoints, new UI sections, new agent capabilities |
| **Architectural changes** | New services, new directories, changed project structure |
| **Dependency changes** | New packages in requirements.txt or package.json |
| **Configuration changes** | New environment variables, new config files |
| **Removed features** | Deleted endpoints, removed UI components |
| **API changes** | Changed request/response formats, new routes |

**Detection commands:**
```bash
# Check for new directories
git diff main --name-only --diff-filter=A | grep -E '^[^/]+/$'

# Check for new route files
git diff main --name-only | grep -E 'routes/|endpoints/|api/'

# Check for dependency changes
git diff main --name-only | grep -E 'requirements|package.json'

# Check for config changes
git diff main --name-only | grep -E 'config|\.env\.example'

# Check for significant file additions/deletions
git diff main --stat | tail -1
```

**If architectural changes detected:**
1. Check if README.md is already in the diff: `git diff main --name-only | grep README.md`
2. If README.md is NOT updated:
   - STOP and notify the user
   - List the architectural changes detected
   - Ask user to update README.md with:
     - New features/capabilities added
     - Any new setup steps required
     - Updated project structure (if changed)
     - New environment variables (if any)
   - Wait for user to update README.md before proceeding

**Skip this check if:**
- Only test files changed
- Only minor bug fixes (no new features)
- Only style/formatting changes
- README.md is already in the changeset

### Step 7: CLAUDE.md Update Check (REQUIRED for Structural Changes)

**Check if changes require CLAUDE.md updates:**

CLAUDE.md provides context for AI assistants. It must be updated when the codebase structure changes.

**Changes that REQUIRE CLAUDE.md updates:**

| Change Type | Examples |
|-------------|----------|
| **New agents** | Files added to `backend/agents/` |
| **New routes** | Files added to `backend/routes/` |
| **New services** | Files added to `backend/services/` |
| **New pages** | Files added to `frontend/src/pages/` |
| **New component directories** | New folders in `frontend/src/components/` |
| **Data flow changes** | Changes to orchestrator, agent coordination |
| **New config requirements** | New environment variables, new dependencies |

**Detection commands:**
```bash
# Check for new structural files
git diff main --name-only --diff-filter=A | grep -E '^backend/(agents|routes|services)/.*\.py$|^frontend/src/(pages|components)/.*\.(jsx|tsx)$'

# Check for deleted structural files
git diff main --name-only --diff-filter=D | grep -E '^backend/(agents|routes|services)/.*\.py$|^frontend/src/(pages|components)/.*\.(jsx|tsx)$'

# Check for changes to orchestrator/data flow
git diff main --name-only | grep -E 'orchestrator|coordinator'
```

**If structural changes detected:**
1. Check if CLAUDE.md is already in the diff: `git diff main --name-only | grep CLAUDE.md`
2. If CLAUDE.md is NOT updated:
   - WARN the user (not blocking, but recommended)
   - List the structural changes detected
   - Suggest updating CLAUDE.md with:
     - New files added to "Key Files by Purpose" tables
     - Updated data flow (if orchestration changed)
     - New common tasks (if applicable)
   - Ask user if they want to update CLAUDE.md now or proceed anyway

**Skip this check if:**
- Only implementation changes within existing files
- Only test files changed
- Only style/formatting changes
- CLAUDE.md is already in the changeset

### Step 8: Push Branch
```bash
git push -u origin <branch-name>
```

### Step 9: Create PR with Standard Format

Use this EXACT format for the PR body:

```markdown
## Summary
<2-4 bullet points describing what changed and why>

## Changes

### Backend
<list modified backend files with brief description>

### Frontend
<list modified frontend files with brief description>

## Test plan
- [ ] All backend tests pass (`make test`)
- [ ] Frontend builds successfully
- [ ] Manual testing completed
- [ ] README.md updated (if architectural changes)

🤖 Generated with [Claude Code](https://claude.ai/claude-code)
```

### Command Format
```bash
gh pr create --title "<title>" --body "$(cat <<'EOF'
<PR body here>
EOF
)"
```

## Title Guidelines

- Keep under 70 characters
- Use imperative mood ("Add feature" not "Added feature")
- Be specific but concise
- Examples:
  - "Add expanded 4Q comparison with categorized metrics"
  - "Fix number formatting in deep insights"
  - "Update analyst ratings color scheme"

## Arguments

- `$ARGUMENTS`: Optional PR title. If not provided, generate from branch name and changes.

## After PR Creation

- Output the PR URL
- Remind user to request review if needed
