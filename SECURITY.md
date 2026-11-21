# Security Policy

RelaySelf is in early architectural bootstrap. Security reporting and support policy should remain explicit as implementation and release surfaces are introduced.

## Reporting a vulnerability

Do **not** publish exploit details, secrets, credentials, private endpoints, or reproducible attack payloads in a public Issue, Discussion, or pull request.

If this repository exposes GitHub private vulnerability reporting in the **Security** tab, use that channel.

If no private reporting channel is available, open a minimal public Issue titled `Security contact request` without sensitive technical details. Include only enough information to establish that a private follow-up route is needed.

## Scope

Security-relevant reports may include, when those surfaces exist:

- authorization or authority-boundary bypasses;
- unintended persistent-state mutation;
- unsafe action authorization or environment-boundary behavior;
- injection paths that convert untrusted/model-produced content into authority;
- secrets or credential exposure;
- dependency, packaging, CI, or release-pipeline vulnerabilities;
- denial-of-service or resource-exhaustion issues with a concrete supported surface.

Ordinary model-quality disagreements, speculative future risks without a concrete affected surface, and general feature requests belong in normal Issues rather than security reporting.

## Supported versions

No versioned support matrix is declared at this bootstrap stage. When supported releases exist, this section must be updated to identify which versions receive security fixes.

## Handling accidentally exposed secrets

If a real credential or secret is committed or disclosed, treat it as compromised. Revoke or rotate it at the source; deleting or rewriting repository history alone is not sufficient remediation.

## Disclosure

Please allow time for triage and remediation before public disclosure of a confirmed vulnerability. Security fixes must still follow the repository's authority, review, and verification rules; urgency does not convert unverified claims into implementation facts.
