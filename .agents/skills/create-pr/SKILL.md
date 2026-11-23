---
name: create-pr
description: Validate, push, and open or update a GitHub pull request when delivering completed code or tracked documentation changes, or when the user asks to submit a PR.
---

# Create a Pull Request

Follow the [repository delivery policy](../../../AGENTS.md#git-and-pull-request-workflow) for completed changes and any explicit delivery limits. Use this workflow when the user asks to open or submit a GitHub pull request (PR) as well. Merge only with explicit authorization.

## 1. Confirm the worktree and branch

- Run `git status --short`, `git branch --show-current`, and `git worktree list` from the intended worktree.
- Do not create a PR from `main` or another protected base branch. If the user is on `main`, identify task-specific local commits and uncommitted changes, including untracked files, then create an isolated task branch from synchronized `origin/main` using the repository's worktree workflow. Cherry-pick only task-specific commits and copy only task-specific uncommitted changes to that branch. Confirm the transfer is complete and the original `main` checkout remains unchanged before continuing; leave unrelated changes out.
- Follow the branch naming rules in the [create-worktree skill](../create-worktree/SKILL.md).
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
- If a validation fix changes repository files, review and commit those fixes as in step 2 before rerunning the full hook. Before pushing, confirm that all repository inputs used by validation, including source, tests, and configuration such as `pyproject.toml`, match the commit being pushed. If any inputs differ, rerun the full validation against the intended commit without including unrelated changes.
- Run `git diff --check` and confirm the working tree contains no unintended changes before pushing.

## 4. Push the branch

Push the current task branch and set its upstream:

```bash
git push -u origin HEAD
```

If the push fails, leave the Compose environment running for further work. After a successful push, stop and remove this worktree's containers and network while retaining its database volume. If the host cleanup helper is configured, use its literal absolute-path invocation from the [host prerequisites](../../../docs/codex/prerequisites.md#optional-allow-routine-compose-cleanup-without-a-prompt). Otherwise, use the repository script:

```bash
bash scripts/stop-local-stack.sh
```

For a legacy Compose project name, verify that the project belongs to the current worktree before using `bash scripts/compose.sh down`.

Obtain explicit authorization before deleting the worktree's database volume, including with `down -v`, `down --volumes`, or direct volume removal.

For a push-only request, report the push and stop after cleanup. Continue to step 5 when PR delivery is in scope.

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
  - [ ] `plan`: Standalone execution plan creation or revision
  - [ ] `refactor`: Code refactoring without functional changes

  ## Related Issues
  <!-- Link related issues if applicable, e.g., Closes #123 -->
  -

  ## Validation
  <!-- List the checks, linters, and test suites that passed in the isolated worktree environment. -->
  - [ ] Passed `.codex/hooks/stop-validation.sh` with formatting, lint, and tests completed (confirm no `Skipping final validation` message; a successful exit alone is insufficient)
  - [ ] Verified diff against `origin/main` (no `.env`, secrets, or unrelated changes included)
  - [ ] Checked documentation against the implementation for changes to API behavior, database schemas, or game rules (if applicable)

  ## Screenshots / Notes (Optional)
  <!-- Add screenshots, API response examples, or deployment notes if helpful for reviewers. -->
  ````

- Format the PR title as `<type>(<scope>): <description>`, for example, `feature(auth): add user login`. Use `feature`, `fix`, `infra`, `docs`, `plan`, or `refactor` as the type, and keep the description concise and focused on the change. Use `plan` as the change type for standalone execution plan creation or revision. When the PR also implements the plan, use the type for the implementation.
- Determine the target base branch from the user's request or repository workflow, defaulting to `main`. Check for an open PR whose head matches the repository and branch just pushed and whose base matches the selected target. Reuse a matching PR and report its URL. If none matches, create a PR with the selected base.
- Use the selected base in both GitHub CLI commands. For example, for a same-repository PR targeting `main`:

  ```bash
  base_branch=main
  head_branch="$(git branch --show-current)"
  gh pr list --state open --base "$base_branch" --head "$head_branch" \
    --json url,isCrossRepository --jq '.[] | select(.isCrossRepository == false) | .url'
  # Run only if no open PR matches.
  gh pr create --base "$base_branch" --head "$head_branch" --title "<title>" --body-file "<body-file>"
  ```

- Report the PR URL, branch, validation results, and any relevant limitation to the user. Do not merge the PR unless explicitly requested.
