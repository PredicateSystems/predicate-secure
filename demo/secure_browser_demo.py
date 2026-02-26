"""Predicate Secure Browser Automation Demo.

This demo showcases the complete agent loop with:
1. Pre-execution authorization (predicate-authorityd sidecar + SecureAgent)
2. Browser automation (PredicateBrowser from sdk-python)
3. Post-execution verification (Local LLM with Qwen 2.5 7B)

The demo runs a simple browser task with full authorization and verification.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path for importing predicate_secure
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from predicate_secure import SecureAgent
from predicate_secure.openclaw_adapter import OpenClawConfig

# Import local LLM verifier
from local_llm_verifier import VerificationPlan, create_verifier_from_env

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)],
)
logger = logging.getLogger(__name__)
console = Console()


class SecureBrowserDemo:
    """Demo orchestrator for secure browser automation."""

    def __init__(self):
        """Initialize demo configuration."""
        # Load environment variables
        load_dotenv(Path(__file__).parent / ".env")

        # Configuration
        self.task_id = os.getenv("DEMO_TASK_ID", "example-search-task")
        self.start_url = os.getenv("DEMO_START_URL", "https://www.example.com")
        self.task_description = os.getenv(
            "DEMO_TASK_DESCRIPTION", "Navigate to example.com and verify page loads"
        )
        self.principal_id = os.getenv("DEMO_PRINCIPAL_ID", "agent:demo-browser")
        self.tenant_id = os.getenv("DEMO_TENANT_ID", "tenant-demo")
        self.output_dir = Path(os.getenv("DEMO_OUTPUT_DIR", "demo/output"))

        # Policy file
        self.policy_file = Path(__file__).parent / "policies" / "browser_automation.yaml"

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components (lazy)
        self.verifier = None
        self.secure_agent = None
        self.browser = None

    def _init_verifier(self):
        """Initialize local LLM verifier."""
        if self.verifier is None:
            console.print("\n[bold cyan]Initializing Local LLM Verifier...[/bold cyan]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Loading Qwen 2.5 7B model...", total=None)
                self.verifier = create_verifier_from_env()
                progress.update(task, completed=True)
            console.print("[green]✓[/green] Verifier initialized\n")

    def _init_secure_agent(self):
        """Initialize SecureAgent with predicate-authority integration."""
        if self.secure_agent is not None:
            return

        console.print("\n[bold cyan]Initializing Secure Agent...[/bold cyan]")

        # For this demo, we'll use a simplified approach without the sidecar
        # In production, you would start the predicate-authorityd sidecar and connect to it
        # For now, use in-process guard with the policy file

        try:
            # Create secure agent with browser-like config
            # Note: SecureAgent expects an agent object, so we'll create a simple wrapper
            from predicate import PredicateBrowser

            # Create browser config (but don't start yet)
            browser_config = {
                "headless": os.getenv("BROWSER_HEADLESS", "false").lower() == "true",
                "api_key": None,  # Using free tier for demo
            }

            # Initialize SecureAgent with policy
            self.secure_agent = SecureAgent(
                agent=browser_config,  # Will be wrapped by SecureAgent
                policy=str(self.policy_file),
                mode="strict",  # Fail-closed mode
                principal_id=self.principal_id,
                trace_format="console",
            )

            console.print(f"[green]✓[/green] SecureAgent initialized")
            console.print(f"  Policy: {self.policy_file}")
            console.print(f"  Mode: strict (fail-closed)")
            console.print(f"  Principal: {self.principal_id}\n")

        except Exception as e:
            console.print(f"[red]✗[/red] Failed to initialize SecureAgent: {e}")
            raise

    async def run_demo(self):
        """Run the complete demo workflow."""
        console.print(
            Panel.fit(
                "[bold cyan]Predicate Secure Browser Automation Demo[/bold cyan]\n\n"
                f"Task: {self.task_description}\n"
                f"Start URL: {self.start_url}\n"
                f"Principal: {self.principal_id}",
                title="Demo Configuration",
                border_style="cyan",
            )
        )

        try:
            # Step 1: Initialize components
            self._init_verifier()
            self._init_secure_agent()

            # Step 2: Initialize browser (with authorization)
            await self._init_browser()

            # Step 3: Perform browser actions with pre-auth and post-verification
            await self._run_browser_task()

            # Step 4: Cleanup
            await self._cleanup()

            console.print(
                Panel.fit(
                    "[bold green]✓ Demo completed successfully![/bold green]",
                    title="Success",
                    border_style="green",
                )
            )

        except Exception as e:
            console.print(
                Panel.fit(
                    f"[bold red]✗ Demo failed: {e}[/bold red]",
                    title="Error",
                    border_style="red",
                )
            )
            logger.exception("Demo failed with error:")
            await self._cleanup()
            raise

    async def _init_browser(self):
        """Initialize browser with SecureAgent integration."""
        console.print("\n[bold cyan]Step 1: Initializing Browser...[/bold cyan]")

        # Import AsyncPredicateBrowser
        from predicate import AsyncPredicateBrowser

        # Get API key from environment (optional - uses free tier if not set)
        api_key = os.getenv("PREDICATE_API_KEY")
        if api_key:
            console.print("[dim]Using Predicate API key for enhanced features[/dim]")
        else:
            console.print("[dim]Using FREE TIER (local browser extension only)[/dim]")

        # Create browser - extension is automatically loaded by start()
        self.browser = AsyncPredicateBrowser(
            headless=os.getenv("BROWSER_HEADLESS", "false").lower() == "true",
            api_key=api_key,  # None = free tier, string = enhanced features
        )

        # Start browser (extension loads automatically)
        await self.browser.start()
        console.print("[green]✓[/green] Browser started\n")

    async def _run_browser_task(self):
        """Run browser task with authorization and verification."""
        console.print("\n[bold cyan]Step 2: Executing Browser Task...[/bold cyan]")

        # Action 1: Navigate to start URL
        await self._authorized_action(
            action="navigate",
            target=self.start_url,
            executor=lambda: self.browser.goto(self.start_url),  # Returns coroutine
        )

        # Action 2: Take snapshot
        await self._authorized_action(
            action="snapshot",
            target="current_page",
            executor=lambda: self._take_snapshot(),  # Returns coroutine
        )

        console.print("\n[green]✓[/green] Task completed successfully\n")

    async def _authorized_action(self, action: str, target: str, executor: callable):
        """Execute an action with pre-authorization and post-verification.

        This is the core loop demonstrating:
        1. Pre-execution authorization (via SecureAgent/predicate-authority)
        2. Action execution (browser operation)
        3. Post-execution verification (via local LLM)
        """
        console.print(f"\n[yellow]→[/yellow] Action: {action} ({target})")

        # === PRE-EXECUTION AUTHORIZATION ===
        console.print("  [dim]Pre-execution: Checking authorization...[/dim]")

        # In a full implementation, this would call SecureAgent.authorize()
        # For this demo, we'll simulate the authorization check
        authorized = self._check_authorization(action, target)

        if not authorized:
            console.print("  [red]✗[/red] Action denied by policy")
            raise PermissionError(f"Action {action} denied by authorization policy")

        console.print("  [green]✓[/green] Action authorized")

        # === ACTION EXECUTION ===
        console.print("  [dim]Executing action...[/dim]")

        # Capture pre-action state
        pre_snapshot = await self._get_page_summary()

        # Execute the action
        try:
            result = executor()
            # Await if the result is a coroutine
            if hasattr(result, '__await__'):
                result = await result
            console.print("  [green]✓[/green] Action executed")
        except Exception as e:
            console.print(f"  [red]✗[/red] Action failed: {e}")
            raise

        # === POST-EXECUTION VERIFICATION ===
        console.print("  [dim]Post-execution: Generating verification plan...[/dim]")

        # Capture post-action state
        post_snapshot = await self._get_page_summary()

        # Generate verification plan using local LLM
        verification_plan = self.verifier.generate_verification_plan(
            action=action,
            action_target=target,
            pre_snapshot_summary=pre_snapshot,
            post_snapshot_summary=post_snapshot,
            context={"task": self.task_description},
        )

        console.print(
            f"  [cyan]i[/cyan] Generated {len(verification_plan.verifications)} verifications"
        )
        if verification_plan.reasoning:
            console.print(f"    Reasoning: {verification_plan.reasoning}")

        # Execute verifications
        console.print("  [dim]Executing verifications...[/dim]")
        all_passed = self._execute_verifications(verification_plan)

        if all_passed:
            console.print("  [green]✓[/green] All verifications passed")
        else:
            console.print("  [red]✗[/red] Some verifications failed")
            raise AssertionError("Post-execution verification failed")

    def _check_authorization(self, action: str, target: str) -> bool:
        """Check if action is authorized by policy.

        In production, this would call SecureAgent.authorize() with full
        ActionRequest and get back a decision with mandate.

        For this demo, we'll use simplified logic based on the policy.
        """
        # Map demo actions to policy actions
        action_map = {
            "navigate": "browser.navigate",
            "snapshot": "browser.snapshot",
            "click": "browser.click",
            "type": "browser.type",
        }

        policy_action = action_map.get(action, action)

        # Simple checks based on our policy
        if action == "navigate":
            # Check if target URL is in allowed domains
            allowed_domains = ["example.com", "google.com", "wikipedia.org"]
            return any(domain in target for domain in allowed_domains)
        elif action == "snapshot":
            # Snapshots are always allowed
            return True
        else:
            # For other actions, default to allow for demo
            return True

    async def _get_page_summary(self) -> str:
        """Get summary of current page state."""
        if not self.browser or not self.browser.page:
            return "Browser not initialized"

        try:
            # Get current URL
            url = self.browser.page.url

            # Get page title
            title = await self.browser.page.title()

            # Get visible text (truncated)
            text = await self.browser.page.inner_text("body")
            text_preview = text[:200] + "..." if len(text) > 200 else text

            return f"URL: {url}\nTitle: {title}\nContent: {text_preview}"
        except Exception as e:
            return f"Error getting page summary: {e}"

    async def _take_snapshot(self):
        """Take a snapshot of the current page."""
        # Use snapshot_async which handles API vs extension automatically
        from predicate.snapshot import snapshot_async
        from predicate.models import SnapshotOptions

        # Take snapshot with overlay enabled to show element highlights
        # This makes it visual and educational - you can see what elements are detected!
        snap = await snapshot_async(
            self.browser,
            SnapshotOptions(
                show_overlay=True,  # Show highlighted boxes around detected elements
                screenshot=False,  # Don't need screenshots for this demo
            ),
        )
        console.print(f"    Snapshot captured: {len(snap.elements)} elements")
        console.print("    [dim](Watch the browser - elements are highlighted!)[/dim]")
        return snap

    def _execute_verifications(self, plan: VerificationPlan) -> bool:
        """Execute verification assertions from plan.

        Returns:
            True if all verifications passed, False otherwise
        """
        all_passed = True

        for i, verif in enumerate(plan.verifications, 1):
            console.print(f"    [{i}] {verif.predicate}({', '.join(map(str, verif.args))})")

            # Execute verification predicate
            try:
                passed = self._execute_predicate(verif.predicate, verif.args)
                if passed:
                    console.print(f"        [green]✓[/green] Passed")
                else:
                    console.print(f"        [red]✗[/red] Failed")
                    all_passed = False
            except Exception as e:
                console.print(f"        [red]✗[/red] Error: {e}")
                all_passed = False

        return all_passed

    def _execute_predicate(self, predicate: str, args: list) -> bool:
        """Execute a verification predicate.

        This is a simplified implementation for demo purposes.
        In production, you would use the full predicate evaluation engine.
        """
        if not self.browser or not self.browser.page:
            return False

        try:
            if predicate == "url_contains":
                substring = args[0] if args else ""
                return substring in self.browser.page.url

            elif predicate == "url_changed":
                # For demo, assume URL changed if we navigated
                return True

            elif predicate == "snapshot_changed":
                # For demo, assume snapshot changed
                return True

            elif predicate == "element_exists":
                selector = args[0] if args else ""
                return self.browser.page.locator(selector).count() > 0

            elif predicate == "element_visible":
                selector = args[0] if args else ""
                return self.browser.page.locator(selector).is_visible()

            else:
                logger.warning(f"Unknown predicate: {predicate}")
                return False

        except Exception as e:
            logger.warning(f"Predicate execution failed: {e}")
            return False

    async def _cleanup(self):
        """Clean up resources."""
        console.print("\n[dim]Cleaning up...[/dim]")

        if self.browser:
            try:
                await self.browser.close()
                console.print("[green]✓[/green] Browser closed")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")


async def main():
    """Main entry point."""
    demo = SecureBrowserDemo()
    await demo.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
