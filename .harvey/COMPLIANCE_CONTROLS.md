# Harvey Elite Compliance Controls
- Enforce least-privilege access for legal datasets and filing artifacts.
- Require immutable audit logs for retrieval, transformation, and filing events.
- Block outbound responses containing unredacted PII/PHI unless explicitly approved.
- Require jurisdiction tagging for every drafted motion, response, and exhibit.
- Record citation lineage for each legal assertion used in generated output.
- Require human sign-off prior to any final civil/criminal filing export.
- Enforce PACER, Westlaw, and LexisNexis terms-of-service and account-use restrictions.
- Require manual MFA step when providers enforce additional authentication challenges.
- Disable plain-text credential storage; use environment variables and local secret files only.
