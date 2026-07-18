# Branch Protection and Required Checks

Agent Machine has a green PR-triggered validation lane. Branch protection is still a release-gate follow-up because required checks should not be configured until the expected check name and workflow visibility are stable.

## Required check

Current validation workflow:

```text
validate
```

Current required job name candidate:

```text
Validate contracts, examples, CLI, formula, and docs
```

Canonical local command:

```bash
make validate
```

## Recommended branch protection for `main`

Recommended settings once main-branch visibility is confirmed:

- require pull request before merging;
- require status checks to pass before merging;
- require the `validate` workflow/job;
- require branches to be up to date before merging if the repository starts receiving concurrent changes;
- restrict bypasses to repository administrators only when emergency remediation is needed;
- do not require signed commits until the signing policy is documented and tested;
- do not require linear history unless the repo standardizes on squash-only merges.

## Current CI proof

Known green proof:

```text
PR #9
workflow run: 25322297618
job: Validate contracts, examples, CLI, formula, and docs
command: make validate
```

Supply-chain strict-mode proof:

```text
PR #11
workflow run: 25327418937
job: Validate contracts, examples, CLI, formula, and docs
command: make validate
```

Release bundle proof:

```text
PR #14
workflow run: 25335379781
job: Validate contracts, examples, CLI, formula, and docs
command: make validate
```

## Open issue

Tracked by:

```text
Issue #10: Add branch protection and required validation checks for Agent Machine
```

## Why not close yet

The connector can see PR-triggered runs. Main-branch push workflow visibility has been inconsistent or unavailable through the connector/API path. Branch protection should be configured after the required check appears consistently for the protected branch, or after the UI confirms the check can be selected.
