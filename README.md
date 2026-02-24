# predicate-secure

Drop-in security wrapper for AI agents. Adds authorization, verification, and audit to any agent framework in 3 lines of code.

## Features

- **Pre-action authorization** - Policy engine gates every action before execution
- **Post-execution verification** - Deterministic predicate checks (no LLM-as-a-judge)
- **Cryptographic audit** - WORM-ready receipts linking intent to outcome
- **Zero refactoring** - Wrap your existing agent, keep your framework

## Installation

```bash
pip install predicate-secure
```

With framework-specific extras:

```bash
pip install predicate-secure[browser-use]
pip install predicate-secure[langchain]
pip install predicate-secure[playwright]
pip install predicate-secure[all]
```

## Quick Start

```python
from predicate_secure import SecureAgent
from browser_use import Agent

# 1. Your existing agent (unchanged)
agent = Agent(task="Buy headphones on Amazon", llm=my_model)

# 2. Wrap with SecureAgent
secure_agent = SecureAgent(
    agent=agent,
    policy="policies/shopping.yaml",
    mode="strict",
)

# 3. Run with full authorization + verification
secure_agent.run()
```

## Modes

| Mode | Behavior |
|------|----------|
| `strict` | Fail-closed: deny action if policy check fails |
| `permissive` | Log but don't block unauthorized actions |
| `debug` | Human-readable trace output for debugging |
| `audit` | Record decisions without enforcement |

## Supported Frameworks

| Framework | Status |
|-----------|--------|
| browser-use | Supported |
| LangChain | Supported |
| Playwright | Supported |
| PydanticAI | Supported |
| OpenClaw | Planned |

## Architecture

`predicate-secure` is a thin orchestration layer that combines:

- **predicate** (sdk-python) - Snapshot engine, DOM pruning, verification predicates
- **predicate-authority** (AgentIdentity) - Policy engine, mandate signing, audit logging

```
SecureAgent
    ├── AgentRuntime (snapshot, assertions)
    ├── AuthorityClient (policy, mandates)
    └── RuntimeAgent (orchestration, pre-action hook)
```

## Policy Example

```yaml
# policies/shopping.yaml
rules:
  - action: "browser.*"
    resource: "https://amazon.com/*"
    effect: allow

  - action: "browser.click"
    resource: "*checkout*"
    effect: allow
    require_verification:
      - url_contains: "/checkout"

  - action: "*"
    resource: "*"
    effect: deny
```

## Development

```bash
# Install dev dependencies
make dev-install

# Install pre-commit hooks
make hooks

# Run tests
make test

# Run linters
make lint
```

## License

Dual-licensed under MIT or Apache-2.0. See [LICENSE](./LICENSE).
