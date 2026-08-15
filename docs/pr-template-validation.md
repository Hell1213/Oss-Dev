# PR Template Validation

## Overview

The PR Template Validation workflow automatically validates pull request submissions against the project's [`PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md). This ensures all PRs include required information for efficient code review.

## What It Checks

The workflow validates that all required sections are present and properly filled:

1. **Summary** — One-line summary of the change
2. **Related Issue** — Reference to the GitHub issue being addressed (e.g., `Fixes #123`)
3. **Type of Change** — Checkbox selection (Bug fix, Feature, Documentation, etc.)
4. **Testing** — Verification that tests pass (ruff, mypy, pytest)
5. **Description** — Detailed explanation of the change and motivation

Each section must:
- Be present in the PR body
- Contain meaningful content (not just placeholder text)
- Not be left blank or contain only HTML comments

## Validation Workflow

The workflow runs automatically when a PR is:
- **Opened** — Initial validation on PR creation
- **Edited** — Re-validation when PR description is updated
- **Synchronized** — Re-validation when new commits are pushed

## Failure Scenarios

The validation **fails** if:
- Any required section is missing
- A section is left empty
- A section contains only placeholder text (e.g., `<!-- describe the solution -->`)

### Example Failure

```
❌ PR Template Validation Failed

- Missing or empty required sections: Summary, Type of Change
- Sections with only placeholder text: Description
```

### Resolution

1. Click "Edit" on your PR description
2. Fill in all required sections with meaningful content
3. The workflow will automatically re-run and pass once fixed

## Success Message

Once all validations pass, you'll see:

```
✅ PR template validation passed
```

## Contributing Guidelines

When submitting a PR, ensure you:

1. Follow the template structure exactly
2. Complete all required sections
3. Use clear, descriptive language
4. Reference the issue being fixed with `Fixes #<number>`
5. Select at least one type of change
6. Confirm that all tests pass locally before submitting

## Configuration

The validation rules are defined in `.github/workflows/pr-lint.yml`. To update the rules:

1. Edit the `requiredSections` array to add/remove sections
2. Modify pattern matching to be stricter or more lenient
3. Update placeholder detection keywords as needed

## Support

If you encounter issues with the PR template validation:

1. Check that your PR follows the template exactly
2. Ensure all sections have meaningful (non-placeholder) content
3. Open an issue if you believe the validation is too strict
