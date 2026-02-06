#!/bin/bash
# Commit script for OSS Dev Agent
# Groups files logically and creates separate commits

set -e

echo "Starting commit process..."

# Group 1: Core configuration and setup
echo "Committing core configuration..."
git add .gitignore LICENSE requirements.txt requirements-dev.txt setup_dev.sh README.md
git commit -m "chore: add project configuration and dependencies" || true

# Group 2: Core agent infrastructure
echo "Committing core agent infrastructure..."
git add agent/ client/ context/ hooks/ safety/ ui/ utils/
git commit -m "feat: add core agent infrastructure and utilities" || true

# Group 3: Configuration and tools registry
echo "Committing configuration system..."
git add config/ tools/base.py tools/builtin/ tools/mcp/ tools/registry.py
git commit -m "feat: add configuration system and tool registry" || true

# Group 4: OSS module structure
echo "Committing OSS module..."
git add oss/__init__.py oss/repository.py oss/memory.py oss/github.py oss/workflow.py
git commit -m "feat: add OSS module structure with workflow orchestrator" || true

# Group 5: OSS tools - Git tools
echo "Committing Git tools..."
git add tools/oss/__init__.py tools/oss/git_*.py
git commit -m "feat: add Git integration tools for OSS workflow" || true

# Group 6: OSS tools - GitHub tools
echo "Committing GitHub tools..."
git add tools/oss/fetch_issue.py tools/oss/create_pr.py tools/oss/get_pr_status.py tools/oss/list_issues.py tools/oss/check_pr_comments.py
git commit -m "feat: add GitHub API integration tools" || true

# Group 7: OSS tools - Repository analysis tools
echo "Committing repository analysis tools..."
git add tools/oss/analyze_repository.py tools/oss/check_start_here.py tools/oss/create_start_here.py tools/oss/update_start_here.py
git commit -m "feat: add repository analysis and START_HERE.md management tools" || true

# Group 8: OSS tools - Workflow and memory tools
echo "Committing workflow and memory tools..."
git add tools/oss/workflow_orchestrator.py tools/oss/branch_memory.py
git commit -m "feat: add workflow orchestrator and branch memory tools" || true

# Group 9: OSS prompts
echo "Committing OSS prompts..."
git add prompts/oss.py prompts/oss_review.py
git commit -m "feat: add OSS-specific prompts and review guidance" || true

# Group 10: System prompts integration
echo "Committing system prompts..."
git add prompts/system.py
git commit -m "feat: integrate OSS prompts into system prompt" || true

# Group 11: CLI commands
echo "Committing CLI commands..."
git add cli/__init__.py cli/oss_commands.py
git commit -m "feat: add OSS Dev Agent CLI commands" || true

# Group 12: Main entry point
echo "Committing main entry point..."
git add main.py
git commit -m "feat: integrate OSS Dev Agent CLI with main entry point" || true

# Group 13: Tests - Core tests
echo "Committing core tests..."
find tests/ -name "*.py" -not -path "tests/oss/*" -not -path "tests/cli/*" -not -path "tests/prompts/*" | xargs git add 2>/dev/null || true
git commit -m "test: add core agent tests" || true

# Group 14: Tests - OSS module tests
echo "Committing OSS module tests..."
git add tests/oss/
git commit -m "test: add tests for OSS modules" || true

# Group 15: Tests - CLI and prompts tests
echo "Committing CLI and prompts tests..."
git add tests/cli/ tests/prompts/
git commit -m "test: add tests for CLI commands and prompts" || true

# Group 16: Scripts and other files
echo "Committing scripts and remaining files..."
git add scripts/ commit_changes.sh
git commit -m "chore: add utility scripts" || true

echo ""
echo "All commits completed!"
echo "Run 'git log --oneline' to see all commits"
echo "Run 'git push -u origin main' to push to remote"
