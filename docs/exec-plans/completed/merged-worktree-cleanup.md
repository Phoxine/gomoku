# Merged Worktree Cleanup

## Goal and scope

Plan a safe end-of-task cleanup procedure. The [PR skill](../../../.agents/skills/create-pr/SKILL.md) already stops Compose containers after pushing and retains the database volume. The remaining task is deciding whether a merged task's worktree and local or remote branches are safe to remove. The merged branch can have a different commit ID after a squash, and someone can push again after the merge. [Worktree isolation](../../../.agents/skills/create-worktree/references/multi-session-worktrees.md) · [Authorization boundaries](../../../AGENTS.md)

## Milestones

1. Start with the skill's [read-only inventory](../../../.agents/skills/merged-worktree-cleanup/SKILL.md#inventory-and-verify). Record each candidate's path, branch or detached HEAD, local head, target and remote refs, and GitHub merge evidence. Fetch the intended base and query the current remote tip using literal Git arguments before making a decision.
2. Define the eligibility checks. For a regular merge, verify the exact candidate tip is reachable from the synchronized target using `git merge-base --is-ancestor`. For a squash merge, match the same repository, base, merged PR head commit, and resulting merge commit on the target. Compare local and remote tips separately with the verified history. Hold candidates with dirty or untracked files, unresolved identity, a detached HEAD, or unmerged commits. An open or closed-unmerged PR alone provides no merge evidence.
3. Draft a dedicated cleanup skill and test it on disposable worktrees and a temporary remote. Produce a list of proposed actions first, with separate approvals for worktree removal and any branch deletion. Protect ignored local files as well as tracked files. Removing the checkout can also remove its private Compose settings, so choose a secure recovery method for the original worktree configuration before removing a checkout whose database volume must remain usable. Keep the worktree if that prerequisite is unresolved. Verify ownership before stopping the stack, retain its volume, and recheck refs and worktree changes immediately before authorized removal. Require remote deletion to match the approved exact remote commit through an explicit expected-SHA lease or an equivalent conditional deletion. If the ref changes or the remote cannot enforce the condition, leave the remote branch in place. Report an interrupted cleanup before retrying and inspect which actions already succeeded. [Git push lease semantics](https://git-scm.com/docs/git-push)

## Acceptance and pull requests

- **Cleanup skill PR.** Validate using the [skill validation workflow](../../../.agents/skills/validate-skill/SKILL.md). Exercise clean merge and squash cases, dirty and untracked cases, and an unapproved deletion. In a disposable remote, advance the candidate after verification and confirm conditional deletion fails and leaves the new tip in place. The inventory may refresh remote-tracking refs and must leave checkouts, local and remote branches, and Compose resources intact. For a fixture where approval is given, confirm only the approved targets are removed and its volume remains. Use a test fixture or a disposable local Compose project. Keep live worktree cleanup separate from the skill PR.
- Consider a separate tooling PR only if repeated manual dry runs reveal a specific need. Test any executable safeguards against passing and rejected fixtures.

## Validation and delivery

Work from a dedicated checkout for implementation. Record `git status --short` and `git rev-parse HEAD` before starting. If tests need the app, initialize and start an isolated stack using the [worktree skill](../../../.agents/skills/create-worktree/SKILL.md). Run `bash scripts/check-docs.sh` after staging Markdown changes. Complete [pre-push validation](../../../.agents/skills/create-pr/SKILL.md#3-validate-before-pushing) and confirm the Stop hook did not skip formatting, lint, or tests. Follow the [post-push cleanup procedure](../../../.agents/skills/create-pr/SKILL.md#4-push-the-branch).

## Progress and decisions

- [x] 2026-11-20. Reviewed the existing workflow and defined scope at `eff8579`.
- [x] 2026-11-24. Inventoried normal and squash merges, separate local and remote tips, and modified, untracked, and ignored paths in disposable Git repositories.
- [x] 2026-11-24. Added the [merged worktree cleanup skill](../../../.agents/skills/merged-worktree-cleanup/SKILL.md) and tested approval boundaries, conditional remote deletion, and volume retention.

## Outcomes and retrospective

An independent dry run found both merge types and held dirty or untracked worktrees and a remote tip that advanced beyond the squash head. It left checkouts, local branches, remote branches, and ignored files intact without deletion approval. A remote ref query can also match names with the same suffix, so the skill requires an exact field comparison. A configured fetch mapping can update local branches, so the skill fetches the target with an empty ref map.

In a temporary bare remote, the explicit SHA lease rejected deletion after a new commit was pushed and preserved the new tip. A matching lease deleted only the approved remote ref and left the local branch intact. A separate fixture removed the approved worktree and local branch and preserved another checkout and its remote branch. Its disposable Compose volume retained test data after shutdown and restart.

The repository maintainer approves each live action and confirms recovery of private worktree settings when needed. Keep the worktree when Compose ownership, successful shutdown, or volume retention cannot be confirmed. The validation used a local remote and disposable Compose project. Revisit tooling if repeated manual dry runs reveal a specific need.
