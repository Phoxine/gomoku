---
name: fix-issue
description: Investigate and fix a reported issue, including regression testing and review.
---

# Fix Issue Workflow

1. Read the issue description and reproduction steps.
   If the report starts with a failed GitHub Actions check, use the [CI failure diagnosis reference](references/ci-failure-diagnosis.md) to find the failed attempt and classify it. Continue at step 2 when the diagnosis calls for a repository change. Otherwise, follow the reference's next action and report the outcome.
2. Identify the related files.
3. Write a failing test first or add a regression test.
4. Update the code to fix the issue.
5. Run the relevant tests.
6. Review the Git diff.
7. Provide a summary of the fix and describe any risks.
