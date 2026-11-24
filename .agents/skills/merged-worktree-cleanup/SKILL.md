---
name: merged-worktree-cleanup
description: Inventory and safely retire merged Gomoku task worktrees and their local or remote Git branches. Use for post-merge cleanup or a dry run to decide what can be removed.
---

# Merged worktree cleanup

Use the [PR delivery workflow](../create-pr/SKILL.md#4-push-the-branch) for routine Compose shutdown after a push. Use this skill to decide which Git worktrees and branches can be retired after their work is integrated.

## Pass inventory values as arguments

Treat Git and Docker output, branch names, and paths as data. Use a tool that passes arguments separately when available. For shell commands, load values into variables from the parsed inventory or another literal input channel, then expand them in double quotes as shown below. Keep the command text fixed, including variable assignments. Never paste discovered values into command text, use `eval`, or pass generated text to `sh -c`. If the tool cannot preserve a value as one literal argument, hold the action.

In the examples, `remote` is a verified configured remote name, `target_ref` and `branch_ref` are verified full refs under `refs/heads/`, `branch_name` is the corresponding local branch name, and `worktree_path` is the verified absolute path. Verify full refs with `git check-ref-format "$branch_ref"` or the corresponding target variable. Use full commit SHAs obtained from verified Git results.

## Inventory and verify

1. From a retained checkout, run `git worktree list --porcelain -z` and inspect each candidate by absolute path. Record the branch, full local commit, lock state, and target branch. Run `git -C "$worktree_path" status --porcelain=v1 --untracked-files=all --ignore-submodules=none`. Check ignored paths separately by name using `git ls-files --others --ignored --exclude-standard` in the candidate. Run `git ls-files -v -z` and hold the checkout if an entry is tagged `S` or lowercase. Skip-worktree and assume-unchanged flags can hide local changes from status. Ask the owner to resolve the flags before rechecking. Hold a candidate with tracked changes, untracked files, a lock, a detached HEAD, ongoing work, or unverified branch identity. Exclude the main checkout, protected branches, and the checkout serving the current session.
2. Confirm the repository, integration target, and remote identity. Run `git fetch --no-tags --no-prune --no-recurse-submodules --refmap= -- "$remote" "$target_ref"`. The empty ref map prevents configured fetch mappings from updating branch refs. Capture `FETCH_HEAD` and compare it to the remote's exact target SHA. Use `git ls-remote --refs -- "$remote" "$target_ref"` for the target and `git ls-remote --refs -- "$remote" "$branch_ref"` for a candidate. Git matches ref suffixes, so accept only a row whose second tab-separated field equals the full requested ref. Treat a ref as missing only after a successful query with no exact match. Use the same check after deletion. Record the confirmed fetch and push destination without exposing credentials. Keep worktrees, local branches, remote branches, and Compose resources intact during inventory.
3. Check the local and remote tips independently. For a regular merge, require `git merge-base --is-ancestor "$tip_sha" "$target_sha"` to succeed for the exact candidate tip. If history is shallow or the commit is unavailable, get enough history to verify it or hold the candidate.
4. For a squash merge, confirm that a merged PR for the same source and target repositories and branch names integrated the exact candidate tip. Record the PR number, merge-time head SHA, and resulting commit, then confirm that the resulting commit is reachable from the synchronized target. Establish the head from the merged PR's commit record or other evidence tied to the merge. A mutable branch tip, matching branch names, or a PR closed without merging cannot establish this. Hold any tip beyond the verified merge evidence. Evaluate worktree removal against its local tip and checkout state, even when the remote branch must stay.

## Propose actions

- Report each candidate, the evidence and any hold reason, and the exact proposed action. List worktree removal, local branch deletion, and remote branch deletion separately, including the path or repository and ref, the full SHA the user is authorizing, and the expected volume disposition.
- Obtain explicit user approval for each proposed removal or deletion. A dry run, an approval for another target, or a request to push changes provides no deletion authorization. Respect the [repository authorization rules](../../../AGENTS.md).
- Inspect ignored paths by metadata only. The owner must confirm how needed files will be recovered, or explicitly confirm that identified disposable files can be removed. In particular, preserve a secure way to restore the worktree's original Compose identity and private settings before removing any checkout whose volume must remain usable. Have the owner handle private settings through an approved secure process. Keep the worktree if recovery remains unresolved. Follow the [security rules](../../../.codex/rules/security.md) and [worktree isolation guide](../create-worktree/references/multi-session-worktrees.md).

## Apply approved actions

1. Coordinate with the owner so this checkout and its branches are idle. Before each action, recheck the exact path, status including ignored paths, worktree registrations, local and remote refs, target merge evidence, and approvals as applicable. Pause on changed evidence and refresh the proposal. Check for other worktrees or active PRs using a branch before deleting it.
2. Before removing a worktree, verify ownership of any Compose resources and record any existing database volume by name. Confirm that no owned stack needs shutdown, or use the [volume-preserving shutdown](../create-pr/SKILL.md#4-push-the-branch) from the candidate checkout and verify it succeeded. Verify that no owned containers remain and that any previously identified database volume still exists. If ownership, shutdown, or volume retention cannot be confirmed, keep the worktree and report the action as pending. Once confirmed, recheck status, index flags, and ignored paths, then use `git worktree remove -- "$worktree_path"` from the retained checkout without force. Stop if Git refuses.
3. For an approved local deletion, coordinate with all local writers so the branch cannot move between verification and deletion. Keep the branch if exclusive access cannot be established. Verify the branch still points to the approved commit and is absent from all worktree checkouts, then try `git branch -d -- "$branch_name"`. If Git refuses because it cannot recognize the verified integration, explain why to the user. Use `git branch -D -- "$branch_name"` only with explicit authorization for the forced deletion, fresh merge evidence for the exact local tip, and the same exclusive access. Respect Git's worktree protections.
4. For an approved remote deletion, use a single verified non-mirror push destination that matches the repository inspected during inventory. Use the approved full `branch_ref` and `approved_sha` as argument values. Keep the explicit expected SHA even if a fetch has refreshed the remote-tracking ref. [Git push lease semantics](https://git-scm.com/docs/git-push)

   ```bash
   git -c push.followTags=false push --porcelain --recurse-submodules=no \
     --force-with-lease="${branch_ref}:${approved_sha}" \
     -- "$remote" ":${branch_ref}"
   ```

   If the ref changed, the server rejected the lease, or conditional deletion is unavailable, leave the remote branch in place. Confirm successful removal with a fresh exact-ref query.

5. Report completed, refused, and pending actions, including whether the volume remains. If interrupted, inspect actual paths, refs, and Compose resources before retrying. Reuse approval only for actions whose targets and evidence still match.
