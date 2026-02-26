# Sidecar Setup Guide (Optional)

This guide explains how to run the demo with the `predicate-authorityd` sidecar for production-like authorization.

**Note:** The sidecar is **optional**. The demo works perfectly with in-process authorization (default mode).

---

## When to Use Sidecar Mode

Use sidecar mode when you want to:
- Test production deployment patterns
- Centralize authorization across multiple agents
- Use the Rust-based high-performance authorization engine
- Enable fleet management and audit logging
- Simulate enterprise deployment scenarios

**For first-time demo users:** Stick with in-process mode. It's simpler and works great!

---

## Installation

### Step 1: Verify Sidecar Installation

The `predicate-authorityd` sidecar binary is automatically installed with `predicate-authority`:

```bash
# Verify sidecar is available
predicate-authorityd --version
```

If not found, ensure `predicate-authority` is installed:

```bash
pip install predicate-authority>=0.1.0
```

### Step 2: Configure Environment

Edit `demo/.env` and uncomment the sidecar configuration:

```bash
# Enable sidecar mode
USE_SIDECAR=true
PREDICATE_SIDECAR_HOST=127.0.0.1
PREDICATE_SIDECAR_PORT=8787

# Configure local IdP mode (for offline/air-gapped operation)
LOCAL_IDP_SIGNING_KEY=demo-secret-key-replace-in-production-minimum-32-chars
LOCAL_IDP_ISSUER=http://localhost/predicate-local-idp
LOCAL_IDP_AUDIENCE=api://predicate-authority
```

---

## Running the Sidecar

### Option A: Manual Start (Recommended for Testing)

Start the sidecar in a separate terminal:

```bash
# Set environment variables
export LOCAL_IDP_SIGNING_KEY="demo-secret-key-replace-in-production-minimum-32-chars"

# Start sidecar with local IdP mode
predicate-authorityd run \
  --host 127.0.0.1 \
  --port 8787 \
  --mode local_only \
  --policy-file policies/browser_automation.yaml \
  --identity-mode local-idp \
  --local-idp-issuer "http://localhost/predicate-local-idp" \
  --local-idp-audience "api://predicate-authority"
```

**Expected output:**

```
[INFO] predicate-authorityd starting...
[INFO] Mode: local_only
[INFO] Identity mode: local-idp
[INFO] Policy loaded: policies/browser_automation.yaml (15 rules)
[INFO] HTTP server listening on http://127.0.0.1:8787
[INFO] Ready to serve requests
```

### Option B: Background Start (Production-like)

```bash
# Set signing key
export LOCAL_IDP_SIGNING_KEY="demo-secret-key-replace-in-production-minimum-32-chars"

# Start in background
nohup predicate-authorityd run \
  --host 127.0.0.1 \
  --port 8787 \
  --mode local_only \
  --policy-file policies/browser_automation.yaml \
  --identity-mode local-idp \
  --local-idp-issuer "http://localhost/predicate-local-idp" \
  --local-idp-audience "api://predicate-authority" \
  > sidecar.log 2>&1 &

# Save process ID
echo $! > sidecar.pid

# Wait for startup
sleep 2

# Verify it's running
curl http://127.0.0.1:8787/health
```

---

## Verifying Sidecar is Running

### Health Check

```bash
curl http://127.0.0.1:8787/health
```

**Expected response:**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptime_seconds": 42
}
```

### Status Check

```bash
curl http://127.0.0.1:8787/status
```

**Expected response:**

```json
{
  "status": "running",
  "mode": "local_only",
  "identity_mode": "local-idp",
  "policy_rules_count": 15,
  "requests_processed": 0,
  "uptime_seconds": 42
}
```

---

## Running the Demo with Sidecar

Once the sidecar is running, start the demo normally:

```bash
# Make sure USE_SIDECAR=true in .env
python secure_browser_demo.py
```

The demo will now connect to the sidecar for authorization instead of using in-process policy evaluation.

**Expected output:**

```
Initializing Secure Agent...
✓ SecureAgent initialized
  Authorization mode: sidecar
  Sidecar URL: http://127.0.0.1:8787
  Policy: policies/browser_automation.yaml
  Mode: strict (fail-closed)
```

---

## Monitoring Sidecar

### View Logs (if started in background)

```bash
tail -f sidecar.log
```

### Check Authorization Decisions

The sidecar logs all authorization decisions:

```
[INFO] Authorization request: principal=agent:demo-browser, action=browser.navigate, resource=https://www.example.com
[INFO] Policy evaluation: matched rule 'allow-navigation-safe-domains'
[INFO] Authorization decision: ALLOW (mandate issued)
```

### View Metrics

```bash
curl http://127.0.0.1:8787/status | jq
```

---

## Stopping the Sidecar

### If started manually (foreground):

Press `Ctrl+C` in the sidecar terminal.

### If started in background:

```bash
# Using saved PID
kill $(cat sidecar.pid)
rm sidecar.pid

# Or find and kill by name
pkill predicate-authorityd

# Or use killall
killall predicate-authorityd
```

---

## Troubleshooting

### Sidecar fails to start

**Issue:** Port 8787 already in use

**Solution:**

```bash
# Check what's using the port
lsof -i :8787

# Kill the process or use a different port
predicate-authorityd run --port 8788 ...
# Update .env: PREDICATE_SIDECAR_PORT=8788
```

### Demo can't connect to sidecar

**Issue:** Connection refused

**Solution:**

```bash
# 1. Check sidecar is running
curl http://127.0.0.1:8787/health

# 2. Check environment variable
echo $USE_SIDECAR  # Should be "true"

# 3. Check sidecar host/port in .env
cat .env | grep SIDECAR
```

### Authorization denied unexpectedly

**Issue:** Policy rules not matching

**Solution:**

```bash
# 1. Check policy file is loaded
curl http://127.0.0.1:8787/status | jq '.policy_rules_count'

# 2. Check sidecar logs for policy evaluation
tail -f sidecar.log | grep "Policy evaluation"

# 3. Verify rule syntax in policies/browser_automation.yaml
```

---

## Advanced Configuration

### Using Custom Policy File

```bash
# Start sidecar with custom policy
predicate-authorityd run \
  --policy-file /path/to/custom-policy.yaml \
  ...
```

### Enabling Cloud Mode

For production with cloud control plane:

```bash
export PREDICATE_API_KEY="your-api-key"

predicate-authorityd run \
  --mode cloud_connected \
  --control-plane-url https://api.predicatesystems.dev \
  --tenant-id your-tenant \
  --project-id your-project \
  --predicate-api-key $PREDICATE_API_KEY \
  ...
```

### Using OIDC/Entra Identity

For enterprise identity providers:

```bash
# Entra (Azure AD)
predicate-authorityd run \
  --identity-mode entra \
  --entra-tenant-id <tenant-id> \
  --entra-client-id <client-id> \
  --entra-client-secret <secret> \
  ...

# Generic OIDC
predicate-authorityd run \
  --identity-mode oidc \
  --oidc-issuer https://your-idp.com \
  --oidc-client-id <client-id> \
  --oidc-client-secret <secret> \
  ...
```

---

## Comparison: In-Process vs Sidecar

| Feature | In-Process | Sidecar |
|---------|-----------|---------|
| Setup complexity | ✅ Simple | ⚠️ Moderate |
| Performance | ✅ Fast | ✅ Very Fast (Rust) |
| Multi-agent support | ❌ No | ✅ Yes |
| Centralized logging | ❌ No | ✅ Yes |
| Fleet management | ❌ No | ✅ Yes |
| Audit trail | ⚠️ Basic | ✅ Production-grade |
| Hot-reload policies | ❌ No | ✅ Yes |
| Production ready | ⚠️ Testing only | ✅ Yes |

---

## Next Steps

1. ✅ Get the basic demo working with in-process mode
2. ✅ Try sidecar mode with local IdP (this guide)
3. 🔄 Experiment with custom policies
4. 🔄 Try cloud-connected mode (requires Predicate account)
5. 🔄 Integrate with enterprise IdP (Entra/OIDC)

---

## References

- **Predicate Authority User Manual**: [predicate-authority-user-manual.md](../../../AgentIdentity/docs/predicate-authority-user-manual.md)
- **Sidecar Operations Guide**: [authorityd-operations.md](../../../AgentIdentity/docs/authorityd-operations.md)
- **Demo README**: [README.md](README.md)
- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)
