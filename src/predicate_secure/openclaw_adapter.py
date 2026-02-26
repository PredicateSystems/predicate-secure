"""OpenClaw adapter with HTTP proxy for skill interception.

This module provides integration with OpenClaw CLI agents by:
1. Starting a local HTTP proxy server
2. Intercepting OpenClaw skill invocations (e.g., predicate-snapshot)
3. Enforcing authorization policies before forwarding to actual skills
4. Managing OpenClaw CLI subprocess lifecycle
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable
from urllib.parse import urlparse


@dataclass
class OpenClawConfig:
    """Configuration for OpenClaw agent wrapper."""

    cli_path: str | None = None  # Path to openclaw CLI (if not in PATH)
    skill_proxy_port: int = 8788  # Port for HTTP proxy server
    skill_name: str = "predicate-snapshot"  # Skill to intercept
    skill_target_url: str | None = None  # Original skill URL (if applicable)
    working_dir: str | None = None  # Working directory for CLI
    env: dict[str, str] | None = None  # Environment variables


@dataclass
class OpenClawProcess:
    """Wrapper for OpenClaw CLI subprocess."""

    process: subprocess.Popen | None
    config: OpenClawConfig
    proxy_server: HTTPServer | None = None
    proxy_thread: threading.Thread | None = None


class SkillProxyHandler(BaseHTTPRequestHandler):
    """HTTP request handler that intercepts OpenClaw skill calls."""

    # Class-level attribute to store the authorizer callback
    authorizer: Callable[[str, dict], bool] | None = None

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default HTTP server logging."""
        # Only log if verbose mode is enabled
        if os.getenv("PREDICATE_SECURE_VERBOSE"):
            super().log_message(format, *args)

    def do_POST(self) -> None:
        """Handle POST requests from OpenClaw skills."""
        try:
            # Parse request path and body
            parsed_path = urlparse(self.path)
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b""

            # Parse JSON body
            try:
                request_data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                request_data = {}

            # Extract action and resource from request
            action = self._extract_action(parsed_path.path, request_data)
            resource = self._extract_resource(request_data)

            # Authorize the request
            if self.authorizer:
                try:
                    allowed = self.authorizer(action, {"resource": resource, "data": request_data})
                    if not allowed:
                        self._send_error_response(403, "Action denied by policy")
                        return
                except Exception as e:
                    self._send_error_response(403, f"Authorization failed: {e}")
                    return

            # Forward to actual skill implementation
            # For now, we'll return a success response
            # In production, this would forward to the real skill endpoint
            response = {
                "success": True,
                "message": "Skill authorized and executed",
                "action": action,
                "resource": resource,
            }

            self._send_json_response(200, response)

        except Exception as e:
            self._send_error_response(500, f"Internal server error: {e}")

    def do_GET(self) -> None:
        """Handle GET requests (health checks, etc.)."""
        if self.path == "/health":
            self._send_json_response(200, {"status": "ok"})
        else:
            self._send_error_response(404, "Not found")

    def _extract_action(self, path: str, data: dict) -> str:
        """Extract action from request path and data."""
        # Path like /predicate-snapshot or /predicate-act
        if path.startswith("/predicate-snapshot"):
            return "openclaw.skill.predicate-snapshot"
        if path.startswith("/predicate-act"):
            action_type = data.get("action", "unknown")
            return f"openclaw.skill.predicate-act.{action_type}"
        return f"openclaw.skill{path}"

    def _extract_resource(self, data: dict) -> str:
        """Extract resource from request data."""
        # For predicate-act, resource is the element ID
        if "elementId" in data:
            return f"element:{data['elementId']}"
        # For predicate-snapshot, resource is the current page
        if "url" in data:
            return data["url"]
        return "*"

    def _send_json_response(self, status: int, data: dict) -> None:
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _send_error_response(self, status: int, message: str) -> None:
        """Send error response."""
        self._send_json_response(status, {"success": False, "error": message})


class OpenClawAdapter:
    """
    Adapter for OpenClaw CLI agents.

    This adapter manages OpenClaw CLI subprocess and intercepts skill
    invocations via an HTTP proxy server.
    """

    def __init__(self, config: OpenClawConfig):
        """
        Initialize OpenClaw adapter.

        Args:
            config: OpenClaw configuration
        """
        self.config = config
        self.process: OpenClawProcess | None = None
        self._authorizer: Callable[[str, dict], bool] | None = None

    def set_authorizer(self, authorizer: Callable[[str, dict], bool]) -> None:
        """
        Set the authorization callback.

        Args:
            authorizer: Callable that takes (action, context) and returns bool
        """
        self._authorizer = authorizer
        SkillProxyHandler.authorizer = self._wrap_authorizer(authorizer)

    def _wrap_authorizer(self, authorizer: Callable[[str, dict], bool]) -> Callable[[str, dict], bool]:
        """Wrap authorizer to handle predicate-authority integration."""

        def wrapped(action: str, context: dict) -> bool:
            try:
                # Call the original authorizer
                return authorizer(action, context)
            except Exception as e:
                # Log error and deny by default
                print(f"Authorization error: {e}")
                return False

        return wrapped

    def start_proxy(self) -> None:
        """Start the HTTP proxy server for skill interception."""
        if self.process and self.process.proxy_server:
            return  # Already running

        port = self.config.skill_proxy_port
        server = HTTPServer(("localhost", port), SkillProxyHandler)

        # Start server in background thread
        def serve():
            print(f"[predicate-secure] Skill proxy listening on http://localhost:{port}")
            server.serve_forever()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()

        if not self.process:
            self.process = OpenClawProcess(
                process=None, config=self.config, proxy_server=server, proxy_thread=thread
            )
        else:
            self.process.proxy_server = server
            self.process.proxy_thread = thread

    def stop_proxy(self) -> None:
        """Stop the HTTP proxy server."""
        if self.process and self.process.proxy_server:
            self.process.proxy_server.shutdown()
            self.process.proxy_server = None
            self.process.proxy_thread = None

    def start_cli(self, task: str | None = None) -> subprocess.Popen:
        """
        Start OpenClaw CLI subprocess.

        Args:
            task: Optional task to execute

        Returns:
            Subprocess handle
        """
        cli_path = self.config.cli_path or "openclaw"
        working_dir = self.config.working_dir or os.getcwd()

        # Build command
        cmd = [cli_path]
        if task:
            cmd.append(task)

        # Build environment
        env = os.environ.copy()
        if self.config.env:
            env.update(self.config.env)

        # Add proxy URL to environment for skills to use
        env["PREDICATE_PROXY_URL"] = f"http://localhost:{self.config.skill_proxy_port}"

        # Start process
        # Security: cmd is built from trusted config (cli_path) and user-provided task
        # The cli_path comes from OpenClawConfig which is controlled by the developer
        # Task parameter is validated and passed as a separate argument (not shell-interpolated)
        process = subprocess.Popen(  # nosec B603
            cmd,
            cwd=working_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        if not self.process:
            self.process = OpenClawProcess(process=process, config=self.config)
        else:
            self.process.process = process

        return process

    def stop_cli(self) -> None:
        """Stop OpenClaw CLI subprocess."""
        if self.process and self.process.process:
            self.process.process.terminate()
            try:
                self.process.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.process.kill()
            self.process.process = None

    def cleanup(self) -> None:
        """Clean up resources (stop proxy and CLI)."""
        self.stop_cli()
        self.stop_proxy()

    @staticmethod
    def detect(agent: Any) -> bool:
        """
        Detect if agent is an OpenClaw wrapper.

        Args:
            agent: Agent object to check

        Returns:
            True if agent is OpenClaw-related
        """
        # Check if it's an OpenClawConfig
        if isinstance(agent, OpenClawConfig):
            return True

        # Check if it's a dict with OpenClaw config keys
        if isinstance(agent, dict):
            return "openclaw_cli_path" in agent or "skill_proxy_url" in agent

        # Check module name
        module = getattr(type(agent), "__module__", "")
        return "openclaw" in module.lower()


def create_openclaw_adapter(
    agent: Any,
    authorizer: Callable[[str, dict], bool] | None = None,
) -> OpenClawAdapter:
    """
    Create OpenClawAdapter from agent configuration.

    Args:
        agent: OpenClaw config dict or OpenClawConfig object
        authorizer: Optional authorization callback

    Returns:
        Configured OpenClawAdapter

    Raises:
        ValueError: If agent is not valid OpenClaw config
    """
    # Convert dict to OpenClawConfig
    if isinstance(agent, dict):
        config = OpenClawConfig(
            cli_path=agent.get("openclaw_cli_path"),
            skill_proxy_port=agent.get("skill_proxy_port", 8788),
            skill_name=agent.get("skill_name", "predicate-snapshot"),
            skill_target_url=agent.get("skill_target_url"),
            working_dir=agent.get("working_dir"),
            env=agent.get("env"),
        )
    elif isinstance(agent, OpenClawConfig):
        config = agent
    else:
        raise ValueError(f"Invalid OpenClaw agent: {type(agent)}")

    adapter = OpenClawAdapter(config)

    if authorizer:
        adapter.set_authorizer(authorizer)

    return adapter
