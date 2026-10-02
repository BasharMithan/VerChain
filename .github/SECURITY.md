# Security Policy

## Supported Versions

Security fixes are provided for the following versions of VerChain:

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| < 0.3   | :x:                |

If you are using an unsupported version, please upgrade to the latest
release before reporting an issue.

## Reporting a Vulnerability

We take the security of VerChain seriously. If you discover a potential
security vulnerability, please report it privately.

**Do not open a public GitHub issue for security vulnerabilities.**
Public disclosure before a fix is available could put VerChain users,
Credential data, wallets, or deployed contracts at risk.

### Preferred reporting method

Use GitHub's private vulnerability-reporting feature:

1. Open the VerChain repository on GitHub.
2. Open the **Security** tab.
3. Select **Report a vulnerability**.
4. Provide the details requested below.

If private reporting is not enabled, contact the maintainers at:

`basharmithan@proton.me`

Replace this address with a real monitored inbox before publishing this file.

## What to Include

Please provide enough information for us to reproduce and assess the issue:

- A clear description of the vulnerability.
- The affected component, such as the Python API, smart contract, wallet integration, authentication flow, database, or frontend.
- The affected version, commit hash, branch, deployment network, or contract address.
- Reproduction steps or a minimal proof of concept.
- The expected behavior and the actual behavior.
- The potential impact, such as unauthorized Credential verification, access-control bypass, private-data exposure, signature replay, token theft, or denial of service.
- Suggested mitigations, if you have them.

Please do not include secrets, private keys, seed phrases, real Credential documents,
access tokens, or production credentials in your report.

## Scope

Examples of security issues that may be in scope include:

- Authentication or authorization bypasses.
- Broken Credential-verification or credential-validation logic.
- Exposure of personally identifiable information or sensitive verification data.
- Smart-contract vulnerabilities, including access-control errors, reentrancy,
  signature-validation flaws, replay attacks, or incorrect permission checks.
- Private-key, secret, API-key, or credential exposure.
- Injection vulnerabilities in APIs or databases.
- Cross-site scripting, cross-site request forgery, insecure redirects, or
  session-management flaws in web applications.
- Dependency vulnerabilities that materially affect VerChain.
- Denial-of-service vulnerabilities that can significantly affect the service.

The following are generally out of scope unless they create a demonstrable
security impact:

- Cosmetic issues or feature requests.
- Vulnerabilities only affecting obsolete or unsupported versions.
- Findings requiring physical access to a maintainer's device.
- Social-engineering attacks against project contributors.
- Rate-limit reports without a realistic, high-impact exploitation scenario.
- Vulnerabilities caused solely by third-party services outside VerChain's control.

## Testing Rules

When testing VerChain, please act responsibly:

- Test only accounts, wallets, contracts, APIs, and environments that you own
  or are explicitly authorized to test.
- Prefer local, development, or testnet environments.
- Do not access, modify, delete, or exfiltrate data belonging to other users.
- Do not disrupt VerChain services or conduct denial-of-service testing.
- Do not publish exploit details until we have had a reasonable opportunity to
  investigate and release a fix.
- Do not use a discovered vulnerability for financial gain, Credential fraud, or
  unauthorized access.

## Disclosure Process

After receiving a report, we aim to:

1. Acknowledge receipt within 7 days.
2. Assess the report and determine its severity.
3. Work with the reporter to reproduce and validate the issue.
4. Develop, test, and release a fix when needed.
5. Coordinate public disclosure after affected users have had an opportunity
   to update or mitigate the issue.

Response and remediation times may vary based on the severity, complexity,
and availability of maintainers.

## Recognition

With your permission, we may acknowledge your contribution in release notes,
a security advisory, or the project's acknowledgements.

## Contact

- GitHub private vulnerability reporting: Use the repository's **Security**
  tab, if enabled.
- Security email: `basharmithan@proton.me`
- General project issues: Use GitHub Issues for non-security bugs and feature
  requests only.
