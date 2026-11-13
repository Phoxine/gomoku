---
name: create-pr
description: Prepare, validate, push, and open a GitHub pull request for changes in this repository when the user asks to create or submit a PR.
---

# Create a Pull Request

Follow this workflow when the user asks to push changes and open a GitHub pull request (PR). Do not merge the PR unless the user explicitly asks.

## 1. Confirm the worktree and branch

- Run `git status --short`, `git branch --show-current`, and `git worktree list` from the intended worktree.
- Do not create a PR from `main` or another protected base branch. If the user is on `main`, identify task-specific local commits and uncommitted changes, including untracked files, then create an isolated task branch from synchronized `origin/main` using the repository's worktree workflow. Cherry-pick only task-specific commits and copy only task-specific uncommitted changes to that branch. Confirm the transfer is complete and the original `main` checkout remains unchanged before continuing; leave unrelated changes out.
- Follow the branch prefixes in `AGENTS.md`: `feature/gomoku-<task>` for product features, `infra/<task>` for development tooling or infrastructure, `fix/<task>` for bug fixes, `docs/<task>` for documentation, and `refactor/<task>` for refactoring without functional changes.
- If the branch or worktree already exists, inspect it before reusing it. Do not overwrite, reset, or discard user changes.
- Inspect the full diff against the intended base branch. Confirm that only task-related files are included. Never stage or commit `.env`, `*.pem`, `*.key`, credentials, or unrelated user changes.

## 2. Prepare an atomic commit

- If there are uncommitted task changes, review them and stage only the intended files.
- Keep each commit focused on one coherent change and use a concise, descriptive commit subject. Do not impose a commit prefix convention that the repository has not adopted.
- If unrelated changes are present, leave them untouched and exclude them from the commit. Ask the user only when the intended PR scope cannot be determined safely.
- Before committing, run `git diff --cached --check` and review the staged diff.

## 3. Validate before pushing

- Use the isolated Docker Compose environment assigned to this worktree. Never point commands at another worktree's project or database.
- Before every push, ensure this worktree's Compose services are running with `bash scripts/compose.sh up --build -d`, then run `bash .codex/hooks/stop-validation.sh`.
- The Stop hook runs formatting, lint, and the full test suite against this worktree's app container. If it fails, fix the issue in this branch and rerun the hook until it passes. If it prints `Skipping final validation`, validation did not run, even if the hook exits successfully. Do not push. Resolve the Compose startup issue, confirm `app` appears in `bash scripts/compose.sh ps --status running --services`, then rerun the hook and confirm formatting, lint, and tests completed without being skipped.
- Run `git diff --check` and confirm the working tree contains no unintended changes before pushing.

## 4. Push the branch

Push the current task branch and set its upstream:

```bash
git push -u origin HEAD
```

If the push fails, leave the Compose environment running for further work. After a successful push, stop and remove this worktree's containers and network while retaining its database volume:

```bash
bash scripts/compose.sh down
```

Never run `down -v` unless the user explicitly authorizes deleting this worktree's database data.

## 5. Create the PR

- Use `.github/pull_request_template.md` as the PR body format. Preserve its headings, explanatory comments, checklist items, and order; fill in the summary, change type, related issues, and validation details. Include the optional Screenshots / Notes section even when it has no content. Use the following format only if the repository template is unavailable:

  ````markdown
  ## Summary
  <!-- Describe what this PR changes and the problem it solves. -->
  -

  ## Type of Change
  <!-- Mark the relevant option with an "x" -->
  - [ ] `feature`: New product feature
  - [ ] `fix`: Bug fix
  - [ ] `infra`: Development tooling, CI/CD, or infrastructure
  - [ ] `docs`: Documentation updates
  - [ ] `refactor`: Code refactoring without functional changes

  ## Related Issues
  <!-- Link related issues if applicable, e.g., Closes #123 -->
  -

  ## Validation
  <!-- List the checks, linters, and test suites that passed in the isolated worktree environment. -->
  - [ ] Passed `.codex/hooks/stop-validation.sh` (formatting, lint, and test suite)
  - [ ] Verified diff against `origin/main` (no `.env`, secrets, or unrelated changes included)

  ## Screenshots / Notes (Optional)
  <!-- Add screenshots, API response examples, or deployment notes if helpful for reviewers. -->
  ````

- Format the PR title as `<type>(<scope>): <description>`, for example, `feature(auth): add user login`. Use `feature`, `fix`, `infra`, `docs`, or `refactor` as the type, and keep the description concise and focused on the change.
- Check for an existing PR for the branch before creating one. Target `main` unless the user or repository workflow specifies another base.
- Create the PR with the GitHub CLI, for example:

  ```bash
  gh pr create --base main --head "$(git branch --show-current)" --title "<title>" --body-file <body-file>
  ```

- Report the PR URL, branch, validation results, and any relevant limitation to the user. Do not merge the PR unless explicitly requested.
