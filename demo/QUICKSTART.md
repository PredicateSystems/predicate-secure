# Quick Start Guide - Predicate Secure Demo

Get the demo running in 5 minutes!

## Prerequisites

- Python 3.11+
- 8GB+ RAM
- GPU recommended (or Apple Silicon MPS, or CPU)

## Installation (3 steps)

### 1. Install Dependencies

```bash
cd /Users/guoliangwang/Code/Sentience/predicate-secure/py-predicate-secure

# Install the predicate-secure SDK
pip install -e .

# Install demo dependencies (includes predicate-runtime==1.1.2 from PyPI)
cd demo
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Configure Environment

The demo comes with a pre-configured `.env` file. **No API key needed!** The demo uses the **FREE TIER** (local browser extension only), which is perfect for this demonstration.

**Optional**: Edit `.env` to customize:

```bash
# Show browser window (set to true for headless)
BROWSER_HEADLESS=false

# Use smaller model if RAM is limited
LLM_MODEL_NAME=Qwen/Qwen2.5-3B-Instruct  # Instead of 7B

# Optional: Add Predicate API key for enhanced features
# (Free tier is sufficient for this demo)
# PREDICATE_API_KEY=your-api-key-here
```

**Note**: The demo works completely offline (except for initial model download) using the free tier!

### 3. Run the Demo

**Simple Mode (Recommended for First Run):**

```bash
python secure_browser_demo.py
```

The demo uses **in-process authorization** (no sidecar needed). Policy evaluation happens directly in Python.

**First run**: Model downloads automatically (~14GB for 7B model, ~6GB for 3B model). Takes 2-5 minutes.

**Subsequent runs**: Fast startup (~5 seconds for model loading).

---

### Optional: Production Mode with Sidecar

For production-like setup with the Rust-based `predicate-authorityd` sidecar:

**Step 1: Verify Sidecar Installation**

The `predicate-authorityd` sidecar binary is installed automatically with `predicate-authority`:

```bash
# Verify sidecar is available
predicate-authorityd --version
```

**Step 2: Start Sidecar with Local IdP**

```bash
# Set signing key for local IdP mode
export LOCAL_IDP_SIGNING_KEY="demo-secret-key-replace-in-production"

# Start sidecar in background
predicate-authorityd run \
  --host 127.0.0.1 \
  --port 8787 \
  --mode local_only \
  --policy-file policies/browser_automation.yaml \
  --identity-mode local-idp \
  --local-idp-issuer "http://localhost/predicate-local-idp" \
  --local-idp-audience "api://predicate-authority" &

# Wait for sidecar to start
sleep 2

# Verify sidecar is running
curl http://127.0.0.1:8787/health
```

**Step 3: Update Demo to Use Sidecar**

Uncomment the sidecar configuration in `.env`:

```bash
# In .env, uncomment these lines:
PREDICATE_SIDECAR_HOST=127.0.0.1
PREDICATE_SIDECAR_PORT=8787
USE_SIDECAR=true
```

**Step 4: Run Demo with Sidecar**

```bash
python secure_browser_demo.py
```

The demo will now use the sidecar for authorization instead of in-process policy evaluation.

**To stop the sidecar:**

```bash
# Find and kill the sidecar process
pkill predicate-authorityd
```

---

**Note:** For this quick start, **in-process mode is recommended**. Sidecar mode is for production deployments where you want centralized authorization across multiple agents.

## Expected Output

```
╭──────────── Demo Configuration ─────────────╮
│ Predicate Secure Browser Automation Demo   │
│                                             │
│ Task: Navigate to example.com and verify   │
│ Start URL: https://www.example.com         │
│ Principal: agent:demo-browser              │
╰─────────────────────────────────────────────╯

Initializing Local LLM Verifier...
⠋ Loading Qwen 2.5 7B model...
✓ Verifier initialized

Step 1: Initializing Browser...
✓ Browser started

Step 2: Executing Browser Task...

→ Action: navigate (https://www.example.com)
  Pre-execution: Checking authorization...
  ✓ Action authorized
  Executing action...
  ✓ Action executed
  Post-execution: Generating verification plan...
  i Generated 2 verifications
  Executing verifications...
    [1] url_contains(example.com)
        ✓ Passed
    [2] snapshot_changed()
        ✓ Passed
  ✓ All verifications passed

╭─────── Success ───────╮
│ ✓ Demo completed      │
│   successfully!       │
╰───────────────────────╯
```

## What Just Happened?

The demo executed a complete **pre-execution authorization + post-execution verification** loop:

1. **Pre-Execution**: Checked if "navigate to example.com" is allowed by policy ✓
2. **Execution**: Opened browser and navigated to the URL ✓
3. **Post-Execution**: Local LLM generated 2 verifications:
   - `url_contains(example.com)` - Check URL is correct ✓
   - `snapshot_changed()` - Check page loaded ✓
4. **Snapshot**: Captured page elements with **visual overlay highlights** ✓
   - Watch the browser window - you'll see colored boxes around detected DOM elements!

All checks passed → Action successful!

## Try Yourself

### Test 1: Policy Violation

Edit `.env` to try navigating to a blocked domain:

```bash
# This should be DENIED by policy (not in allowed domains)
DEMO_START_URL=https://malicious-site.com
```

Run again:

```bash
python secure_browser_demo.py
```

Expected:
```
→ Action: navigate (https://malicious-site.com)
  Pre-execution: Checking authorization...
  ✗ Action denied by policy
```

### Test 2: Custom Task

Edit `secure_browser_demo.py` to add more actions:

```python
async def _run_browser_task(self):
    """Run browser task with authorization and verification."""

    # Navigate
    await self._authorized_action(
        action="navigate",
        target=self.start_url,
        executor=lambda: self.browser.goto(self.start_url)
    )

    # ADD THIS: Click a link
    await self._authorized_action(
        action="click",
        target="a",  # Click first link
        executor=lambda: self.browser.page.click("a")
    )
```

## Troubleshooting

### "Out of Memory" Error

**Solution**: Use smaller model

```bash
# In .env
LLM_MODEL_NAME=Qwen/Qwen2.5-3B-Instruct
```

Or enable quantization (requires `bitsandbytes`):

```bash
pip install bitsandbytes
```

### "Browser Failed to Start"

**Solution**: Install Playwright browsers

```bash
playwright install chromium
```

### "Model Download Failed"

**Solution**: Check internet connection and HuggingFace access

```bash
# Test download manually
python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('Qwen/Qwen2.5-7B-Instruct', trust_remote_code=True)"
```

## Next Steps

1. **Read Architecture**: See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design
2. **Customize Policy**: Edit [policies/browser_automation.yaml](policies/browser_automation.yaml)
3. **Add Predicates**: Extend verification logic in [local_llm_verifier.py](local_llm_verifier.py)
4. **Build Your Agent**: Use this as a template for your own secure agent!

## Questions?

- **Demo Documentation**: [README.md](README.md)
- **Policy Reference**: Check `policies/browser_automation.yaml` for examples
- **Predicate Authority**: See `AgentIdentity/docs/predicate-authority-user-manual.md`

---

**Happy hacking!** 🚀
