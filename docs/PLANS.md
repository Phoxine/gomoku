# Execution Plans

Create a versioned execution plan when work spans multiple sessions, introduces a complex feature with independently verifiable milestones, or makes a major refactor across components. For a small change that fits in one session, a short plan in the task or pull request is enough when useful.

## Where plans live

Start a Markdown plan in `docs/exec-plans/active/`. When all acceptance checks pass, record the outcome and retrospective, then move the file to `docs/exec-plans/completed/`. Update any links that point to the old path and verify relative links after the move. The two directories are siblings, so links from a plan to other project files can usually stay the same.

The completed [knowledge base maintenance plan](exec-plans/completed/knowledge-base-maintenance.md) is the first example.

## What to include

- **Goal and scope.** State what someone will be able to do after the change. Explain relevant context, define project-specific terms, and link to the source files, contracts, and tests needed to start.
- **Milestones and work steps.** Identify the order of work, the files or components affected, and commands with their working directories. Give each milestone a concrete result.
- **Validation and acceptance.** Show exactly how to confirm each result, including expected output or behavior. Include a failure case when it helps demonstrate that a check catches the intended problem.
- **Recovery.** When work can fail partway or change state, explain how to inspect the current state, resume or retry safely, and undo a partial change if needed. Follow the project's worktree and delivery rules.
- **Progress, discoveries, and decisions.** Keep a dated progress checklist that distinguishes completed and pending work. Record unexpected behavior with evidence and explain why consequential decisions were made. Update these sections at milestones and before handing off the work.
- **Outcomes and retrospective.** Record the validation results, remaining gaps, and lessons from the work. If a follow-up leaves technical debt, record it in `docs/exec-plans/tech-debt-tracker.md` with its impact, evidence, and a concrete next step.

A new contributor should be able to resume from the plan and the checkout alone. When a conversation or PR review settles a decision that affects future work, record what was decided, why, and any constraints in the owning specification, design, or development guide. Link to the implementation and the checks a future contributor can run. Link to the owning document from the plan when the decision affects a milestone.

See the [Cookbook guide to versioned execution plans](https://developers.openai.com/cookbook/articles/codex_exec_plans).

## Pull request scope

When the task is to write or revise an execution plan as a standalone deliverable, use a `plan/<task-slug>` branch. Follow the [worktree setup and branch naming rules](../.agents/skills/create-worktree/SKILL.md). When a task includes implementing the planned work, choose the branch prefix for the implementation.

When an execution plan contains changes that can be independently reviewed, validated, and merged, deliver them in separate pull requests. Each PR should have one coherent purpose and include the tests and documentation needed to verify its change.

Record the intended PRs in the plan. For each PR, list the milestones or deliverables it covers, its acceptance checks, and any dependencies that affect merge order. Update the plan if the split changes during implementation.

Keep related changes in one PR when they need to land together for correctness or compatibility. Record the reason in the plan.
