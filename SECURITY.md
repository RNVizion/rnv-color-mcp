# Security Policy

This project is a hosted MCP server with an OAuth 2.1 resource-server layer. Reports about the
server, its authorization logic, or its deployment are welcome.

## Before you report: the public endpoint runs with authentication disabled, deliberately

The live server at `https://rnvizion-rnv-color-mcp.hf.space/mcp` accepts unauthenticated requests.
This is a design decision, not an oversight.

The OAuth 2.1 layer is implemented, tested, and enforced when enabled — but it is opt-in by
environment switch (`RNV_AUTH`), and that switch is not set in production. The server is a public
demo with no user data and no private state; requiring a token would break every zero-setup arrival
from the MCP registry for no protection worth having. Confirming this is easy:
`/.well-known/oauth-protected-resource/mcp` returns 404, which is the correct signal that auth is
off.

So: "the server does not require a token" is not a vulnerability report. **"The server enforces
scopes incorrectly when auth is on" is**, and that is exactly the kind of finding this policy exists
for.

## Supported versions

There is one deployment, and it runs whatever is on `main`. Version tags mark releases for the MCP
registry; they are not maintained branches, and there is no long-term-support line. Fixes land on
`main` and reach production through the deploy workflow, which will not push unless the test suite
passes.

## Reporting a vulnerability

**Do not open a public issue for a security vulnerability.**

Email **security@rnvizion.dev**. If GitHub private vulnerability reporting is enabled on this
repository ("Report a vulnerability" under the Security tab), that works too and is preferred — it
keeps the report structured and private.

Please include: a description of the issue, steps to reproduce, the affected commit or deployed
version, and the impact as you see it.

## What to expect

- **Acknowledgment within seven days.** This project has one maintainer working around a day job and
  intermittent power. Seven days is a range that will be met rather than a promise that sounds good.
- A coordinated fix, with a disclosure timeline agreed with you before anything is made public.
- Credit for the report, if you want it.
- Public disclosure once a fix ships, as a GitHub Security Advisory on this repository.
- **No bounty.** This is an unfunded personal project. Reports are valued; they are not paid.

## Scope

**In scope**

- The MCP server and its nine tools, including input handling and the color-name resolver.
- The OAuth 2.1 resource-server layer: token validation, audience and issuer binding, and per-tool
  scope enforcement when `RNV_AUTH` is set.
- The RFC 9728 protected-resource metadata endpoint and the `WWW-Authenticate` challenge.
- The palette store and its write-through persistence, including anything that would let a caller
  read or destroy palettes they should not reach.
- The deployment pipeline as it affects this repository.

**Out of scope**

- **Third-party rebuilds hosted elsewhere.** Only the deployment listed above is this project's; a
  fork someone else stood up is theirs to secure and theirs to answer for.
- **The Hugging Face platform itself.** Report those to Hugging Face.
- **The self-issued development keypair.** `tests/gen_test_key.py` generates a throwaway RSA key so
  the test suite can mint its own tokens with no external identity provider and no stored
  credential. It is test scaffolding, never a production key, and no key material is committed.
- Findings that require the reporter to already hold a valid token with the scope in question.
- Denial of service by volume against a free-tier host.

## Secrets and credentials

No credential is committed to this repository, and the test suite requires none — it generates its
own keys and the shared fixture strips any inherited token so tests cannot touch real data.

Live credentials exist only as Hugging Face Space secrets and GitHub Actions encrypted secrets, each
scoped to a single purpose. Any suspected exposure is handled by rotation, not by patching around
it.

If you believe a credential has leaked, that is in scope and worth an email even if you are not
sure.
