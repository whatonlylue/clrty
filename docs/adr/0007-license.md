# 0007. License

Date: 2026-09-28
Status: Accepted

## Context

clrty will vendor the SlopCodeBench ast-grep rules (Build plan › Repository layout), which are Apache-2.0 licensed. The original SlopCodeBench code is MIT (Project Plan › Research findings). clrty's own code needs a license that is compatible with both upstream dependencies and the project's distribution goals.

## Options considered

**MIT:** Simple, permissive, matches the original SlopCodeBench license. Allows proprietary use and modifications with minimal restrictions.

**Apache-2.0:** More detailed, includes an explicit patent grant, and matches the license of the vendored SCB rules (Build plan › Assumed decisions). Ensures consistency across the codebase and provides stronger patent protection to users.

## Decision

**Apache-2.0.** This choice matches the vendored SCB rules and adds a patent grant (Build plan › Assumed decisions). The vendored rules must keep their Apache-2.0 notices, and adopting Apache-2.0 for the whole project simplifies license compliance.

## Consequences

Contributions are licensed under Apache-2.0 inbound and outbound (section 5). The NOTICE file credits the vendored SCB rules as Apache-2.0 (SCB's own code is MIT; only the rules clrty vendors carry the Apache-2.0 license). Users get stronger patent protection. The only downside is slightly longer license text, but this is standard for serious open-source projects and fits the academic rigor of the SlopCodeBench foundation.

The GitHub repository was initialised with an MIT LICENSE; it was replaced with Apache-2.0 on 2026-09-28 before any external contributions.
