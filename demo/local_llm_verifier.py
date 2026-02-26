"""Local LLM-based post-execution verification planner.

Uses HuggingFace transformers with Qwen 2.5 7B to generate verification
assertions on-the-fly based on browser state and action context.

This serves as the post-execution verification layer in the complete
predicate-secure agent loop.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class VerificationSpec:
    """Specification for a verification assertion."""

    predicate: str  # e.g., "url_contains", "element_exists", "snapshot_changed"
    args: list[str | int] = None
    label: str | None = None
    rationale: str | None = None

    def __post_init__(self):
        if self.args is None:
            self.args = []


@dataclass
class VerificationPlan:
    """Plan containing multiple verification assertions."""

    action: str  # The action that was performed
    verifications: list[VerificationSpec]
    reasoning: str | None = None


class LocalLLMVerifier:
    """Local LLM-based verification planner using HuggingFace transformers."""

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-7B-Instruct",
        device: str = "auto",
        max_tokens: int = 512,
        temperature: float = 0.0,
    ):
        """Initialize local LLM verifier.

        Args:
            model_name: HuggingFace model name (default: Qwen/Qwen2.5-7B-Instruct)
            device: Device to run model on (auto, cuda, cpu, mps)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 for deterministic)
        """
        self.model_name = model_name
        self.device = device
        self.max_tokens = max_tokens
        self.temperature = temperature

        self._model: Optional[Any] = None
        self._tokenizer: Optional[Any] = None
        self._initialized = False

    def _lazy_init(self) -> None:
        """Lazy initialization of model and tokenizer."""
        if self._initialized:
            return

        logger.info("Loading local LLM model: %s", self.model_name)

        try:

            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)

            # Load model with automatic device mapping
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map=self.device,
                trust_remote_code=True,
                # Optional: Add quantization config here if needed
                # load_in_8bit=True,  # Requires bitsandbytes
            )

            self._initialized = True
            logger.info(f"Model loaded successfully on device: {self.device}")

        except ImportError as e:
            raise RuntimeError(
                f"Failed to import transformers. Install with: pip install transformers torch accelerate\n"
                f"Error: {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to load model {self.model_name}: {e}") from e

    def generate_verification_plan(
        self,
        action: str,
        action_target: str | None,
        pre_snapshot_summary: str,
        post_snapshot_summary: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> VerificationPlan:
        """Generate verification plan for a browser action.

        Args:
            action: The action performed (e.g., "navigate", "click", "type")
            action_target: Target of the action (e.g., URL, element selector)
            pre_snapshot_summary: Summary of page state before action
            post_snapshot_summary: Summary of page state after action (if available)
            context: Additional context (e.g., task description, intent)

        Returns:
            VerificationPlan with generated verification assertions
        """
        self._lazy_init()

        # Build prompt for verification planning
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            action=action,
            action_target=action_target,
            pre_snapshot_summary=pre_snapshot_summary,
            post_snapshot_summary=post_snapshot_summary,
            context=context or {},
        )

        # Generate verification plan
        response = self._generate(system_prompt, user_prompt)

        # Parse response into VerificationPlan
        try:
            plan = self._parse_verification_plan(response, action)
            logger.debug(f"Generated {len(plan.verifications)} verification assertions")
            return plan
        except Exception as e:
            logger.warning(f"Failed to parse verification plan: {e}")
            # Return fallback plan with basic assertion
            return self._fallback_plan(action)

    def _build_system_prompt(self) -> str:
        """Build system prompt for verification planning."""
        return """You are a verification planner for browser automation.

Your task is to generate POST-EXECUTION verification assertions that check
whether a browser action succeeded and produced the expected outcome.

Given:
- The action performed (navigate, click, type, etc.)
- The action target (URL, element, input text)
- Page state before action
- Page state after action (if available)

Generate a JSON plan with verification assertions using these predicates:

**Supported Predicates:**
- url_contains(substring): Check if current URL contains substring
- url_matches(pattern): Check if URL matches regex pattern
- url_changed: Check if URL changed from previous state
- snapshot_changed: Check if page content changed
- element_exists(selector): Check if element exists in DOM
- element_not_exists(selector): Check if element does NOT exist
- element_visible(selector): Check if element is visible
- element_count(selector, min_count): Check element count >= min_count
- text_contains(substring): Check if page text contains substring
- text_matches(pattern): Check if page text matches pattern

**Output Format:**
Return ONLY valid JSON matching this schema:
{
  "reasoning": "Brief explanation of verification strategy",
  "verifications": [
    {
      "predicate": "url_contains",
      "args": ["expected_substring"],
      "label": "verify_navigation",
      "rationale": "Check navigation succeeded"
    }
  ]
}

**Guidelines:**
1. Generate 1-3 verification assertions (not too many)
2. Choose assertions that directly validate the action's success
3. For navigate/goto: verify URL changed or contains expected domain
4. For click: verify snapshot changed, element appeared/disappeared, or URL changed
5. For type: verify element value contains typed text or form submitted
6. Be specific and actionable
7. NO prose, NO markdown - ONLY JSON output
"""

    def _build_user_prompt(
        self,
        action: str,
        action_target: str | None,
        pre_snapshot_summary: str,
        post_snapshot_summary: str | None,
        context: dict[str, Any],
    ) -> str:
        """Build user prompt with action context."""
        parts = [
            "ACTION PERFORMED:",
            f"  Action: {action}",
            f"  Target: {action_target or 'N/A'}",
            "",
            "PAGE STATE BEFORE ACTION:",
            self._truncate_text(pre_snapshot_summary, max_length=800),
        ]

        if post_snapshot_summary:
            parts.extend(
                [
                    "",
                    "PAGE STATE AFTER ACTION:",
                    self._truncate_text(post_snapshot_summary, max_length=800),
                ]
            )

        if context.get("task"):
            parts.extend(["", f"TASK CONTEXT: {context['task']}"])

        if context.get("intent"):
            parts.extend(["", f"ACTION INTENT: {context['intent']}"])

        parts.extend(
            [
                "",
                "Generate verification plan as JSON:",
            ]
        )

        return "\n".join(parts)

    def _generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text using the local LLM."""
        assert self._tokenizer is not None, "Tokenizer not initialized"
        assert self._model is not None, "Model not initialized"

        # Format as chat messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Apply chat template
        text = self._tokenizer.apply_chat_template(  # type: ignore
            messages, tokenize=False, add_generation_prompt=True
        )

        # Tokenize
        inputs = self._tokenizer([text], return_tensors="pt").to(self._model.device)  # type: ignore

        # Generate
        outputs = self._model.generate(  # type: ignore
            **inputs,
            max_new_tokens=self.max_tokens,
            temperature=self.temperature if self.temperature > 0 else None,
            do_sample=self.temperature > 0,
            pad_token_id=self._tokenizer.eos_token_id,  # type: ignore
        )

        # Decode
        generated_text: str = self._tokenizer.decode(outputs[0], skip_special_tokens=True)  # type: ignore

        # Extract response (everything after the user prompt)
        # This handles the chat template format
        if "<|im_start|>assistant" in generated_text:
            response = generated_text.split("<|im_start|>assistant")[-1]
        elif "assistant\n" in generated_text:
            response = generated_text.split("assistant\n")[-1]
        else:
            # Fallback: take everything after user prompt
            response = generated_text[len(str(text)) :]

        return response.strip()

    def _parse_verification_plan(self, response: str, action: str) -> VerificationPlan:
        """Parse LLM response into VerificationPlan."""
        # Extract JSON from response (handle markdown code blocks)
        json_str = response
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()

        # Parse JSON
        data = json.loads(json_str)

        # Build VerificationPlan
        verifications = []
        for v in data.get("verifications", []):
            verifications.append(
                VerificationSpec(
                    predicate=v["predicate"],
                    args=v.get("args", []),
                    label=v.get("label"),
                    rationale=v.get("rationale"),
                )
            )

        return VerificationPlan(
            action=action, verifications=verifications, reasoning=data.get("reasoning")
        )

    def _fallback_plan(self, action: str) -> VerificationPlan:
        """Generate fallback verification plan when LLM fails."""
        # Simple heuristic-based fallback
        if action in ("navigate", "goto"):
            return VerificationPlan(
                action=action,
                verifications=[
                    VerificationSpec(predicate="url_changed", label="verify_navigation_succeeded")
                ],
                reasoning="Fallback: verify URL changed after navigation",
            )
        elif action == "click":
            return VerificationPlan(
                action=action,
                verifications=[
                    VerificationSpec(predicate="snapshot_changed", label="verify_click_effect")
                ],
                reasoning="Fallback: verify page changed after click",
            )
        else:
            return VerificationPlan(
                action=action,
                verifications=[
                    VerificationSpec(predicate="snapshot_changed", label="verify_action_effect")
                ],
                reasoning="Fallback: verify page state changed",
            )

    @staticmethod
    def _truncate_text(text: str, max_length: int) -> str:
        """Truncate text to max length with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."


# Factory function for easy instantiation
def create_verifier_from_env() -> LocalLLMVerifier:
    """Create LocalLLMVerifier from environment variables."""
    return LocalLLMVerifier(
        model_name=os.getenv("LLM_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct"),
        device=os.getenv("LLM_DEVICE", "auto"),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "512")),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
    )
