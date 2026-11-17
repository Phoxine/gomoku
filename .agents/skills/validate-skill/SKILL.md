---
name: validate-skill
description: Validate new or modified agent skills, or assess skills and AGENTS.md for clarity, overlap, and behavior.
---

# Validate and refine skills

Use this workflow when creating or modifying a project skill, or when asked to assess or streamline skills or their division of responsibility with AGENTS.md. Establish the requested scope and whether changes are authorized; an assessment alone is read-only. Inspect the target instructions, references, relevant neighboring skills, and applicable repository instructions before recommending changes.

- Check that the name and description identify the intended task and distinguish neighboring skills. Check frontmatter, links, and referenced resources; run an available skill validator when appropriate.
- Identify duplicated, generic, obsolete, conflicting, or overly broad instructions. Retain project-specific constraints and useful decision points; do not remove requirements solely to reduce length. Propose merging or removing a skill only with evidence of overlap and regard changes to other skills as separate scope.
- When assessing AGENTS.md alongside skills, retain broadly applicable project constraints, authorization boundaries, and routing instructions there; place task-specific procedures in discoverable skills where appropriate. Check that moved instructions remain reachable when needed, including workflows that can occur independently of another skill. Identify any behavioral change or coverage gap before proposing a move. Follow the repository's approval requirements for modifying AGENTS.md.
- Choose realistic in-scope and out-of-scope requests, including relevant boundary cases. Assess whether the instructions lead to the intended decisions and preserve user authorization. For consequential or complex changes, use independent forward-testing when available and authorized, with an isolated workspace and no unintended external side effects. Do not claim execution or automatic selection was tested if it was only inspected.
- If changes are requested, make focused corrections and repeat the relevant checks. Report findings, changes, evidence, and untested limitations; distinguish structural checks from observed behavior.

When creating or updating a skill, follow the available skill-creator guidance. This workflow evaluates skills; `validate-subagent` covers subagent registration and dispatch.
