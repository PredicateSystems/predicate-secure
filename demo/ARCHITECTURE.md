# Predicate Secure Demo Architecture

## Overview

This demo implements the complete **Pre-Execution Authorization + Post-Execution Verification** loop for AI agent browser automation, showcasing how predicate-secure integrates authorization and verification into a single cohesive security framework.

## Components

### 1. Pre-Execution Authorization Layer

**Implementation**: `predicate-authority` + `SecureAgent`

**Location**: `secure_browser_demo.py` → `_check_authorization()`

**Flow**:
```python
# Before any browser action
action = "navigate"
target = "https://example.com"

# Build authorization request
request = ActionRequest(
    principal=PrincipalRef(principal_id="agent:demo-browser"),
    action_spec=ActionSpec(
        action="browser.navigate",
        resource="https://example.com",
        intent="Navigate to example.com"
    ),
    state_evidence=StateEvidence(...),
    verification_evidence=VerificationEvidence(...)
)

# Check authorization against policy
decision = guard.authorize(request)

if not decision.allowed:
    raise PermissionError(f"Action denied: {decision.reason}")
```

**Policy Engine**:
- **File**: `policies/browser_automation.yaml`
- **Mode**: Fail-closed (deny by default)
- **Rules**: Define allowed principals, actions, resources, and required labels

**Key Features**:
- Action-level granularity (navigate, click, type, etc.)
- Resource-level granularity (domain patterns, element selectors)
- Label-based conditions (require evidence of prior state)
- Explicit deny rules for dangerous operations

### 2. Browser Automation Layer

**Implementation**: `PredicateBrowser` from sdk-python

**Location**: `secure_browser_demo.py` → `_init_browser()`

**Capabilities**:
- Playwright-based browser automation
- Sentience extension for ML-powered snapshots
- Support for headless/headed mode
- Element interaction (click, type, fill)
- Page navigation and snapshot capture

**Integration Point**:
```python
# Browser wrapped by SecureAgent
browser = PredicateBrowser(
    headless=False,
    api_key=None  # Free tier
)

# Every browser action goes through authorization
await self._authorized_action(
    action="navigate",
    target=url,
    executor=lambda: browser.goto(url)
)
```

### 3. Post-Execution Verification Layer

**Implementation**: `LocalLLMVerifier` with Qwen 2.5 7B

**Location**: `local_llm_verifier.py`

**Flow**:
```python
# After action execution, generate verification plan
verification_plan = verifier.generate_verification_plan(
    action="navigate",
    action_target="https://example.com",
    pre_snapshot_summary=pre_state,
    post_snapshot_summary=post_state,
    context={"task": "Navigate to example.com"}
)

# Execute generated verifications
for verification in verification_plan.verifications:
    result = execute_predicate(
        verification.predicate,
        verification.args
    )
    if not result:
        raise AssertionError("Verification failed")
```

**Verification Predicates**:
- `url_contains(substring)`: Check URL contains substring
- `url_changed()`: Check URL changed from pre-action state
- `snapshot_changed()`: Check page content changed
- `element_exists(selector)`: Check element present in DOM
- `element_visible(selector)`: Check element is visible
- `element_count(selector, min_count)`: Check element count

**LLM Prompt Strategy**:
- **System Prompt**: Define predicate vocabulary and output format
- **User Prompt**: Provide action context, pre/post state, and task intent
- **Output**: JSON with reasoning and verification specs
- **Temperature**: 0.0 (deterministic)

### 4. Orchestration Layer

**Implementation**: `SecureBrowserDemo` class

**Location**: `secure_browser_demo.py`

**Responsibilities**:
1. Initialize all components (verifier, secure agent, browser)
2. Execute actions with authorization + verification loop
3. Capture and compare pre/post action state
4. Log all decisions and verification results
5. Handle errors and cleanup

**Core Loop**:
```python
async def _authorized_action(self, action, target, executor):
    # 1. PRE-EXECUTION AUTHORIZATION
    authorized = self._check_authorization(action, target)
    if not authorized:
        raise PermissionError("Action denied")

    # 2. CAPTURE PRE-ACTION STATE
    pre_snapshot = self._get_page_summary()

    # 3. EXECUTE ACTION
    result = executor()

    # 4. CAPTURE POST-ACTION STATE
    post_snapshot = self._get_page_summary()

    # 5. POST-EXECUTION VERIFICATION
    verification_plan = self.verifier.generate_verification_plan(
        action, target, pre_snapshot, post_snapshot
    )

    # 6. EXECUTE VERIFICATIONS
    all_passed = self._execute_verifications(verification_plan)
    if not all_passed:
        raise AssertionError("Verification failed")
```

## Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    User Request                               │
│  "Navigate to example.com and verify page loads"             │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               SecureBrowserDemo.run_demo()                   │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌───────┐      ┌──────────┐    ┌─────────┐
    │ LLM   │      │ Secure   │    │ Browser │
    │ Verifier     │ Agent    │    │         │
    └───────┘      └──────────┘    └─────────┘
                         │
                         ▼
        ┌────────────────────────────────────────┐
        │  Action Loop: navigate, snapshot, ...  │
        └────────────────┬───────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌─────────┐   ┌─────────────┐   ┌──────────┐
    │ Pre-Auth│   │  Execute    │   │Post-Verify│
    │ Check   │→  │  Action     │→  │  Check   │
    └─────────┘   └─────────────┘   └──────────┘
        │                │                │
        ▼                ▼                ▼
    Policy           Browser          LLM-generated
    Engine           Automation       Verifications
```

## Security Properties

### 1. Fail-Closed Authorization

**Property**: All actions denied unless explicitly allowed

**Implementation**:
- Default policy effect: DENY
- Allowlist-based (not blocklist-based)
- No implicit permissions

**Example**:
```yaml
# This action is DENIED (no matching allow rule)
action: browser.navigate
resource: https://malicious-site.com

# This action is ALLOWED (matches rule)
action: browser.navigate
resource: https://www.example.com
```

### 2. Pre-Execution Enforcement

**Property**: Authorization checked BEFORE action execution

**Implementation**:
- Authorization precedes all browser operations
- No optimistic execution
- Synchronous authorization (no race conditions)

**Guarantee**: If authorization fails, action never executes

### 3. Post-Execution Verification

**Property**: Action success verified by independent LLM

**Implementation**:
- LLM generates verification assertions based on action context
- Verifications executed against actual browser state
- Failures cause action to be marked as unsuccessful

**Guarantee**: Action marked successful only if all verifications pass

### 4. Evidence-Based Decisions

**Property**: Authorization and verification use captured state evidence

**Implementation**:
- Pre-action snapshot captured
- Post-action snapshot captured
- Evidence passed to policy engine and verifier

**Guarantee**: Decisions based on actual state, not assumptions

## Extension Points

### Custom Policies

Add new authorization rules to `policies/browser_automation.yaml`:

```yaml
- name: allow-form-submission-safe-domains
  effect: ALLOW
  principals:
    - "agent:demo-browser"
  actions:
    - "browser.click"
  resources:
    - "element:button[type=submit*"
  conditions:
    required_labels:
      - "form_validated"
      - "user_confirmed"
```

### Custom Predicates

Add new verification predicates to `local_llm_verifier.py`:

```python
# In LocalLLMVerifier._execute_predicate()

elif predicate == "api_response_ok":
    # Custom predicate: check API response status
    response_code = self.browser.page.evaluate(
        "() => window.__lastApiResponse?.status"
    )
    return response_code == 200
```

### Custom Evidence

Extend state evidence with domain-specific signals:

```python
# Capture custom evidence
custom_evidence = {
    "form_fields_filled": self._check_form_complete(),
    "user_confirmation": self._check_confirmation_dialog(),
    "api_calls_succeeded": self._check_api_responses()
}

# Pass to authorization
request = ActionRequest(
    ...,
    state_evidence=StateEvidence(
        source="demo",
        state_hash=compute_hash(custom_evidence),
        custom_data=custom_evidence
    )
)
```

## Performance Considerations

### LLM Model Size

- **Qwen 2.5 7B**: ~14GB disk, ~8GB RAM, good accuracy
- **Qwen 2.5 3B**: ~6GB disk, ~4GB RAM, fast but less accurate
- **Quantization**: Use 8-bit or 4-bit quantization to reduce memory

### Caching

- Model weights cached after first load (~30s initial load)
- Subsequent calls: <1s per verification plan generation

### Batching

- Multiple verifications generated in single LLM call
- Batch verification execution (parallel predicate evaluation)

## Deployment Scenarios

### Development (Current Demo)

- **Authorization**: In-process policy engine
- **Browser**: Local Playwright
- **Verification**: Local LLM (GPU/CPU)

### Production (Recommended)

- **Authorization**: `predicate-authorityd` sidecar (Rust)
- **Browser**: Distributed browser grid
- **Verification**: Hosted LLM API or local inference server

### Air-Gapped (Secure Environments)

- **Authorization**: Sidecar with local-idp identity mode
- **Browser**: Local browser pool
- **Verification**: Local LLM on dedicated hardware

## Testing Strategy

### Unit Tests

- Test individual predicates (url_contains, element_exists, etc.)
- Test policy rule matching
- Test verification plan generation

### Integration Tests

- Test full authorization + execution + verification loop
- Test policy violation scenarios
- Test verification failure scenarios

### End-to-End Tests

- Test complete browser tasks
- Test multi-step workflows
- Test delegation scenarios (future)

## Future Enhancements

1. **Delegation Support**: Pass mandates between agents
2. **Audit Trail**: Store all decisions in tamper-evident log
3. **Streaming Verifications**: Generate and execute verifications incrementally
4. **Multi-Modal Verification**: Use vision models for screenshot-based verification
5. **Policy Learning**: Learn policies from human demonstrations
6. **Automatic Repair**: Auto-fix actions that fail verification

## References

- **Predicate Authority Manual**: [predicate-authority-user-manual.md](../../../AgentIdentity/docs/predicate-authority-user-manual.md)
- **SDK Python Browser**: [browser.py](../../../sdk-python/predicate/browser.py)
- **WebBench Planner**: [planner_executor_agent.py](../../../webbench/webbench/agents/planner_executor_agent.py)
