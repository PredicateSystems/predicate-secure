# Changelog - Predicate Secure Demo

## [2024-02-25] - Interactive Click Functionality

### Added
- **Interactive clicking**: Demo now finds and clicks the "Learn more" link on example.com using semantic element query
- **Semantic element finding**: Uses `find()` function from predicate SDK with DSL query `"role=link text~'Learn more'"`
- **Post-click verification**: Automatically verifies URL contains "example-domains" after clicking via LLM-generated verifications

### Implementation Details

#### New Methods
1. **`_find_and_click_link(snapshot, link_text)`**
   - Uses semantic query to find links by text
   - Falls back gracefully if link not found
   - Wraps click in authorized action pattern with verification

2. **`_click_element(element)`**
   - Clicks element using Playwright selector
   - Falls back to coordinate-based clicking if selector fails

#### Enhanced Methods
3. **`_authorized_action()` now returns result**
   - Returns the executor result for use in subsequent actions
   - Enables capturing snapshot for element finding

4. **`_run_browser_task()` updated**
   - Step 1: Navigate to example.com
   - Step 2: Take snapshot (with overlay)
   - Step 3: Find and click "Learn more" link
   - Post-verification checks URL contains "example-domains"

### Policy Changes
- Added `click` action to authorization policy
- Added `element#*` resource pattern for element ID-based clicks
- Updated `allow-browser-click-safe-elements` rule

### Verification Flow
When clicking the link, the demo:
1. **Pre-execution authorization**: Checks click action is allowed by policy
2. **Execute click**: Uses Playwright to click the element
3. **Post-execution verification**: LLM generates verifications including:
   - URL changed from example.com
   - URL contains "example-domains"
   - Page content updated
   - Element interaction successful

### Visual Features
- Snapshot overlay enabled (`show_overlay=True`)
- Elements highlighted in browser during snapshot capture
- Console shows element details (ID, role, clickability)

## [2024-02-25] - Cloud Tracing Integration

### Added
- **Cloud tracing**: Upload authorization and verification events to Predicate Studio
- **Run tracking**: Each demo run gets unique UUID and timestamp label
- **Event emission**:
  - Authorization events (action, target, decision)
  - Verification events (predicates, reasoning, pass/fail)
- **Studio integration**: View execution timeline at `https://studio.predicatesystems.dev/runs/{run_id}`

### Configuration
- Automatic when `PREDICATE_API_KEY` is set in `.env`
- Uses `create_tracer()` from predicate SDK
- Blocking upload on cleanup to ensure events are sent

## [2024-02-24] - Initial Release

### Core Features
- Pre-execution authorization via policy file
- Post-execution verification via local LLM (Qwen 2.5 7B)
- Apple Silicon MPS support via `device_map="auto"`
- AsyncPredicateBrowser integration
- Visual element overlay during snapshot capture

### Dependencies
- `predicate-runtime==1.1.2` (browser automation)
- `predicate-authority>=0.1.0` (authorization)
- Qwen 2.5 7B Instruct (local LLM)
- Rich console output

### Documentation
- Quick start guide (5 minutes)
- Full setup instructions
- Sidecar setup guide (optional)
- Architecture diagrams
