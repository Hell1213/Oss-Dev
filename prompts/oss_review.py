"""
OSS Code Review Self-Check Prompts

Prompts for the agent to review its own code before submitting.
"""


def get_code_review_self_check_prompt(changes_summary: str, issue_description: str) -> str:
    """
    Get prompt for self-reviewing code before commit.
    
    Args:
        changes_summary: Summary of changes made
        issue_description: Original issue description
    
    Returns:
        Self-review prompt
    """
    return f"""# Code Review Self-Check

Before committing, review your changes against these criteria:

## 1. Scope Alignment
- [ ] Does this fix exactly what the issue asks for?
- [ ] Are all changed files directly related to the issue?
- [ ] Did I avoid unrelated changes?

## 2. Code Quality
- [ ] Does the code follow existing patterns in the repo?
- [ ] Are variable/function names consistent with codebase style?
- [ ] Is the code readable and maintainable?
- [ ] Are there any obvious bugs or edge cases missed?

## 3. Testing
- [ ] Are tests added/updated for the fix?
- [ ] Do tests cover the main case and edge cases?
- [ ] Do tests follow existing test patterns?

## 4. Documentation
- [ ] Is documentation updated only if directly affected?
- [ ] Are comments added only where necessary?
- [ ] Is the code self-documenting?

## 5. Commit Quality
- [ ] Is the commit message clear and follows conventional format?
- [ ] Are changes logically grouped?
- [ ] Is the diff minimal and focused?

## Changes Made:
{changes_summary}

## Original Issue:
{issue_description}

Review your changes using 'git_diff' and 'git_status' tools.
If any criteria are not met, fix them before committing."""


def get_maintainer_feedback_prompt(feedback: str, pr_url: str) -> str:
    """
    Get prompt for handling maintainer feedback.
    
    Args:
        feedback: Maintainer feedback/comments
        pr_url: PR URL
    
    Returns:
        Feedback handling prompt
    """
    return f"""# Maintainer Feedback Received

A maintainer has provided feedback on your PR: {pr_url}

## Feedback:
{feedback}

## How to Handle Feedback:

1. **Read Carefully**: Understand what the maintainer is asking for
2. **Be Respectful**: Maintainers are volunteers helping improve the project
3. **Address All Points**: Make sure to address every comment
4. **Ask for Clarification**: If feedback is unclear, ask ONE precise question
5. **Make Changes**: Update code, tests, or documentation as requested
6. **Keep Scope**: Only address the feedback, don't add unrelated changes
7. **Update PR**: Push changes and acknowledge feedback

## Steps:
1. Use 'check_pr_comments' tool to get all feedback
2. Review each comment carefully
3. Make necessary changes
4. Test changes if applicable
5. Commit with message: `fix: address maintainer feedback`
6. Push changes
7. Acknowledge feedback in PR comments if appropriate

Remember: Maintainer feedback is valuable. Use it to improve your contribution."""


def get_rebase_prompt(base_branch: str = "main") -> str:
    """
    Get prompt for rebasing branch.
    
    Args:
        base_branch: Base branch to rebase onto
    
    Returns:
        Rebase prompt
    """
    return f"""# Rebase Branch

Your branch needs to be rebased onto {base_branch} to resolve conflicts or update with latest changes.

## Rebase Steps:

1. **Fetch Latest Changes**
   - Use 'git_fetch' to get latest from remote
   
2. **Rebase Onto Base Branch**
   - Use 'git_rebase' tool to rebase onto {base_branch}
   - If conflicts occur, resolve them carefully
   
3. **Resolve Conflicts** (if any)
   - Read conflict markers carefully
   - Keep your changes while integrating upstream changes
   - Test after resolving conflicts
   
4. **Force Push** (if needed)
   - After rebase, you may need to force push
   - Use 'git_push' with force flag if necessary
   - Be careful: only force push to your feature branch

## Conflict Resolution Guidelines:
- Keep your changes that address the issue
- Integrate upstream changes that don't conflict
- Test thoroughly after resolving conflicts
- Don't break existing functionality

After rebase, verify tests still pass and PR is updated."""


def get_scope_violation_check_prompt(diff_summary: str, issue_description: str) -> str:
    """
    Get prompt for checking scope violations.
    
    Args:
        diff_summary: Summary of changes in diff
        issue_description: Original issue description
    
    Returns:
        Scope violation check prompt
    """
    return f"""# Scope Violation Check

Review your changes to ensure they stay within issue scope.

## Your Changes:
{diff_summary}

## Original Issue:
{issue_description}

## Check for Scope Violations:

1. **Unrelated Files**: Are any changed files unrelated to the issue?
   - If yes, remove those changes

2. **Formatting Changes**: Did you reformat unrelated code?
   - If yes, revert formatting-only changes

3. **Refactoring**: Did you refactor code that wasn't part of the issue?
   - If yes, revert refactoring changes

4. **Feature Additions**: Did you add features not requested?
   - If yes, remove feature additions

5. **Style Changes**: Did you change code style globally?
   - If yes, revert style-only changes

6. **Documentation**: Did you update documentation unnecessarily?
   - If yes, revert unrelated doc changes

## Action Required:

Use 'git_diff' to review all changes.
If you find scope violations:
1. Identify the violating changes
2. Revert or remove them
3. Keep only changes directly related to the issue
4. Re-test to ensure fix still works

Remember: A focused PR is more likely to be merged quickly."""
